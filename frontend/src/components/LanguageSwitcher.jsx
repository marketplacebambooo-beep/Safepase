import { LANGUAGES } from '../i18n/translations'
import { useLanguage } from '../i18n/LanguageContext'

const styles = {
  default: 'rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-600',
  light: 'rounded-lg border border-white/30 bg-white/15 px-3 py-2 text-sm font-medium text-white backdrop-blur-sm',
  header: 'rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700',
}

export default function LanguageSwitcher({ className = '', variant = 'default', showLabel = false }) {
  const { lang, setLang, t } = useLanguage()

  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      {showLabel && (
        <span className={`text-xs font-semibold ${variant === 'light' ? 'text-white/80' : 'text-slate-500'}`}>
          {t('language')}
        </span>
      )}
      <select
        className={`${styles[variant] || styles.default} w-full`}
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        aria-label={t('selectLanguage')}
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>{l.label}</option>
        ))}
      </select>
    </label>
  )
}
