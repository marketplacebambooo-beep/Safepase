import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, Eye, EyeOff, Link2, Lock, Shield, Smartphone,
} from 'lucide-react'
import { api, setToken, setUser } from '../api'
import Logo from '../components/Logo'
import CimasLogo from '../components/CimasLogo'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { useLanguage } from '../i18n/LanguageContext'

export default function Login({ onLogin }) {
  const { t } = useLanguage()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(false)
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const FEATURES = [
    { icon: Smartphone, label: t('featureUssd') },
    { icon: Activity, label: t('featureRisk') },
    { icon: Link2, label: t('featureReferral') },
  ]

  const STATS = [
    { value: '3', label: t('statLayers') },
    { value: '4', label: t('statTiers') },
    { value: '24/7', label: t('statAlerts') },
  ]

  useEffect(() => {
    const saved = localStorage.getItem('safepass_remember_email')
    if (saved) {
      setEmail(saved)
      setRemember(true)
    }
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!consent) {
      setError(t('consentRequired'))
      return
    }
    setError('')
    setLoading(true)
    try {
      const { access_token } = await api.login(email, password)
      setToken(access_token)
      const user = await api.me()
      setUser(user)
      if (remember) {
        localStorage.setItem('safepass_remember_email', email)
      } else {
        localStorage.removeItem('safepass_remember_email')
      }
      onLogin(user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen max-h-screen overflow-hidden">
      <div className="relative hidden h-full w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-900 via-brand-600 to-brand-500 px-10 py-10 xl:px-14 xl:py-12 lg:flex">
        <div className="pointer-events-none absolute -left-20 -top-20 h-64 w-64 rounded-full bg-sky-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 -right-16 h-56 w-56 rounded-full bg-teal-400/20 blur-3xl" />

        <div className="relative flex flex-col items-center pt-4 text-center">
          <Logo size="xl" className="w-full max-w-[300px]" />
          <p className="mt-4 text-sm font-semibold tracking-wide text-white">{t('healthathon')}</p>
          <p className="mt-1 text-xs text-white/75">{t('healthathonTagline')}</p>
          <div className="mt-5 w-full max-w-xs">
            <LanguageSwitcher variant="light" showLabel />
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-md space-y-6 text-center">
          <span className="inline-block rounded-full border border-white/20 bg-white/10 px-5 py-1.5 text-xs font-bold tracking-wide text-white backdrop-blur-sm">
            {t('safePassage')}
          </span>
          <div className="space-y-3">
            {FEATURES.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-4 rounded-xl border border-white/15 bg-white/10 px-5 py-3.5 text-left shadow-sm backdrop-blur-sm">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-sky-400 to-teal-400 text-white">
                  <Icon size={18} />
                </div>
                <span className="text-sm font-semibold text-white">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative space-y-5">
          <div className="mx-auto grid max-w-md grid-cols-3 gap-3">
            {STATS.map(({ value, label }) => (
              <div key={label} className="rounded-xl border border-white/15 bg-white/10 px-3 py-4 text-center backdrop-blur-sm">
                <p className="text-2xl font-bold text-white">{value}</p>
                <p className="mt-0.5 text-[10px] font-bold tracking-wider text-white/60">{label}</p>
              </div>
            ))}
          </div>
          <p className="text-center text-xs text-white/50">{t('rolesLayer')}</p>
        </div>
      </div>

      <div className="hidden w-1 shrink-0 bg-gradient-to-b from-brand-500 via-sky-500 to-teal-500 lg:block" />

      <div className="flex h-full w-full items-center justify-center bg-white lg:w-1/2">
        <div className="w-full max-w-md px-6 py-4 sm:px-10">
          <div className="mb-4 flex items-center justify-between lg:hidden">
            <Logo size="md" className="max-w-[160px]" />
            <LanguageSwitcher variant="header" className="w-36" />
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900">{t('signIn')}</h2>
            <p className="mt-1 text-sm text-slate-500">{t('signInSubtitle')}</p>

            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">{t('email')}</label>
                <input className="input-field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">{t('password')}</label>
                <div className="relative">
                  <input className="input-field pr-11" type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
                  <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between text-sm">
                <label className="flex cursor-pointer items-center gap-2 text-slate-600">
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-500" />
                  {t('rememberMe')}
                </label>
                <Link to="/forgot-password" className="font-medium text-brand-600 hover:text-brand-700">{t('forgotPassword')}</Link>
              </div>
              <label className="flex cursor-pointer gap-3 rounded-xl border border-brand-100 bg-brand-50/60 p-3 text-xs leading-relaxed text-slate-600">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-brand-500" />
                <span>{t('consent')}</span>
              </label>
              {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
              <button type="submit" className="btn-primary w-full !rounded-xl !py-3 !text-base" disabled={loading || !consent}>
                {loading ? t('signingIn') : t('signInButton')}
              </button>
            </form>
          </div>

          <div className="mt-6 space-y-3 border-t border-slate-100 pt-4">
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-[10px] font-bold tracking-wide text-slate-400">
              {[
                { icon: Lock, label: t('tls') },
                { icon: Shield, label: t('jwt') },
                { icon: Smartphone, label: t('ussdSms') },
                { icon: Activity, label: t('live') },
              ].map(({ icon: Icon, label }) => (
                <span key={label} className="flex items-center gap-1"><Icon size={11} /> {label}</span>
              ))}
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">{t('poweredBy')}</p>
              <CimasLogo size="lg" showLabel={false} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
