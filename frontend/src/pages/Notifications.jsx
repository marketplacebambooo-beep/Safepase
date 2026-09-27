import { useEffect, useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, MessageSquare, Phone, Smartphone } from 'lucide-react'
import { api } from '../api'
import { EmptyState, LoadingScreen } from '../components/UI'
import { useLanguage } from '../i18n/LanguageContext'

const STATUS_STYLES = {
  sent: 'bg-teal-50 text-teal-700',
  failed: 'bg-red-50 text-red-700',
  pending: 'bg-amber-50 text-amber-700',
}

const CHANNEL_STYLES = {
  sms: 'bg-sky-50 text-sky-700',
  whatsapp: 'bg-green-50 text-green-700',
  voice: 'bg-violet-50 text-violet-700',
  airtime: 'bg-amber-50 text-amber-700',
}

export default function Notifications() {
  const { t } = useLanguage()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [channels, setChannels] = useState(null)

  useEffect(() => {
    api.channelsStatus().then(setChannels).catch(() => {})
    api.notifications().then(setItems).finally(() => setLoading(false))
    const interval = setInterval(() => api.notifications().then(setItems), 15000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <LoadingScreen />

  const ready = channels?.sms_ready && channels?.whatsapp_ready && channels?.voice_ready && channels?.airtime_ready
  const hasIssues = (channels?.issues?.length ?? 0) > 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t('smsLog')}</h1>
        <p className="text-slate-500">{t('smsLogLiveDesc')}</p>
      </div>

      {channels && (
        <div className={`card-panel p-5 ${ready ? 'border-teal-200 bg-teal-50/30' : 'border-amber-200 bg-amber-50/30'}`}>
          <div className="flex items-start gap-3">
            {ready ? (
              <CheckCircle className="mt-0.5 shrink-0 text-teal-600" size={20} />
            ) : (
              <AlertTriangle className="mt-0.5 shrink-0 text-amber-600" size={20} />
            )}
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-semibold text-slate-900">
                  {ready ? t('channelLiveReady') : t('channelLivePending')}
                </p>
                <p className="mt-1 text-sm text-slate-600">{t('channelLiveHint')}</p>
              </div>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <div className="rounded-xl border border-white/80 bg-white/70 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('smsProvider')}</p>
                  <p className="mt-1 font-medium text-slate-800">{channels.sms_provider}</p>
                  <p className="text-xs text-slate-500">{t('senderId')}: {channels.sms_sender_id}</p>
                </div>
                <div className="rounded-xl border border-white/80 bg-white/70 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('whatsappProvider')}</p>
                  <p className="mt-1 font-medium text-slate-800">{channels.whatsapp_provider}</p>
                  <p className="text-xs text-slate-500">{t('senderId')}: {channels.whatsapp_sender_id}</p>
                </div>
                <div className="rounded-xl border border-white/80 bg-white/70 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('voiceProvider')}</p>
                  <p className="mt-1 font-medium text-slate-800">{channels.voice_provider}</p>
                  <p className="text-xs text-slate-500">{t('voicePhone')}: {channels.voice_phone || '—'}</p>
                </div>
                <div className="rounded-xl border border-white/80 bg-white/70 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('airtimeProvider')}</p>
                  <p className="mt-1 font-medium text-slate-800">{channels.airtime_provider}</p>
                  <p className="text-xs text-slate-500">{channels.airtime_currency} {channels.airtime_amount}</p>
                </div>
              </div>
              {channels.ussd_callback_url && (
                <div className="rounded-xl border border-white/80 bg-white/70 px-4 py-3 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('ussdCallbackUrl')}</p>
                  <p className="mt-1 break-all font-mono text-slate-800">{channels.ussd_callback_url}</p>
                  {channels.ussd_service_code && (
                    <p className="mt-2 text-xs text-slate-500">{t('ussdServiceCode')}: {channels.ussd_service_code}</p>
                  )}
                </div>
              )}
              {channels.voice_callback_url && (
                <div className="rounded-xl border border-white/80 bg-white/70 px-4 py-3 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('voiceCallbackUrl')}</p>
                  <p className="mt-1 break-all font-mono text-slate-800">{channels.voice_callback_url}</p>
                </div>
              )}
              {hasIssues && (
                <ul className="space-y-1 text-sm text-amber-800">
                  {channels.issues.map((issue) => (
                    <li key={issue} className="flex items-start gap-2">
                      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="card-panel">
        {items.length === 0 ? (
          <EmptyState icon={Bell} title={t('noMessages')} description={t('noMessagesDesc')} />
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((n) => (
              <div key={n.id} className="flex gap-4 p-5 transition hover:bg-slate-50">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                  {n.channel === 'voice' ? <Phone size={18} /> : n.channel === 'airtime' ? <Smartphone size={18} /> : <MessageSquare size={18} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-800">{n.recipient}</p>
                    <span className="shrink-0 text-xs text-slate-400">{new Date(n.sent_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{n.message}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${STATUS_STYLES[n.status] || STATUS_STYLES.sent}`}>
                      {n.status === 'pending' ? t('pending') : n.status === 'failed' ? t('statusFailed') : t('statusSent')}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${CHANNEL_STYLES[n.channel] || 'bg-slate-100 text-slate-500'}`}>{n.channel}</span>
                    {n.provider_ref && (
                      <span className="font-mono text-[10px] text-slate-400">{n.provider_ref}</span>
                    )}
                    {n.status === 'failed' && (
                      <button className="text-[10px] font-semibold uppercase text-brand-600 hover:text-brand-700" onClick={() => api.retryNotification(n.id).then(() => api.notifications().then(setItems))}>
                        {t('retry')}
                      </button>
                    )}
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
