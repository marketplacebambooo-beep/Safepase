import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Brain, Calendar, GraduationCap } from 'lucide-react'
import { api, getUser } from '../api'
import { LoadingScreen, Modal, RiskBadge } from '../components/UI'
import { useLanguage } from '../i18n/LanguageContext'
import { LANGUAGES } from '../i18n/translations'

const PREP_KEYS = [
  { key: 'facility_identified', labelKey: 'prepFacility' },
  { key: 'escort_identified', labelKey: 'prepEscort' },
  { key: 'danger_education_done', labelKey: 'prepDangerEdu' },
  { key: 'bag_prepared', labelKey: 'prepBag' },
]

const DANGER_TYPES = [
  { value: 'bleeding', labelKey: 'bleeding' },
  { value: 'severe_headache', labelKey: 'severeHeadache' },
  { value: 'swelling', labelKey: 'swelling' },
  { value: 'reduced_movement', labelKey: 'reducedMovement' },
  { value: 'other', labelKey: 'other' },
]

const FLAG_LABEL_KEYS = {
  adolescent: 'flagAdolescent',
  twins: 'flagTwins',
  first_pregnancy: 'flagFirstPregnancy',
  early_pregnancy: 'flagEarly',
  late_pregnancy: 'flagLate',
  post_term: 'flagPostTerm',
  guardian_consent_pending: 'flagGuardianPending',
  advanced_age: 'flagAdvancedAge',
}

function CareFlagBadge({ flag, t }) {
  const labelKey = FLAG_LABEL_KEYS[flag]
  if (!labelKey) return null
  const urgent = ['adolescent', 'twins', 'post_term', 'guardian_consent_pending'].includes(flag)
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${urgent ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>
      {t(labelKey)}
    </span>
  )
}

