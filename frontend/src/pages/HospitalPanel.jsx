import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Ambulance, CheckCircle, Clock, Hospital, User, XCircle } from 'lucide-react'
import { api } from '../api'
import { EmptyState, LoadingScreen, ReferralStepper } from '../components/UI'
import DashboardSummaryPanel from '../components/DashboardSummaryPanel'
import { useLanguage } from '../i18n/LanguageContext'

function getStatusActions(t) {
  return {
    issued: [{ status: 'acknowledged', label: t('acknowledge'), icon: CheckCircle }],
    acknowledged: [
      { status: 'in_transit', label: t('patientDeparted'), icon: Ambulance },
      { status: 'arrived', label: t('patientArrived'), icon: Hospital },
      { status: 'no_show', label: t('noShow'), icon: XCircle, variant: 'danger' },
      { status: 'cancelled', label: t('cancelReferral'), icon: XCircle, variant: 'muted' },
    ],
    in_transit: [
      { status: 'arrived', label: t('patientArrived'), icon: Hospital },
      { status: 'no_show', label: t('noShow'), icon: XCircle, variant: 'danger' },
      { status: 'cancelled', label: t('cancelReferral'), icon: XCircle, variant: 'muted' },
    ],
    arrived: [
      { status: 'completed', label: t('treatmentComplete'), icon: CheckCircle },
      { status: 'cancelled', label: t('cancelReferral'), icon: XCircle, variant: 'muted' },
    ],
  }
}

const URGENCY_KEYS = { emergency: 'emergency', urgent: 'urgent', routine: 'routine' }

export default function HospitalPanel({ user }) {
  const { t } = useLanguage()
  const statusActions = getStatusActions(t)
  const [referrals, setReferrals] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(null)

  async function load() {
    try {
      const [r, s] = await Promise.all([api.referrals(), api.analytics()])
      setReferrals(r)
      setStats(s)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [])

  async function updateStatus(id, status) {
    setUpdating(id)
    await api.updateReferralStatus(id, status)
    await load()
    setUpdating(null)
  }

  const active = referrals.filter((r) => !['completed', 'cancelled', 'no_show'].includes(r.status))

  if (loading) return <LoadingScreen />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t('hospitalPanel')}</h1>
        <p className="text-slate-500">{user.facility_name || t('hospitalDefault')} — {t('hospitalSubtitle')}</p>
      </div>

      <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card-panel p-5">
          <p className="text-sm text-slate-500">{t('incoming')}</p>
          <p className="text-3xl font-bold text-red-600">{active.length}</p>
        </div>
        <div className="card-panel p-5">
          <p className="text-sm text-slate-500">{t('emergency')}</p>
          <p className="text-3xl font-bold text-amber-600">{active.filter((r) => r.urgency === 'emergency').length}</p>
        </div>
        <div className="card-panel p-5">
          <p className="text-sm text-slate-500">{t('completedToday')}</p>
          <p className="text-3xl font-bold text-teal-600">{stats?.completed_today ?? 0}</p>
        </div>
      </div>

      {active.length === 0 ? (
        <div className="card-panel">
          <div className="border-b border-slate-100 px-5 py-4">
            <DashboardSummaryPanel />
          </div>
          <EmptyState icon={Hospital} title={t('noReferrals')} description={t('noReferralsDescSms')} />
        </div>
      ) : (
        <div className="space-y-4">
          <DashboardSummaryPanel />
          {active.map((r) => (
            <div
              key={r.id}
              className={`card-panel overflow-hidden ${r.urgency === 'emergency' ? 'ring-2 ring-red-200' : ''}`}
            >
              <div className={`px-6 py-3 ${r.urgency === 'emergency' ? 'bg-red-600 text-white' : 'bg-brand-500 text-white'}`}>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold">{r.ref_number}</span>
                  <span className="rounded-full bg-white/20 px-3 py-0.5 text-xs font-bold uppercase">{t(URGENCY_KEYS[r.urgency] || 'urgent')}</span>
                </div>
              </div>
              <div className="p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-slate-900">{r.patient_name}</h3>
                    <p className="text-slate-500">{r.patient_weeks} {t('weeksPregnantShort')}</p>
                    <p className="mt-2 text-sm"><strong>{t('from')}:</strong> {r.from_facility_name}</p>
                    <p className="text-sm"><strong>{t('reason')}:</strong> {r.reason}</p>
                    <p className="mt-2 flex items-center gap-1 text-xs text-slate-400">
                      <Clock size={12} /> {t('issued')} {new Date(r.issued_at).toLocaleString()}
                    </p>
                  </div>
                  <Link to={`/patients/${r.pregnancy_id}`} className="btn-secondary !text-xs shrink-0">
                    <User size={14} /> {t('viewPatient')}
                  </Link>
                </div>

                <div className="my-6">
                  <ReferralStepper status={r.status} />
                </div>

                <div className="flex flex-wrap gap-2">
                  {(statusActions[r.status] || []).map(({ status, label, icon: Icon, variant }) => (
                    <button
                      key={status}
                      className={variant === 'danger' ? 'rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-xs font-semibold text-red-700 hover:bg-red-100' : variant === 'muted' ? 'btn-secondary !text-xs' : 'btn-primary !text-xs'}
                      disabled={updating === r.id}
                      onClick={() => updateStatus(r.id, status)}
                    >
                      <Icon size={14} /> {updating === r.id ? t('updating') : label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </div>
  )
}
