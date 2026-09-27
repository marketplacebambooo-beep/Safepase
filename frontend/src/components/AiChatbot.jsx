import { useEffect, useRef, useState } from 'react'
import FormattedText from './FormattedText'
import {
  Brain,
  MessageCircle,
  Mic,
  MicOff,
  Paperclip,
  Plus,
  Send,
  Trash2,
  X,
} from 'lucide-react'
import { api } from '../api'
import { useLanguage } from '../i18n/LanguageContext'

const WELCOME_KEYS = {
  nurse: 'aiChatWelcomeNurse',
  hospital: 'aiChatWelcomeHospital',
  admin: 'aiChatWelcomeAdmin',
}

function welcomeMessage(user, t) {
  const key = WELCOME_KEYS[user.role] || 'aiChatWelcomeNurse'
  return {
    id: 'welcome',
    role: 'assistant',
    content: t(key),
    ai_powered: false,
    message_type: 'text',
    created_at: new Date().toISOString(),
  }
}

export default function AiChatbot({ user }) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)
  const fileRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])

  async function loadSessions(selectId = null) {
    const list = await api.aiChatSessions()
    setSessions(list)
    const target = selectId ?? activeSessionId ?? list[0]?.id ?? null
    if (target) {
      setActiveSessionId(target)
      await loadMessages(target)
    } else {
      setActiveSessionId(null)
      setMessages([welcomeMessage(user, t)])
    }
    return list
  }

  async function loadMessages(sessionId) {
    const history = await api.aiChatHistory(sessionId)
    if (history.length) {
      setMessages(history)
    } else {
      setMessages([welcomeMessage(user, t)])
    }
  }

  useEffect(() => {
    if (open) {
      loadSessions().catch(() => {
        setMessages([welcomeMessage(user, t)])
      })
    }
  }, [open, user.role])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function startNewChat() {
    setError('')
    const session = await api.createAiChatSession()
    setSessions((prev) => [session, ...prev])
    setActiveSessionId(session.id)
    setMessages([welcomeMessage(user, t)])
    setInput('')
  }

  async function selectSession(sessionId) {
    if (sessionId === activeSessionId) return
    setActiveSessionId(sessionId)
    setError('')
    await loadMessages(sessionId)
  }

  async function deleteSession(sessionId, event) {
    event.stopPropagation()
    await api.deleteAiChatSession(sessionId)
    const list = await loadSessions()
    if (!list.length) {
      const session = await api.createAiChatSession()
      setSessions([session])
      setActiveSessionId(session.id)
      setMessages([welcomeMessage(user, t)])
    }
  }

  async function sendMessage(text, messageType = 'text', attachmentName = null) {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setInput('')
    setError('')
    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: trimmed,
      ai_powered: false,
      message_type: messageType,
      attachment_name: attachmentName,
      created_at: new Date().toISOString(),
    }
    setMessages((m) => [...m, userMsg])
    setLoading(true)
    try {
      const res = await api.aiChat(trimmed, activeSessionId)
      if (!activeSessionId) setActiveSessionId(res.session_id)
      setMessages((m) => [...m, {
        id: res.message_id,
        role: 'assistant',
        content: res.reply,
        ai_powered: res.ai_powered,
        message_type: 'text',
        created_at: new Date().toISOString(),
      }])
      await loadSessions(res.session_id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function send(e) {
    e.preventDefault()
    await sendMessage(input)
  }

  async function handleFileSelect(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setError('')
    setLoading(true)
    try {
      const res = await api.attachAiChatFile(file)
      setInput(res.suggested_message)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function toggleRecording() {
    if (recording) {
      recorderRef.current?.stop()
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(t('aiChatMicUnsupported'))
      return
    }
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        if (!blob.size) return
        setLoading(true)
        try {
          const file = new File([blob], `voice-${Date.now()}.webm`, { type: 'audio/webm' })
          const res = await api.transcribeAiChat(file)
          const text = `[Voice note]: ${res.text}`
          setInput(text)
        } catch (err) {
          setError(err.message)
        } finally {
          setLoading(false)
        }
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      setError(t('aiChatMicDenied'))
    }
  }

  async function clearHistory() {
    if (activeSessionId) {
      await api.deleteAiChatSession(activeSessionId)
    }
    await startNewChat()
  }

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-teal-500 text-white shadow-lg transition hover:scale-105 hover:shadow-xl"
          aria-label={t('aiAssistant')}
        >
          <MessageCircle size={24} />
        </button>
      )}

      {open && (
        <div className="fixed bottom-6 right-6 z-50 flex h-[min(560px,85vh)] w-[min(720px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <aside className="flex w-36 shrink-0 flex-col border-r border-slate-100 bg-slate-50">
            <button
              type="button"
              onClick={startNewChat}
              className="m-2 flex items-center gap-1.5 rounded-xl bg-brand-500 px-2.5 py-2 text-xs font-semibold text-white hover:bg-brand-600"
            >
              <Plus size={14} />
              {t('aiChatNew')}
            </button>
            <div className="flex-1 space-y-1 overflow-y-auto px-2 pb-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => selectSession(session.id)}
                  onKeyDown={(e) => e.key === 'Enter' && selectSession(session.id)}
                  className={`group w-full cursor-pointer rounded-lg px-2 py-2 text-left text-xs transition ${
                    activeSessionId === session.id
                      ? 'bg-white shadow-sm ring-1 ring-brand-200'
                      : 'hover:bg-white/80'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <p className="line-clamp-2 font-medium text-slate-800">{session.title}</p>
                    <button
                      type="button"
                      onClick={(e) => deleteSession(session.id, e)}
                      className="shrink-0 rounded p-0.5 text-slate-400 opacity-0 hover:text-red-500 group-hover:opacity-100"
                      title={t('aiChatDelete')}
                    >
                      <X size={12} />
                    </button>
                  </div>
                  {session.preview && (
                    <p className="mt-1 line-clamp-2 text-[10px] text-slate-500">{session.preview}</p>
                  )}
                </div>
              ))}
            </div>
          </aside>

          <div className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-brand-500 to-teal-500 px-4 py-3 text-white">
              <div className="flex items-center gap-2">
                <Brain size={20} />
                <div>
                  <p className="text-sm font-bold">{t('aiAssistant')}</p>
                  <p className="text-[10px] text-white/80">{t('aiAssistantSubtitle')}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button type="button" onClick={clearHistory} className="rounded-lg p-1.5 hover:bg-white/20" title={t('aiChatClear')}>
                  <Trash2 size={16} />
                </button>
                <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-1.5 hover:bg-white/20">
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                      m.role === 'user'
                        ? 'bg-brand-500 text-white'
                        : 'bg-slate-100 text-slate-800'
                    }`}
                  >
                    {m.attachment_name && (
                      <p className="mb-1 flex items-center gap-1 text-[10px] opacity-80">
                        <Paperclip size={12} />
                        {m.attachment_name}
                      </p>
                    )}
                    {m.message_type === 'audio' && m.role === 'user' && (
                      <p className="mb-1 text-[10px] opacity-80">{t('aiChatVoiceNote')}</p>
                    )}
                    {m.role === 'assistant' ? (
                      <FormattedText text={m.content} className="!space-y-2 [&_p]:!text-sm [&_h2]:!text-sm [&_h3]:!text-sm" />
                    ) : (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    )}
                    {m.role === 'assistant' && (
                      <p className="mt-1 text-[10px] opacity-60">
                        {m.ai_powered ? t('aiPowered') : t('ruleBased')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-slate-100 px-3 py-2 text-sm text-slate-500">{t('aiChatThinking')}</div>
                </div>
              )}
              {error && <p className="text-xs text-red-600">{error}</p>}
              <div ref={bottomRef} />
            </div>

            <form onSubmit={send} className="border-t border-slate-100 p-3">
              <div className="flex gap-2">
                <input ref={fileRef} type="file" className="hidden" accept=".txt,.md,.csv,.json,.jpg,.jpeg,.png,.webp" onChange={handleFileSelect} />
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  disabled={loading}
                  className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 disabled:opacity-50"
                  title={t('aiChatAttach')}
                >
                  <Paperclip size={16} />
                </button>
                <button
                  type="button"
                  onClick={toggleRecording}
                  disabled={loading}
                  className={`rounded-xl border p-2 disabled:opacity-50 ${
                    recording
                      ? 'border-red-300 bg-red-50 text-red-600'
                      : 'border-slate-200 text-slate-500 hover:bg-slate-50'
                  }`}
                  title={recording ? t('aiChatStopRecording') : t('aiChatRecord')}
                >
                  {recording ? <MicOff size={16} /> : <Mic size={16} />}
                </button>
                <input
                  className="input-field flex-1 !py-2 text-sm"
                  placeholder={t('aiChatPlaceholder')}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                />
                <button type="submit" className="btn-primary !px-3 !py-2" disabled={loading || !input.trim()}>
                  <Send size={16} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