const TAB_ITEMS = [
  { id: 'overview', labelKey: 'overview' },
  { id: 'danger', labelKey: 'dangerSigns' },
  { id: 'birth', labelKey: 'birthPrep' },
  { id: 'education', labelKey: 'educationSchedule' },
  { id: 'ai', labelKey: 'aiInsights' },
  { id: 'referrals', labelKey: 'referrals' },
  { id: 'visits', labelKey: 'visits' },
]

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useLanguage()
  const user = getUser()
  const readOnly = user?.role === 'hospital'
  const isNurse = user?.role === 'nurse'

  const [patient, setPatient] = useState(null)
  const [visits, setVisits] = useState([])
  const [education, setEducation] = useState([])
  const [aiInsights, setAiInsights] = useState([])
  const [hospitals, setHospitals] = useState([])
  const [tab, setTab] = useState('overview')
  const [referOpen, setReferOpen] = useState(false)
  const [referralForm, setReferralForm] = useState({ hospitalId: '', reason: '', urgency: 'emergency' })
  const [prepForm, setPrepForm] = useState({})
  const [dangerForm, setDangerForm] = useState({ sign_type: 'bleeding', description: '' })
  const [saving, setSaving] = useState(false)

  async function load() {
    const [p, f, v, edu, insights] = await Promise.all([
      api.pregnancy(id),
      api.facilities(),
      api.visits(id).catch(() => []),
      api.educationSchedule(id).catch(() => []),
      api.aiInsights(id).catch(() => []),
    ])
    setPatient(p)
    setVisits(v)
    setEducation(edu)
    setAiInsights(insights)
    const hospitalList = f.filter((x) => x.type === 'hospital')
    setHospitals(hospitalList)
    if (p.birth_prep) setPrepForm(p.birth_prep)
    if (hospitalList[0]) setReferralForm((r) => ({ ...r, hospitalId: hospitalList[0].id }))
  }

  useEffect(() => { load() }, [id])

  async function savePrep() {
    setSaving(true)
    await api.updateBirthPrep(id, prepForm)
    await load()
    setSaving(false)
  }

  async function addDangerSign(e) {
    e.preventDefault()
    setSaving(true)
    await api.addDangerSign(id, dangerForm)
    setDangerForm({ sign_type: 'bleeding', description: '' })
    await load()
    setSaving(false)
  }

  async function sendEducation() {
    setSaving(true)
    await api.sendEducation(id)
    await load()
    setSaving(false)
  }

  async function refreshAi() {
    setSaving(true)
    await api.refreshAiTriage(id)
    await load()
    setSaving(false)
  }

  async function discharge(status) {
    const statusLabel = status.replace('_', ' ')
    if (!window.confirm(t('markPatientConfirm').replace('{status}', statusLabel))) return
    await api.updatePregnancyStatus(id, status)
    await load()
  }

  async function issueReferral(e) {
    e.preventDefault()
    if (patient.status !== 'active') return
    await api.createReferral({
      pregnancy_id: Number(id),
      to_facility_id: Number(referralForm.hospitalId),
      urgency: referralForm.urgency,
      reason: referralForm.reason,
    })
    setReferOpen(false)
    load()
  }

  async function recordGuardianConsent() {
    setSaving(true)
    await api.updatePregnancyCare(id, { guardian_consent_recorded: true })
    await load()
    setSaving(false)
  }

  if (!patient) return <LoadingScreen />

  const patientLang = LANGUAGES.find((l) => l.code === patient.language)?.label || LANGUAGES[0].label
  const pathway = patient.care_pathway

  return (
    <div className="space-y-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-brand-600">
        <ArrowLeft size={16} /> {t('back')}
      </button>

      <div className="card-panel p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900">{patient.first_name} {patient.last_name}</h1>
              <RiskBadge level={patient.risk_level} />
            </div>
            {pathway?.care_flags?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {pathway.care_flags.map((flag) => (
                  <CareFlagBadge key={flag} flag={flag} t={t} />
                ))}
              </div>
            )}
            <p className="mt-1 font-mono text-sm text-slate-500">{patient.ref_number}</p>
            <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600">
              <span>{patient.weeks_pregnant} {t('weeksPregnantShort')}</span>
              {patient.edd && <span className="flex items-center gap-1"><Calendar size={14} /> {t('edd')} {new Date(patient.edd).toLocaleDateString()}</span>}
              <span>{t('age')} {patient.age}</span>
              <span>{patient.village}</span>
              {patient.phone && <span>{patient.phone}</span>}
            </div>
          </div>
          {isNurse && patient.status === 'active' && (
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" onClick={() => setReferOpen(true)}>{t('createReferral')}</button>
              <button className="btn-secondary" onClick={sendEducation} disabled={saving}>
                <GraduationCap size={14} /> {t('sendEducation')}
              </button>
              <button className="btn-secondary" onClick={() => discharge('discharged')}>{t('discharge')}</button>
            </div>
          )}
        </div>

        <div className="mt-6 flex gap-1 overflow-x-auto border-b border-slate-100">
          {TAB_ITEMS.map(({ id: tabId, labelKey }) => (
            <button
              key={tabId}
              onClick={() => setTab(tabId)}
              className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium transition ${
                tab === tabId ? 'border-b-2 border-brand-500 text-brand-600' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {t(labelKey)}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {tab === 'overview' && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase text-slate-400">{t('medicalHistory')}</p>
                <ul className="mt-2 space-y-1 text-sm">
                  <li>{t('previousCsLabel')}: {patient.previous_cs ? t('yes') : t('no')}</li>
                  <li>{t('hypertension')}: {patient.hypertension ? t('yes') : t('no')}</li>
                  <li>{t('multipleGestation')}: {patient.multiple_gestation ? t('yes') : t('no')}</li>
                  <li>{t('gravidaParity').replace('{g}', patient.gravida ?? pathway?.gravida ?? 1).replace('{p}', patient.parity ?? pathway?.parity ?? 0)}</li>
                  <li>{t('status')}: <span className="capitalize">{patient.status.replace('_', ' ')}</span></li>
                  <li>{t('consentLabel')}: {patient.consent_recorded ? t('yes') : t('no')}</li>
                  {patient.age != null && patient.age < 18 && (
                    <li className="flex flex-wrap items-center gap-2">
                      {t('guardianConsent')}: {patient.guardian_consent_recorded ? t('yes') : t('no')}
                      {isNurse && !patient.guardian_consent_recorded && (
                        <button type="button" className="btn-secondary !py-1 !text-xs" onClick={recordGuardianConsent} disabled={saving}>
                          {t('recordGuardianConsent')}
                        </button>
                      )}
                    </li>
                  )}
                  <li className="flex items-center gap-2 pt-2">
                    <span>{t('language')}:</span>
                    <span className="font-medium">{patientLang}</span>
                  </li>
                  <li>{t('whatsappOptIn')}: {patient.whatsapp_opt_in ? t('yes') : t('no')}</li>
                </ul>
              </div>
              {pathway && (
                <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4 md:col-span-2">
                  <p className="text-xs font-semibold uppercase text-amber-700">{t('carePathway')}</p>
                  <div className="mt-2 grid gap-3 text-sm sm:grid-cols-2">
                    <p><span className="font-medium">{t('trimester')}:</span> {pathway.trimester_label}</p>
                    <p><span className="font-medium">{t('gestationStage')}:</span> {pathway.gestation_stage_label}</p>
                    {pathway.days_since_last_visit != null && (
                      <p><span className="font-medium">{t('daysSinceVisit')}:</span> {pathway.days_since_last_visit}</p>
                    )}
                    <p><span className="font-medium">{t('mohccAncSchedule')}:</span> {pathway.mohcc_anc_weeks?.join(', ')}</p>
                  </div>
                  {pathway.anc_schedule?.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-semibold uppercase text-amber-600">{t('ancCalendar')}</p>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {pathway.anc_schedule.map((item) => (
                          <div key={item.week} className={`rounded-lg px-3 py-2 text-xs ${
                            item.status === 'overdue' ? 'bg-red-50 text-red-800' :
                            item.status === 'due' ? 'bg-amber-100 text-amber-900' :
                            item.status === 'completed' ? 'bg-green-50 text-green-800' :
                            'bg-white/80 text-slate-600'
                          }`}>
                            <span className="font-semibold">{t('week')} {item.week}</span>
                            <span className="ml-2 capitalize">
                              {item.status === 'completed' ? t('ancStatusCompleted') :
                               item.status === 'due' ? t('ancStatusDue') :
                               item.status === 'overdue' ? t('overdue') : t('ancStatusUpcoming')}
                            </span>
                            {item.estimated_due_date && (
                              <p className="text-[10px] opacity-80">{new Date(item.estimated_due_date).toLocaleDateString()}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {pathway.follow_up_tasks?.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-semibold uppercase text-amber-600">{t('followUpTasks')}</p>
                      <ul className="mt-2 space-y-2">
                        {pathway.follow_up_tasks.map((task) => (
                          <li key={task.code} className="rounded-lg bg-white/80 p-3 text-sm">
                            <span className={`mr-2 inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                              task.priority === 'emergency' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'
                            }`}>{task.priority}</span>
                            <span className="font-medium">{task.title}</span>
                            <p className="mt-1 text-slate-600">{task.detail}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {pathway.protocol_notes?.length > 0 && (
                    <div className="mt-4 text-xs text-amber-800/90">
                      <p className="font-semibold uppercase">{t('protocolNotes')}</p>
                      <ul className="mt-1 list-disc pl-4">
                        {pathway.protocol_notes.map((note) => <li key={note}>{note}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              {patient.birth_prep && (
                <div className="rounded-xl bg-brand-50 p-4">
                  <p className="text-xs font-semibold uppercase text-brand-600">{t('birthPrep')}</p>
                  <p className="mt-2 text-3xl font-bold text-brand-700">{patient.birth_prep.completed_pct}%</p>
                  <p className="text-xs text-brand-600">{t('checklistComplete')}</p>
                </div>
              )}
            </div>
          )}

          {tab === 'danger' && (
            <div className="space-y-4">
              {isNurse && patient.status === 'active' && (
                <form onSubmit={addDangerSign} className="rounded-xl border border-slate-200 p-4">
                  <p className="mb-3 text-sm font-semibold text-slate-700">{t('recordDangerSign')}</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <select className="input-field" value={dangerForm.sign_type} onChange={(e) => setDangerForm({ ...dangerForm, sign_type: e.target.value })}>
                      {DANGER_TYPES.map((d) => <option key={d.value} value={d.value}>{t(d.labelKey)}</option>)}
                    </select>
                    <input className="input-field" placeholder={t('notes')} value={dangerForm.description} onChange={(e) => setDangerForm({ ...dangerForm, description: e.target.value })} />
                  </div>
                  <button className="btn-primary mt-3" disabled={saving}>{saving ? t('saving') : t('recordDangerSign')}</button>
                </form>
              )}
              {patient.danger_signs?.length ? patient.danger_signs.map((d) => (
                <div key={d.id} className="rounded-xl border border-red-100 bg-red-50 p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="mt-0.5 text-red-500" size={18} />
                    <div>
                      <p className="font-semibold capitalize text-red-800">{t(DANGER_TYPES.find((x) => x.value === d.sign_type)?.labelKey || 'other')}</p>
                      {d.ai_brief && (
                        <p className="mt-2 rounded-lg bg-white/80 p-2 text-sm text-red-900">
                          <Brain size={12} className="mr-1 inline" /> {d.ai_brief}
                        </p>
                      )}
                      <p className="text-xs text-red-600">{new Date(d.reported_at).toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              )) : <p className="text-sm text-slate-500">{t('noDangerSigns')}</p>}
            </div>
          )}

          {tab === 'birth' && (
            <div className="max-w-lg space-y-4">
              {PREP_KEYS.map(({ key, labelKey }) => (
                <label key={key} className={`flex items-center gap-3 rounded-xl border border-slate-200 p-4 ${readOnly ? '' : 'cursor-pointer hover:bg-slate-50'}`}>
                  <input type="checkbox" checked={!!prepForm[key]} disabled={readOnly} onChange={(e) => setPrepForm({ ...prepForm, [key]: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-brand-500" />
                  <span className="text-sm font-medium">{t(labelKey)}</span>
                </label>
              ))}
              <div>
                <label className="mb-1 block text-sm font-medium">{t('escortPhone')}</label>
                <input className="input-field" disabled={readOnly} value={prepForm.escort_phone || ''} onChange={(e) => setPrepForm({ ...prepForm, escort_phone: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t('transportPlan')}</label>
                <input className="input-field" disabled={readOnly} value={prepForm.transport_plan || ''} onChange={(e) => setPrepForm({ ...prepForm, transport_plan: e.target.value })} />
              </div>
              {isNurse && <button className="btn-primary" onClick={savePrep} disabled={saving}>{saving ? t('saving') : t('saveBirthPlan')}</button>}
            </div>
          )}

          {tab === 'education' && (
            <div className="space-y-3">
              <p className="text-sm text-slate-500">{t('educationDesc')} ({patientLang})</p>
              {education.map((item) => (
                <div key={item.week} className={`rounded-xl border p-4 ${item.due ? 'border-teal-200 bg-teal-50' : 'border-slate-200'}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">{t('week')} {item.week}</span>
                    <span className={`text-xs font-bold uppercase ${item.due ? 'text-teal-600' : 'text-slate-400'}`}>{item.due ? t('due') : t('pending')}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{item.message}</p>
                </div>
              ))}
            </div>
          )}

          {tab === 'ai' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">{t('aiTriageDesc')}</p>
                {!readOnly && (
                  <button className="btn-secondary !text-xs" onClick={refreshAi} disabled={saving}>
                    <Brain size={14} /> {t('refreshAi')}
                  </button>
                )}
              </div>
              {aiInsights.length ? aiInsights.map((insight) => (
                <div key={insight.id} className="rounded-xl border border-violet-100 bg-violet-50 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase text-violet-600">{insight.insight_type.replace('_', ' ')}</span>
                    <span className="text-[10px] text-violet-500">{insight.ai_powered ? t('aiPowered') : t('ruleBased')}</span>
                  </div>
                  <p className="mt-2 text-sm text-violet-900">{insight.content}</p>
                  <p className="mt-1 text-xs text-violet-400">{new Date(insight.created_at).toLocaleString()} · {insight.language}</p>
                </div>
              )) : <p className="text-sm text-slate-500">{t('aiInsightsAppear')}</p>}
            </div>
          )}

          {tab === 'referrals' && (
            <div className="space-y-3">
              {patient.referrals?.length ? patient.referrals.map((r) => (
                <div key={r.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold">{r.ref_number}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize">{r.status.replace('_', ' ')}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{r.to_facility_name} · {t(r.urgency === 'emergency' ? 'emergency' : r.urgency === 'routine' ? 'routine' : 'urgent')}</p>
                  <p className="text-sm text-slate-500">{r.reason}</p>
                </div>
              )) : <p className="text-sm text-slate-500">{t('noReferralsYet')}</p>}
            </div>
          )}

          {tab === 'visits' && (
            <div className="space-y-3">
              {visits.length ? visits.map((v) => (
                <div key={v.id} className="rounded-xl border border-slate-200 p-4 text-sm">
                  <p className="font-medium capitalize">{v.visit_type.replace('_', ' ')}</p>
                  <p className="mt-1 text-xs text-slate-400">{new Date(v.visited_at).toLocaleString()}</p>
                </div>
              )) : <p className="text-sm text-slate-500">{t('noVisits')}</p>}
            </div>
          )}
        </div>
      </div>

      <Modal open={referOpen} title={t('createReferral')} onClose={() => setReferOpen(false)}>
        <form onSubmit={issueReferral} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">{t('destinationHospital')}</label>
            <select className="input-field" value={referralForm.hospitalId} onChange={(e) => setReferralForm({ ...referralForm, hospitalId: e.target.value })} required>
              {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{t('clinicalReason')}</label>
            <textarea className="input-field" rows={3} placeholder={t('clinicalReasonPlaceholder')} value={referralForm.reason} onChange={(e) => setReferralForm({ ...referralForm, reason: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{t('urgency')}</label>
            <select className="input-field" value={referralForm.urgency} onChange={(e) => setReferralForm({ ...referralForm, urgency: e.target.value })}>
              <option value="emergency">{t('emergency')}</option>
              <option value="urgent">{t('urgent')}</option>
              <option value="routine">{t('routine')}</option>
            </select>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setReferOpen(false)}>{t('cancel')}</button>
            <button type="submit" className="btn-primary">{t('issueReferral')}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
