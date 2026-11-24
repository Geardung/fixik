import { useCallback, useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import './auth.css'

async function api(path, options) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 204) return null
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return body
}

function AuthThemeToggle() {
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
  return (
    <button type="button" className="theme-toggle" onClick={toggle}>
      {theme === 'light' ? 'Тёмная' : 'Светлая'}
    </button>
  )
}

export default function AuthPage({ onAuthed }) {
  const [secret, setSecret] = useState('')
  const [otpauth, setOtpauth] = useState('')
  const [digits, setDigits] = useState(Array(6).fill(''))
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const canvasRef = useRef(null)
  const inputsRef = useRef([])

  const startAuth = useCallback(async () => {
    try {
      const data = await api('/api/auth/start', { method: 'POST' })
      setSecret(data.secret)
      setOtpauth(data.otpauth_url)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    setDigits(Array(6).fill(''))
    startAuth()
  }, [startAuth])

  useEffect(() => {
    if (!otpauth || !canvasRef.current) return
    const fg =
      getComputedStyle(document.documentElement).getPropertyValue('--qr-fg').trim() ||
      '#0f1419'
    QRCode.toCanvas(canvasRef.current, otpauth, {
      width: 220,
      margin: 1,
      color: { dark: fg, light: '#ffffff' },
    }).catch(() => {})
  }, [otpauth])

  function onDigit(i, value) {
    const v = value.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[i] = v
    setDigits(next)
    if (v && i < 5) inputsRef.current[i + 1]?.focus()
    if (next.every((d) => d !== '')) submit(next.join(''))
  }

  function onKeyDown(i, e) {
    if (e.key === 'Backspace' && !digits[i] && i > 0) {
      inputsRef.current[i - 1]?.focus()
    }
    if (e.key === 'ArrowLeft' && i > 0) inputsRef.current[i - 1]?.focus()
    if (e.key === 'ArrowRight' && i < 5) inputsRef.current[i + 1]?.focus()
  }

  function onPaste(e) {
    const text = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6)
    if (!text) return
    e.preventDefault()
    const next = Array(6).fill('')
    for (let i = 0; i < text.length; i++) next[i] = text[i]
    setDigits(next)
    inputsRef.current[Math.min(text.length, 5)]?.focus()
    if (text.length === 6) submit(text)
  }

  async function submit(code) {
    if (!secret) return
    setBusy(true)
    setError(null)
    try {
      await api('/api/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ secret, code }),
      })
      onAuthed()
    } catch (e) {
      setError(e.message)
      setDigits(Array(6).fill(''))
      inputsRef.current[0]?.focus()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-root">
      <AuthThemeToggle />

      <main className="auth-main">
        <header className="auth-header">
          <h1 className="auth-title" aria-label="ae">
            <span className="brand-mark" role="img" aria-hidden="true" />
          </h1>
          <p className="auth-sub">
            Отсканируйте код и введите шесть цифр из приложения-authenticator
          </p>
        </header>

        <section className="auth-split">
          <div className="auth-pane auth-pane--left">
            <div className="qr-frame">
              {otpauth ? (
                <canvas ref={canvasRef} aria-label="QR-код TOTP" />
              ) : (
                <div className="qr-placeholder">Генерация</div>
              )}
            </div>
            {secret && (
              <p className="secret-caption" title={secret}>
                {secret}
              </p>
            )}
          </div>

          <div className="auth-splitter" aria-hidden="true" />

          <div className="auth-pane auth-pane--right">
            <p className="digits-hint">Код из приложения</p>
            <div className="digits" onPaste={onPaste}>
              {digits.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => {
                    inputsRef.current[i] = el
                  }}
                  className="digit"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={1}
                  value={d}
                  disabled={busy || !secret}
                  onChange={(e) => onDigit(i, e.target.value)}
                  onKeyDown={(e) => onKeyDown(i, e)}
                  aria-label={`Цифра ${i + 1}`}
                />
              ))}
            </div>
            {error && <p className="auth-error">{error}</p>}
            <p className="auth-note">
              {busy ? 'Проверка' : 'Заполнение шести цифр отправляет форму'}
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}
