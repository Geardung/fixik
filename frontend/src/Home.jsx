import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import BucketView from './BucketView.jsx'
import TopBar from './TopBar.jsx'
import './storage.css'

const ACCESS_LABEL = {
  public: 'Публичное',
  link: 'По ссылке',
  private: 'Закрытое',
}

export default function Home({ user, onLogout }) {
  const [buckets, setBuckets] = useState(null)
  const [error, setError] = useState(null)
  const [open, setOpen] = useState(null)

  const load = useCallback(async () => {
    try {
      setBuckets(await api('/api/buckets'))
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    onLogout()
  }

  async function createAndOpen() {
    try {
      const bucket = await api('/api/buckets', {
        method: 'POST',
        body: JSON.stringify({ name: 'Новое ведро' }),
      })
      setOpen({ uuid: bucket.uuid, renameOnMount: true })
    } catch (err) {
      setError(err.message)
    }
  }

  if (open) {
    return (
      <BucketView
        key={open.uuid}
        bucketUuid={open.uuid}
        renameOnMount={open.renameOnMount}
        onBack={() => {
          setOpen(null)
          load()
        }}
        user={user}
        onLogout={logout}
      />
    )
  }

  return (
    <div className="home-root">
      <div className="home-topbar">
        <TopBar user={user} onLogout={logout} />
      </div>

      <main className="storage-main">
        <header className="storage-header">
          <div>
            <h1 className="storage-title" aria-label="ae">
              <span className="brand-mark brand-mark--sm" role="img" aria-hidden="true" />
            </h1>
            <p className="storage-sub">{user.display_name || 'Вы вошли'}</p>
          </div>
        </header>

        {error && <p className="storage-error">{error}</p>}

        <div className="masonry">
          <div className="masonry-item masonry-item--bare">
            <button
              type="button"
              className="tile tile--plus"
              onClick={createAndOpen}
              aria-label="Создать ведро"
            >
              <span className="plus-icon" aria-hidden="true" />
            </button>
          </div>
          {(buckets || []).map((b) => (
            <div className="masonry-item" key={b.uuid}>
              <button
                type="button"
                className="tile tile--folder"
                onClick={() => setOpen({ uuid: b.uuid, renameOnMount: false })}
              >
                <div className="tile-body">
                  <p className="tile-name tile-name--lg" title={b.name}>
                    {b.name}
                  </p>
                  <p className="tile-meta">{ACCESS_LABEL[b.access] || b.access}</p>
                  <a
                    className="tile-link"
                    href={`/b/${b.share_hash}`}
                    onClick={(e) => e.stopPropagation()}
                    title="Открыть ссылку"
                  >
                    /b/{b.share_hash}
                  </a>
                </div>
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
