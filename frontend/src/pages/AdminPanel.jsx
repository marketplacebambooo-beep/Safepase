import { useEffect, useState } from 'react'
import { api } from '../api'
import { LoadingScreen, Modal } from '../components/UI'
import DashboardSummaryPanel from '../components/DashboardSummaryPanel'
import { useLanguage } from '../i18n/LanguageContext'

const TAB_KEYS = [
  { key: 'District', labelKey: 'tabDistrict' },
  { key: 'Compliance', labelKey: 'tabCompliance' },
  { key: 'Facilities', labelKey: 'tabFacilities' },
  { key: 'Users', labelKey: 'tabUsers' },
  { key: 'CHWs', labelKey: 'tabChws' },
]

const ADD_KEYS = {
  Facilities: 'addFacility',
  Users: 'addUser',
  CHWs: 'addChw',
}

const ROLE_KEYS = { nurse: 'roleNurse', hospital: 'roleHospital', admin: 'roleAdmin' }

export default function AdminPanel() {
  const { t } = useLanguage()
  const [tab, setTab] = useState('District')
  const [loading, setLoading] = useState(true)
  const [districts, setDistricts] = useState([])
  const [facilities, setFacilities] = useState([])
  const [users, setUsers] = useState([])
  const [chws, setChws] = useState([])
  const [compliance, setCompliance] = useState(null)
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState({})
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [d, f, u, c, comp] = await Promise.all([
        api.districtAnalytics(),
        api.admin.facilities(),
        api.admin.users(),
        api.admin.chws(),
        api.complianceReport().catch(() => null),
      ])
      setDistricts(d)
      setFacilities(f)
      setUsers(u)
      setChws(c)
      setCompliance(comp)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function save(e) {
    e.preventDefault()
    setError('')
    try {
      if (modal === 'facility') {
        await api.admin.createFacility({ ...form, type: form.type || 'clinic' })
      } else if (modal === 'user') {
        await api.admin.createUser(form)
      } else if (modal === 'chw') {
        await api.admin.createChw(form)
      }
      setModal(null)
      setForm({})
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const modalTitles = {
    facility: t('addFacility'),
    user: t('addUser'),
    chw: t('addChw'),
  }

  if (loading) return <LoadingScreen />

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('adminConsole')}</h1>
          <p className="text-slate-500">{t('adminSubtitle')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {tab !== 'District' && tab !== 'Compliance' && (
            <button className="btn-primary" onClick={() => { setModal(tab.slice(0, -1).toLowerCase()); setForm({}) }}>
              {t(ADD_KEYS[tab])}
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {TAB_KEYS.map(({ key, labelKey }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === key ? 'bg-brand-50 text-brand-700' : 'text-slate-500 hover:bg-slate-100'}`}
          >
            {t(labelKey)}
          </button>
        ))}
      </div>

      {tab === 'District' && (
        <div className="grid gap-4 md:grid-cols-2">
          {districts.map((d) => (
            <div key={d.district} className="card-panel p-5">
              <h3 className="text-lg font-bold text-slate-900">{d.district}</h3>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">{t('activePregnancies')}</span><p className="text-xl font-bold">{d.active_pregnancies}</p></div>
                <div><span className="text-slate-500">{t('highRisk')}</span><p className="text-xl font-bold text-amber-600">{d.high_risk}</p></div>
                <div><span className="text-slate-500">{t('pendingReferrals')}</span><p className="text-xl font-bold">{d.pending_referrals}</p></div>
                <div><span className="text-slate-500">{t('referralsMonth')}</span><p className="text-xl font-bold text-brand-600">{d.referrals_this_month}</p></div>
              </div>
              <p className="mt-4 text-xs text-slate-400">{d.facilities.length} {t('facilitiesCount')}</p>
            </div>
          ))}
        </div>
      )}

      {tab === 'Compliance' && compliance && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900">{t('complianceReport')}</h2>
            <p className="text-sm text-slate-500">{t('complianceSubtitle')}</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="card-panel p-4">
              <p className="text-xs text-slate-500">{t('totalAdolescent')}</p>
              <p className="text-2xl font-bold">{compliance.total_adolescent_active}</p>
            </div>
            <div className="card-panel p-4">
              <p className="text-xs text-slate-500">{t('guardianConsentPending')}</p>
              <p className="text-2xl font-bold text-red-600">{compliance.guardian_consent_pending}</p>
            </div>
            <div className="card-panel p-4">
              <p className="text-xs text-slate-500">{t('primigravidaCount')}</p>
              <p className="text-2xl font-bold text-brand-600">{compliance.primigravida_active}</p>
            </div>
          </div>
          {compliance.districts.length === 0 ? (
            <p className="text-sm text-slate-500">{t('noComplianceGaps')}</p>
          ) : (
            <>
              <DashboardSummaryPanel />
              {compliance.districts.map((district) => (
              <div key={district.district} className="card-panel overflow-hidden">
                <div className="border-b border-slate-100 px-5 py-4">
                  <h3 className="font-semibold text-slate-900">{district.district}</h3>
                  <p className="text-xs text-red-600">{district.pending_count} {t('guardianConsentPending').toLowerCase()}</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b text-xs text-slate-500">
                        <th className="p-3">{t('patient')}</th>
                        <th>{t('age')}</th>
                        <th>{t('weeksCol')}</th>
                        <th>{t('gravida')} / {t('parity')}</th>
                        <th>{t('facility')}</th>
                        <th>{t('reference')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {district.cases.map((c) => (
                        <tr key={c.pregnancy_id} className="border-b border-slate-50">
                          <td className="p-3 font-medium">{c.patient_name}</td>
                          <td>{c.age}</td>
                          <td>{c.weeks_pregnant}w</td>
                          <td>G{c.gravida}P{c.parity}{c.first_pregnancy ? ' · 1st' : ''}</td>
                          <td>{c.facility_name}</td>
                          <td className="font-mono text-xs">{c.ref_number}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            </>
          )}
        </div>
      )}

      {tab === 'Facilities' && (
        <div className="card-panel overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <DashboardSummaryPanel />
          </div>
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b text-slate-500"><th className="p-3">{t('name')}</th><th>{t('type')}</th><th>{t('district')}</th><th>{t('phone')}</th></tr></thead>
            <tbody>
              {facilities.map((f) => (
                <tr key={f.id} className="border-b border-slate-50"><td className="p-3 font-medium">{f.name}</td><td className="capitalize">{f.type === 'hospital' ? t('facilityTypeHospital') : t('facilityTypeClinic')}</td><td>{f.district}</td><td>{f.phone || '—'}</td></tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {tab === 'Users' && (
        <div className="card-panel overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <DashboardSummaryPanel />
          </div>
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b text-slate-500"><th className="p-3">{t('name')}</th><th>{t('emailCol')}</th><th>{t('role')}</th><th>{t('facility')}</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-50"><td className="p-3 font-medium">{u.name}</td><td>{u.email}</td><td>{t(ROLE_KEYS[u.role] || 'roleNurse')}</td><td>{u.facility_name || '—'}</td></tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {tab === 'CHWs' && (
        <div className="card-panel overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <DashboardSummaryPanel />
          </div>
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b text-slate-500"><th className="p-3">{t('name')}</th><th>{t('phone')}</th><th>{t('village')}</th><th>{t('facilityId')}</th></tr></thead>
            <tbody>
              {chws.map((c) => (
                <tr key={c.id} className="border-b border-slate-50"><td className="p-3 font-medium">{c.name}</td><td>{c.phone}</td><td>{c.village}</td><td>{c.facility_id}</td></tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      </div>

      <Modal open={!!modal} title={modalTitles[modal] || ''} onClose={() => setModal(null)}>
        <form onSubmit={save} className="space-y-4">
          {modal === 'facility' && (
            <>
              <input className="input-field" placeholder={t('name')} value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <select className="input-field" value={form.type || 'clinic'} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="clinic">{t('facilityTypeClinic')}</option>
                <option value="hospital">{t('facilityTypeHospital')}</option>
              </select>
              <input className="input-field" placeholder={t('district')} value={form.district || ''} onChange={(e) => setForm({ ...form, district: e.target.value })} />
              <input className="input-field" placeholder={t('phone')} value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </>
          )}
          {modal === 'user' && (
            <>
              <input className="input-field" placeholder={t('name')} value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <input className="input-field" type="email" placeholder={t('email')} value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              <input className="input-field" type="password" placeholder={t('passwordMin8')} minLength={8} value={form.password || ''} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
              <select className="input-field" value={form.role || 'nurse'} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="nurse">{t('roleNurse')}</option>
                <option value="hospital">{t('roleHospital')}</option>
                <option value="admin">{t('roleAdmin')}</option>
              </select>
              <input className="input-field" type="number" placeholder={t('facilityIdOptional')} value={form.facility_id || ''} onChange={(e) => setForm({ ...form, facility_id: e.target.value ? Number(e.target.value) : null })} />
            </>
          )}
          {modal === 'chw' && (
            <>
              <input className="input-field" placeholder={t('name')} value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <input className="input-field" placeholder={t('phoneSms')} value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
              <input className="input-field" placeholder={t('village')} value={form.village || ''} onChange={(e) => setForm({ ...form, village: e.target.value })} />
              <input className="input-field" type="number" placeholder={t('facilityId')} value={form.facility_id || ''} onChange={(e) => setForm({ ...form, facility_id: Number(e.target.value) })} required />
            </>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setModal(null)}>{t('cancel')}</button>
            <button type="submit" className="btn-primary">{t('save')}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
