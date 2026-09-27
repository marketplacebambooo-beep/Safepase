import { Link } from 'react-router-dom'
import { Calendar } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'

const FLAG_KEYS = {
  first_pregnancy: 'flagFirstPregnancy',
  adolescent: 'flagAdolescent',
  twins: 'flagTwins',
}

export default function AncCalendarPanel({ entries, loading, tall = false }) {
  const { t } = useLanguage()
  const listClass = tall ? 'max-h-[28rem] overflow-y-auto divide-y divide-slate-50' : 'max-h-72 overflow-y-auto divide-y divide-slate-50'

  if (loading) {
    return (
      <div className={`card-panel ${tall ? 'min-h-[28rem]' : ''} p-5`}>
        <p className="text-sm text-slate-500">{t('loadingAncCalendar')}</p>
      </div>
    )
  }

  return (
    <div className={`card-panel overflow-hidden ${tall ? 'min-h-[28rem]' : ''}`}>
      <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-5">
        <Calendar size={20} className="text-brand-600" />
        <h2 className="text-lg font-bold text-slate-900">{t('ancCalendar')}</h2>
        <span className="ml-auto rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-medium text-brand-700">
          {entries.length}
        </span>
      </div>
      {entries.length === 0 ? (
        <p className="p-5 text-sm text-slate-500">{t('noAncDue')}</p>
      ) : (
        <div className={listClass}>
          {entries.map((entry) => (
            <div key={`${entry.pregnancy_id}-${entry.anc_week}`} className="px-5 py-3 text-sm hover:bg-brand-50/40">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <Link to={`/patients/${entry.pregnancy_id}`} className="font-semibold text-brand-700 hover:underline">
                    {entry.patient_name}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {t('week')} {entry.anc_week} · {entry.weeks_pregnant}w · {entry.ref_number}
                  </p>
                  {entry.estimated_due_date && (
                    <p className="text-xs text-slate-400">
                      {t('estimatedDue')}: {new Date(entry.estimated_due_date).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                  entry.status === 'overdue' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'
                }`}>
                  {entry.status === 'overdue' ? t('overdue') : t('due')}
                </span>
              </div>
              {entry.care_flags?.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {entry.care_flags.filter((f) => FLAG_KEYS[f]).slice(0, 3).map((flag) => (
                    <span key={flag} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                      {t(FLAG_KEYS[flag])}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
