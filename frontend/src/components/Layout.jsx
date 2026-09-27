import { NavLink, Outlet } from 'react-router-dom'
import { Activity, Bell, Building2, LayoutDashboard, LogOut, Menu, Shield, X } from 'lucide-react'
import { api } from '../api'
import { useEffect, useState } from 'react'
import Logo from './Logo'
import CimasLogo from './CimasLogo'
import LanguageSwitcher from './LanguageSwitcher'
import AiChatbot from './AiChatbot'
import { useLanguage } from '../i18n/LanguageContext'

const navForRole = (role, t) => {
  const base = [{ to: '/notifications', icon: Bell, label: t('smsLog') }]
  if (role === 'admin') {
    return [{ to: '/admin', icon: Shield, label: t('adminConsole') }, ...base]
  }
  if (role === 'nurse') {
    return [{ to: '/clinic', icon: LayoutDashboard, label: t('clinicDashboard') }, ...base]
  }
  return [{ to: '/hospital', icon: Building2, label: t('hospitalAlerts') }, ...base]
}

const ROLE_KEYS = { nurse: 'roleNurse', hospital: 'roleHospital', admin: 'roleAdmin' }

export default function Layout({ user, onLogout }) {
  const { t } = useLanguage()
  const [recentSms, setRecentSms] = useState(0)
  const [online, setOnline] = useState(true)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    function refresh() {
      api.notifications().then((n) => setRecentSms(n.length)).catch(() => {})
      api.health().then(() => setOnline(true)).catch(() => setOnline(false))
    }
    refresh()
    const interval = setInterval(refresh, 30000)
    return () => clearInterval(interval)
  }, [])

  const nav = navForRole(user.role, t)

  return (
    <div className="flex min-h-screen bg-slate-50">
      {mobileOpen && (
        <button className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)} aria-label={t('closeMenu')} />
      )}

      <aside className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="relative flex items-center justify-center border-b border-slate-100 px-6 py-6">
          <Logo size="sidebar" className="mx-auto" />
          <button className="absolute right-4 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-500 lg:hidden" onClick={() => setMobileOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 p-4">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition ${
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-50'
                }`
              }
            >
              <Icon size={18} />
              {label}
              {to === '/notifications' && recentSms > 0 && (
                <span className="ml-auto rounded-full bg-brand-500 px-2 py-0.5 text-[10px] font-bold text-white">{recentSms}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-100 p-4">
          <div className="mb-3 rounded-xl bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-800">{user.name}</p>
            <p className="text-xs text-slate-500">{user.facility_name || t('districtOversight')}</p>
            <p className="text-xs capitalize text-slate-400">{t(ROLE_KEYS[user.role] || 'roleNurse')}</p>
          </div>
          <button onClick={onLogout} className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
            <LogOut size={16} /> {t('signOut')}
          </button>
          <div className="mt-4 flex flex-col items-center gap-2 border-t border-slate-100 pt-4">
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">{t('poweredBy')}</p>
            <CimasLogo size="sm" showLabel={false} />
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col lg:ml-64">
        <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/80 px-4 py-4 backdrop-blur-md lg:px-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button className="rounded-lg border border-slate-200 p-2 text-slate-600 lg:hidden" onClick={() => setMobileOpen(true)}>
                <Menu size={18} />
              </button>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Activity size={16} className={online ? 'text-teal-500' : 'text-red-500'} />
                <span>{online ? t('systemOnline') : t('systemOffline')}</span>
                {user.facility_name && (
                  <>
                    <span className="hidden text-slate-300 sm:inline">·</span>
                    <span className="hidden sm:inline">{user.facility_name}</span>
                  </>
                )}
              </div>
            </div>
            <LanguageSwitcher variant="header" className="w-40" showLabel />
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-8">
          <Outlet />
        </main>
        <AiChatbot user={user} />
      </div>
    </div>
  )
}
