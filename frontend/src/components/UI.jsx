import { useLanguage } from '../i18n/LanguageContext'

const RISK_LABEL_KEYS = {
  green: 'riskGreen',
  amber: 'riskAmber',
  red: 'riskRed',
  emergency: 'riskEmergency',
}

export function RiskBadge({ level, size = 'md' }) {
  const { t } = useLanguage()
  const styles = {
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    amber: 'bg-amber-50 text-amber-800 ring-amber-200',
    red: 'bg-red-50 text-red-700 ring-red-200',
    emergency: 'bg-red-600 text-white ring-red-700 animate-pulse',
  }
  const sizes = { sm: 'px-2 py-0.5 text-[10px]', md: 'px-2.5 py-1 text-xs' }
  const label = t(RISK_LABEL_KEYS[level] || 'riskGreen')
  return (
    <span className={`inline-flex rounded-full font-semibold uppercase tracking-wide ring-1 ring-inset ${styles[level] || styles.green} ${sizes[size]}`}>
      {label}
    </span>
  )
}

export function StatCard({ icon: Icon, label, value, accent = 'brand' }) {
  const accents = {
    brand: 'from-brand-500 to-brand-600',
    red: 'from-red-500 to-red-600',
    amber: 'from-amber-500 to-amber-600',
    teal: 'from-teal-500 to-teal-600',
    sky: 'from-sky-500 to-brand-500',
  }
  return (
    <div className="card-panel p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-4xl font-bold text-slate-900">{value}</p>
        </div>
        <div className={`rounded-xl bg-gradient-to-br ${accents[accent]} p-3.5 text-white shadow-sm`}>
          <Icon size={24} />
        </div>
      </div>
    </div>
  )
}

export function LoadingScreen() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500" />
    </div>
  )
}

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 rounded-full bg-slate-100 p-4 text-slate-400">
        <Icon size={32} />
      </div>
      <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} rounded-2xl bg-white p-6 shadow-modal`}>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function ReferralStepper({ status }) {
  const { t } = useLanguage()
  const steps = [
    { key: 'issued', label: t('statusIssued') },
    { key: 'acknowledged', label: t('statusAcknowledged') },
    { key: 'in_transit', label: t('statusInTransit') },
    { key: 'arrived', label: t('statusArrived') },
    { key: 'completed', label: t('statusCompleted') },
  ]
  const order = steps.map((s) => s.key)
  const current = order.indexOf(status)

  return (
    <div className="flex items-center gap-1">
      {steps.map((step, i) => {
        const done = i <= current && current >= 0
        const active = i === current
        return (
          <div key={step.key} className="flex flex-1 flex-col items-center">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${done ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-400'} ${active ? 'ring-4 ring-brand-100' : ''}`}>
              {i + 1}
            </div>
            <span className={`mt-1 text-[10px] font-medium ${done ? 'text-brand-600' : 'text-slate-400'}`}>{step.label}</span>
          </div>
        )
      })}
    </div>
  )
}
