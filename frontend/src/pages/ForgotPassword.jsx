import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api } from '../api'
import Logo from '../components/Logo'
import { useLanguage } from '../i18n/LanguageContext'

export default function ForgotPassword() {
  const { t } = useLanguage()
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [step, setStep] = useState('request')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function requestReset(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.forgotPassword(email)
      setMessage(res.message)
      if (res.reset_token) {
        setToken(res.reset_token)
        setStep('reset')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function submitReset(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.resetPassword(token, newPassword)
      setMessage(t('passwordUpdated'))
      setStep('done')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Logo size="md" className="mx-auto mb-6 max-w-[160px]" />
        <h1 className="text-center text-xl font-bold text-slate-900">{t('resetPassword')}</h1>
        <p className="mt-1 text-center text-sm text-slate-500">{t('resetSubtitle')}</p>

        {step === 'request' && (
          <form onSubmit={requestReset} className="mt-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">{t('email')}</label>
              <input className="input-field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {message && <p className="text-sm text-teal-600">{message}</p>}
            <button className="btn-primary w-full" disabled={loading}>{loading ? t('sending') : t('sendResetLink')}</button>
          </form>
        )}

        {step === 'reset' && (
          <form onSubmit={submitReset} className="mt-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">{t('resetToken')}</label>
              <input className="input-field" value={token} onChange={(e) => setToken(e.target.value)} required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">{t('newPassword')}</label>
              <input className="input-field" type="password" minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button className="btn-primary w-full" disabled={loading}>{loading ? t('savingPassword') : t('updatePassword')}</button>
          </form>
        )}

        {step === 'done' && <p className="mt-6 text-center text-sm text-teal-600">{message}</p>}

        <Link to="/login" className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-brand-600 hover:text-brand-700">
          <ArrowLeft size={14} /> {t('backToSignIn')}
        </Link>
      </div>
    </div>
  )
}