import { useCallback, useState } from 'react'

const ICON = {
  profile: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
    </svg>
  ),
  settings: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </svg>
  ),
  moon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a7 7 0 0 0 11.5 11.5z" />
    </svg>
  ),
  sun: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  ),
  logout: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  ),
}

function useThemeState() {
  const [theme, setTheme] = useState(
    () => document.documentElement.dataset.theme || 'dark',
  )
  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      document.documentElement.dataset.theme = next
      localStorage.setItem('theme', next)
      return next
    })
  }, [])
  return { theme, toggle }
}

export default function TopBar({ user, onLogout }) {
  const { theme, toggle } = useThemeState()
  const [panel, setPanel] = useState(null)

  return (
    <div className="topbar">
      <div className="topbar-icons" role="toolbar" aria-label="Аккаунт">
        <button
          type="button"
          className={`icon-btn${panel === 'profile' ? ' icon-btn--on' : ''}`}
          onClick={() => setPanel((p) => (p === 'profile' ? null : 'profile'))}
          aria-label="Профиль"
          title="Профиль"
        >
          {ICON.profile}
        </button>
        <button
          type="button"
          className={`icon-btn${panel === 'settings' ? ' icon-btn--on' : ''}`}
          onClick={() => setPanel((p) => (p === 'settings' ? null : 'settings'))}
          aria-label="Настройки"
          title="Настройки"
        >
          {ICON.settings}
        </button>
        <button
          type="button"
          className="icon-btn"
          onClick={toggle}
          aria-label={theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}
          title={theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}
        >
          {theme === 'light' ? ICON.moon : ICON.sun}
        </button>
        <button
          type="button"
          className="icon-btn icon-btn--danger"
          onClick={onLogout}
          aria-label="Выйти"
          title="Выйти"
        >
          {ICON.logout}
        </button>
      </div>

      {panel === 'profile' && (
        <div className="topbar-panel" role="dialog" aria-label="Профиль">
          <p className="topbar-panel-title">Профиль</p>
          <p className="topbar-panel-row">
            <span className="muted">Имя</span>
            <span>{user?.display_name || '—'}</span>
          </p>
          <p className="topbar-panel-row">
            <span className="muted">Секрет TOTP</span>
            <code className="topbar-secret">{user?.totp_secret || '—'}</code>
          </p>
        </div>
      )}

      {panel === 'settings' && (
        <div className="topbar-panel" role="dialog" aria-label="Настройки">
          <p className="topbar-panel-title">Настройки</p>
          <p className="topbar-panel-row">
            <span className="muted">Тема</span>
            <span>{theme === 'light' ? 'Светлая' : 'Тёмная'}</span>
          </p>
          <p className="topbar-panel-hint">
            Тема переключается иконкой полумесяца / солнца.
          </p>
        </div>
      )}
    </div>
  )
}
