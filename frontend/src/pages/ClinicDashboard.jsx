import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, Baby, Plus, Search, Users } from 'lucide-react'
import { api } from '../api'
import { EmptyState, LoadingScreen, Modal, RiskBadge, StatCard } from '../components/UI'
import DashboardSummaryPanel from '../components/DashboardSummaryPanel'
import AncCalendarPanel from '../components/AncCalendarPanel'
import RiskChartPanel from '../components/RiskChartPanel'
import { LANGUAGES } from '../i18n/translations'
import { useLanguage } from '../i18n/LanguageContext'

function ReferralModal({ pregnancy, hospitals, onClose, onCreated }) {
  const { t } = useLanguage()
  const [hospitalId, setHospitalId] = useState(hospitals[0]?.id || '')
  const [reason, setReason] = useState('')
  const [urgency, setUrgency] = useState('urgent')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.createReferral({
        pregnancy_id: pregnancy.id,
        to_facility_id: Number(hospitalId),
        urgency,
        reason,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open title={t('createReferral')} onClose={onClose}>
      <div className="mb-4 flex items-center gap-3 rounded-xl bg-slate-50 p-4">
        <RiskBadge level={pregnancy.risk_level} />
        <div>
          <p className="font-semibold text-slate-900">{pregnancy.first_name} {pregnancy.last_name}</p>
          <p className="text-sm text-slate-500">{pregnancy.weeks_pregnant} {t('weeksPregnantShort')} · {pregnancy.village}</p>
        </div>
      </div>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium">{t('destinationHospital')}</label>
          <select className="input-field" value={hospitalId} onChange={(e) => setHospitalId(e.target.value)} required>
            {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">{t('clinicalReason')}</label>
          <textarea className="input-field" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required placeholder={t('clinicalReasonPlaceholder')} />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">{t('urgency')}</label>
          <select className="input-field" value={urgency} onChange={(e) => setUrgency(e.target.value)}>
            <option value="emergency">{t('emergency')}</option>
            <option value="urgent">{t('urgent')}</option>
            <option value="routine">{t('routine')}</option>
          </select>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t('cancel')}</button>
          <button type="submit" className="btn-primary" disabled={loading || !reason.trim()}>
            {loading ? t('issuingReferral') : t('issueReferral')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function RegisterPatientModal({ chws, onClose, onCreated }) {
  const { t } = useLanguage()
  const [form, setForm] = useState({
    first_name: '', last_name: '', age: '', weeks_pregnant: '', village: '', phone: '',
    chw_id: '', previous_cs: false, hypertension: false, multiple_gestation: false,
    gravida: '1', parity: '0',
    guardian_consent_recorded: false, language: 'en', whatsapp_opt_in: true,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.createPregnancy({
        first_name: form.first_name,
        last_name: form.last_name,
        age: Number(form.age),
        weeks_pregnant: Number(form.weeks_pregnant),
        village: form.village,
        phone: form.phone || null,
        chw_id: form.chw_id ? Number(form.chw_id) : null,
        previous_cs: form.previous_cs,
        hypertension: form.hypertension,
        multiple_gestation: form.multiple_gestation,
        fetal_count: form.multiple_gestation ? 2 : 1,
        gravida: Number(form.gravida),
        parity: Number(form.parity),
        guardian_consent_recorded: Number(form.age) >= 18 ? true : form.guardian_consent_recorded,
        consent_recorded: true,
        language: form.language,
        whatsapp_opt_in: form.whatsapp_opt_in,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }))

  return (
    <Modal open title={t('registerPatient')} onClose={onClose} wide>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium">{t('firstName')}</label>
          <input className="input-field" value={form.first_name} onChange={(e) => set('first_name', e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('lastName')}</label>
          <input className="input-field" value={form.last_name} onChange={(e) => set('last_name', e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('age')}</label>
          <input className="input-field" type="number" min="12" max="55" value={form.age} onChange={(e) => set('age', e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('weeks')}</label>
          <input className="input-field" type="number" min="1" max="42" value={form.weeks_pregnant} onChange={(e) => set('weeks_pregnant', e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('village')}</label>
          <input className="input-field" value={form.village} onChange={(e) => set('village', e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('phoneSms')}</label>
          <input className="input-field" placeholder="+263..." value={form.phone} onChange={(e) => set('phone', e.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-sm font-medium">{t('assignedChw')}</label>
          <select className="input-field" value={form.chw_id} onChange={(e) => set('chw_id', e.target.value)}>
            <option value="">{t('none')}</option>
            {chws.map((c) => <option key={c.id} value={c.id}>{c.name} — {c.village}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('language')}</label>
          <select className="input-field" value={form.language} onChange={(e) => set('language', e.target.value)}>
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm sm:col-span-2">
          <input type="checkbox" checked={form.whatsapp_opt_in} onChange={(e) => set('whatsapp_opt_in', e.target.checked)} />
          {t('whatsappInAddition')}
        </label>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('gravida')}</label>
          <input className="input-field" type="number" min="1" max="20" value={form.gravida} onChange={(e) => set('gravida', e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('parity')}</label>
          <input className="input-field" type="number" min="0" max="15" value={form.parity} onChange={(e) => {
            const p = e.target.value
            set('parity', p)
            if (Number(p) === 0) setForm((f) => ({ ...f, parity: p, gravida: f.gravida === '' || Number(f.gravida) < 1 ? '1' : f.gravida }))
            else setForm((f) => ({ ...f, parity: p, gravida: String(Math.max(Number(p) + 1, Number(f.gravida) || 1)) }))
          }} required />
          {Number(form.parity) === 0 && <p className="mt-1 text-xs text-amber-600">{t('flagFirstPregnancy')}</p>}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.previous_cs} onChange={(e) => set('previous_cs', e.target.checked)} />
          {t('previousCs')}
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.hypertension} onChange={(e) => set('hypertension', e.target.checked)} />
          {t('hypertension')}
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.multiple_gestation} onChange={(e) => set('multiple_gestation', e.target.checked)} />
          {t('multipleGestation')}
        </label>
        {Number(form.age) > 0 && Number(form.age) < 18 && (
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input type="checkbox" checked={form.guardian_consent_recorded} onChange={(e) => set('guardian_consent_recorded', e.target.checked)} />
            {t('guardianConsent')} <span className="text-xs text-amber-600">({t('guardianConsentRequired')})</span>
          </label>
        )}
        {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
        <div className="flex justify-end gap-3 sm:col-span-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t('cancel')}</button>
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? t('registering') : t('registerPatient')}</button>
        </div>
      </form>
    </Modal>
  )
}

export default function ClinicDashboard({ user }) {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const [pregnancies, setPregnancies] = useState([])
  const [chartPregnancies, setChartPregnancies] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [hospitals, setHospitals] = useState([])
  const [chws, setChws] = useState([])
  const [selected, setSelected] = useState(null)
  const [registerOpen, setRegisterOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [ancCalendar, setAncCalendar] = useState([])
  const [ancLoading, setAncLoading] = useState(true)

  async function loadAnc() {
    setAncLoading(true)
    try {
      const entries = await api.ancCalendar().catch(() => [])
      setAncCalendar(entries)
    } finally {
      setAncLoading(false)
    }
  }

  async function load() {
    setLoading(true)
    try {
      const [p, allP, s, f, c] = await Promise.all([
        api.pregnancies({ risk: filter, q: search || undefined }),
        api.pregnancies(),
        api.analytics(),
        api.facilities(),
        api.chws(),
      ])
      setPregnancies(p)
      setChartPregnancies(allP)
      setStats(s)
      setHospitals(f.filter((x) => x.type === 'hospital'))
      setChws(c)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(load, search ? 300 : 0)
    return () => clearTimeout(t)
  }, [filter, search])

  useEffect(() => { loadAnc() }, [])

  const sorted = [...pregnancies].sort((a, b) => {
    const order = { emergency: 0, red: 1, amber: 2, green: 3 }
    return (order[a.risk_level] ?? 4) - (order[b.risk_level] ?? 4)
  })

  const riskFilters = [
    { key: 'all', label: t('riskAll') },
    { key: 'emergency', label: t('riskEmergency') },
    { key: 'red', label: t('riskRed') },
    { key: 'amber', label: t('riskAmber') },
    { key: 'green', label: t('riskGreen') },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('clinicDashboard')}</h1>
          <p className="text-slate-500">{user.facility_name || t('clinicDefault')} — {t('monitorSubtitle')}</p>
        </div>
        <button className="btn-primary" onClick={() => setRegisterOpen(true)}>
          <Plus size={16} /> {t('registerPatient')}
        </button>
      </div>

      <div className="space-y-6">
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard icon={Users} label={t('activePregnancies')} value={stats.active_pregnancies} />
          <StatCard icon={AlertTriangle} label={t('highRisk')} value={stats.high_risk} accent="red" />
          <StatCard icon={Baby} label={t('pendingReferrals')} value={stats.pending_referrals} accent="amber" />
          <StatCard icon={Users} label={t('referralsMonth')} value={stats.referrals_this_month} accent="teal" />
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <RiskChartPanel pregnancies={chartPregnancies} />
        </div>
        <div className="xl:col-span-2">
          <AncCalendarPanel entries={ancCalendar} loading={ancLoading} tall />
        </div>
      </div>

      <div className="card-panel overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {riskFilters.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  filter === key ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="relative max-w-xs flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              className="input-field pl-9"
              placeholder={t('searchClinicPlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="border-b border-slate-100 px-5 py-5">
          <DashboardSummaryPanel />
        </div>

        {loading ? <LoadingScreen /> : sorted.length === 0 ? (
          <EmptyState icon={Users} title={t('noPatients')} description={t('noPatientsDesc')} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-3">{t('patient')}</th>
                  <th className="px-5 py-3">{t('weeksCol')}</th>
                  <th className="px-5 py-3">{t('village')}</th>
                  <th className="px-5 py-3">{t('riskCol')}</th>
                  <th className="px-5 py-3">{t('reference')}</th>
                  <th className="px-5 py-3 text-right">{t('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((p) => (
                  <tr key={p.id} className="border-b border-slate-50 transition hover:bg-brand-50/30">
                    <td className="px-5 py-4">
                      <button onClick={() => navigate(`/patients/${p.id}`)} className="font-semibold text-brand-700 hover:underline">
                        {p.first_name} {p.last_name}
                      </button>
                      <p className="text-xs text-slate-400">{t('age')} {p.age}</p>
                    </td>
                    <td className="px-5 py-4">{p.weeks_pregnant}w</td>
                    <td className="px-5 py-4">{p.village}</td>
                    <td className="px-5 py-4"><RiskBadge level={p.risk_level} /></td>
                    <td className="px-5 py-4 font-mono text-xs">{p.ref_number}</td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Link to={`/patients/${p.id}`} className="btn-secondary !py-1.5 !text-xs">{t('view')}</Link>
                        {['emergency', 'red', 'amber'].includes(p.risk_level) && (
                          <button className="btn-primary !py-1.5 !text-xs" onClick={() => setSelected(p)}>{t('refer')}</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </div>

      {selected && (
        <ReferralModal pregnancy={selected} hospitals={hospitals} onClose={() => setSelected(null)} onCreated={load} />
      )}
      {registerOpen && (
        <RegisterPatientModal chws={chws} onClose={() => setRegisterOpen(false)} onCreated={() => { load(); loadAnc() }} />
      )}
    </div>
  )
}
