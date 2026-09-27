import { ChartColumn } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'

const RISK_LEVELS = [
  { key: 'emergency', labelKey: 'riskEmergency', bar: 'bg-red-600', badge: 'bg-red-100 text-red-800' },
  { key: 'red', labelKey: 'riskRed', bar: 'bg-red-400', badge: 'bg-red-50 text-red-700' },
  { key: 'amber', labelKey: 'riskAmber', bar: 'bg-amber-400', badge: 'bg-amber-50 text-amber-800' },
  { key: 'green', labelKey: 'riskGreen', bar: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-800' },
]

export default function RiskChartPanel({ pregnancies = [] }) {
  const { t } = useLanguage()

  const counts = RISK_LEVELS.map(({ key }) =>
    pregnancies.filter((p) => p.risk_level === key).length
  )
  const total = counts.reduce((sum, n) => sum + n, 0)
  const max = Math.max(...counts, 1)

  return (
    <div className="card-panel overflow-hidden">
      <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500 text-white shadow-sm">
          <ChartColumn size={22} />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">{t('riskChartTitle')}</h2>
          <p className="text-sm text-slate-500">{t('riskChartSubtitle')}</p>
        </div>
        <span className="ml-auto rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
          {total} {t('activePregnancies').toLowerCase()}
        </span>
      </div>

      {total === 0 ? (
        <p className="px-6 py-16 text-center text-sm text-slate-500">{t('noPatientsForChart')}</p>
      ) : (
        <div className="px-6 py-8">
          <div className="flex h-64 items-end justify-center gap-5 sm:gap-8 md:gap-10">
            {RISK_LEVELS.map(({ key, labelKey, bar }, index) => {
              const count = counts[index]
              const height = Math.max((count / max) * 100, count > 0 ? 12 : 4)
              return (
                <div key={key} className="flex min-w-0 flex-1 flex-col items-center">
                  <span className="mb-2 text-lg font-bold text-slate-800">{count}</span>
                  <div className="flex h-52 w-full max-w-[88px] items-end">
                    <div
                      className={`w-full rounded-t-xl shadow-sm transition-all ${bar}`}
                      style={{ height: `${height}%` }}
                      title={`${t(labelKey)}: ${count}`}
                    />
                  </div>
                  <span className={`mt-3 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${RISK_LEVELS[index].badge}`}>
                    {t(labelKey)}
                  </span>
                </div>
              )
            })}
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-4">
            {RISK_LEVELS.map(({ key, labelKey, badge }, index) => {
              const count = counts[index]
              const pct = total ? Math.round((count / total) * 100) : 0
              return (
                <div key={`${key}-stat`} className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 text-center">
                  <p className={`text-xs font-bold uppercase tracking-wide ${badge.split(' ')[1]}`}>{t(labelKey)}</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">{pct}%</p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
