import { useCallback, useEffect, useState } from 'react'
import AuthPage from './AuthPage.jsx'
import Home from './Home.jsx'
import { BucketSharePage, FileSharePage, FolderSharePage } from './ShareView.jsx'
import './index.css'

function parseSharePath(pathname) {
  const m = pathname.match(/^\/([fab])\/([A-Za-z0-9]{4,32})\/?$/)
  if (!m) return null
  const kind = { f: 'file', a: 'folder', b: 'bucket' }[m[1]]
  return { kind, hash: m[2] }
}

export default function App() {
  const [user, setUser] = useState(undefined)
  const share = parseSharePath(window.location.pathname)

  const refresh = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me', { credentials: 'include' })
      if (!res.ok) {
        setUser(null)
        return
      }
      setUser(await res.json())
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  if (share) {
    if (share.kind === 'file') return <FileSharePage hash={share.hash} />
    if (share.kind === 'folder') return <FolderSharePage hash={share.hash} />
    return <BucketSharePage hash={share.hash} />
  }

  if (user === undefined) {
    return (
      <div className="boot">
        <p className="muted">…</p>
      </div>
    )
  }

  if (!user) {
    return <AuthPage onAuthed={refresh} />
  }

  return <Home user={user} onLogout={refresh} />
}
