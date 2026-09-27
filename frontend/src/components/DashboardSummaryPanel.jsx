import { useCallback, useEffect, useState } from 'react'
import FormattedText from './FormattedText'
import { AlertCircle, Brain, ChevronDown, RefreshCw } from 'lucide-react'
import { api } from '../api'
import { useLanguage } from '../i18n/LanguageContext'

export default function DashboardSummaryPanel() {
  const { t } = useLanguage()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.dashboardSummary()
      setData(res)
      setLoaded(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  function toggle() {
    const next = !open
    setOpen(next)
    if (next && !loaded && !loading) load()
  }

  useEffect(() => {
    if (open && !loaded && !loading) load()
  }, [open, loaded, loading, load])

  const alertCount = data?.highlights?.length ?? 0

  return (
    <div className="w-full overflow-hidden rounded-2xl border border-brand-200 bg-white shadow-card">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="group flex w-full items-center gap-3 bg-gradient-to-r from-brand-50 to-teal-50 px-5 py-4 text-left transition hover:from-brand-100 hover:to-teal-100"
      >
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-500 text-white shadow-sm">
          <Brain size={22} />
        </div>
        <div className="min-w-0 flex-1">
          <span className="block text-base font-bold text-brand-800 group-hover:text-brand-900">
            {t('dashboardSummary')}
          </span>
          <span className="mt-0.5 block text-sm text-brand-600/80">{t('dashboardSummarySubtitle')}</span>
        </div>
        {alertCount > 0 && !open && (
          <span className="rounded-full bg-amber-500 px-2.5 py-1 text-xs font-bold text-white">
            {alertCount}
          </span>
        )}
        <ChevronDown
          size={22}
          className={`shrink-0 text-brand-600 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="border-t border-brand-100">
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-6 py-3">
            <p className="text-sm font-medium text-slate-600">{t('dashboardSummarySubtitle')}</p>
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50 disabled:opacity-50"
              title={t('refreshSummary')}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              {t('refreshSummary')}
            </button>
          </div>

          <div className="min-h-[220px] space-y-5 px-6 py-6">
            {loading && !data && (
              <div className="space-y-3">
                <div className="h-4 animate-pulse rounded-md bg-slate-100" />
                <div className="h-4 w-11/12 animate-pulse rounded-md bg-slate-100" />
                <div className="h-4 w-10/12 animate-pulse rounded-md bg-slate-100" />
                <div className="h-4 w-8/12 animate-pulse rounded-md bg-slate-100" />
              </div>
            )}

            {error && (
              <p className="flex items-start gap-2 text-sm text-red-600">
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                {error}
              </p>
            )}

            {data && (
              <>
                <FormattedText text={data.summary} />

                {data.highlights?.length > 0 && (
                  <div>
                    <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">
                      {t('keyAlerts')}
                    </p>
                    <ul className="space-y-2.5">
                      {data.highlights.map((item) => (
                        <li
                          key={item}
                          className="flex items-start gap-3 rounded-xl border border-amber-100 bg-amber-50/80 px-4 py-3 text-sm text-amber-900"
                        >
                          <AlertCircle size={16} className="mt-0.5 shrink-0 text-amber-600" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-400">
                  <span>{data.ai_powered ? t('aiPowered') : t('ruleBased')}</span>
                  {data.generated_at && (
                    <span>{new Date(data.generated_at).toLocaleString()}</span>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="border-t border-slate-100 bg-slate-50/40 px-6 py-3">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="w-full text-center text-sm font-medium text-slate-500 hover:text-brand-600"
            >
              {t('closeBriefing')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
