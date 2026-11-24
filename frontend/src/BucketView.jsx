import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import TopBar from './TopBar.jsx'

const KIND_LABEL = { photo: 'Фото', video: 'Видео', text: 'Текст', other: 'Файл' }
const ACCESS_LABEL = {
  public: 'Публичное',
  link: 'По ссылке',
  private: 'Закрытое',
}

export function formatSize(n) {
  if (n < 1024) return `${n} Б`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} КБ`
  return `${(n / 1024 / 1024).toFixed(1)} МБ`
}

export function pluralFiles(n) {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return `${n} файл`
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return `${n} файла`
  return `${n} файлов`
}

function PreviewBody({ file }) {
  const [url, setUrl] = useState(null)
  const [text, setText] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    setUrl(null)
    setText(null)
    setErr(null)
    api(`/api/files/${file.uuid}/url`)
      .then((r) => {
        if (!alive) return
        setUrl(r.url)
        if (file.kind === 'text') {
          return fetch(r.url)
            .then((res) => (res.ok ? res.text() : Promise.reject(new Error(`HTTP ${res.status}`))))
            .then((t) => {
              if (alive) setText(t)
            })
            .catch((e) => {
              if (alive) setErr(e.message)
            })
        }
        return null
      })
      .catch((e) => {
        if (alive) setErr(e.message)
      })
    return () => {
      alive = false
    }
  }, [file.uuid, file.kind])

  if (err) return <p className="storage-error">{err}</p>
  if (!url) return <p className="muted preview-loading">…</p>

  if (file.kind === 'photo') {
    return <img className="preview-img" src={url} alt={file.original_name} />
  }
  if (file.kind === 'video') {
    return <video className="preview-video" src={url} controls autoPlay />
  }
  if (file.kind === 'text') {
    if (text === null) return <p className="muted preview-loading">…</p>
    return <pre className="preview-text">{text}</pre>
  }
  return (
    <div className="preview-other">
      <span className="tile-ext">
        {file.extension ? `.${file.extension}` : 'Файл'}
      </span>
      <a className="btn btn--primary" href={url} download={file.original_name}>
        Скачать
      </a>
    </div>
  )
}

function PreviewPanel({ file, onClose }) {
  return (
    <aside className="preview-panel" aria-label="Предпросмотр">
      <header className="preview-head">
        <div className="preview-head-text">
          <p className="preview-name" title={file.original_name}>
            {file.original_name}
          </p>
          <p className="tile-meta">
            {KIND_LABEL[file.kind] || 'Файл'} · {formatSize(file.size_bytes)}
          </p>
        </div>
        <div className="preview-actions">
          <a className="tile-action" href={`/f/${file.share_hash}`}>
            Полный просмотр
          </a>
          <button type="button" className="tile-action" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </header>
      <div className="preview-body">
        <PreviewBody file={file} />
      </div>
    </aside>
  )
}

function FileTile({ file, onAction, onPreview, active }) {
  const [thumb, setThumb] = useState(null)

  useEffect(() => {
    if (file.kind !== 'photo') return undefined
    let alive = true
    api(`/api/files/${file.uuid}/url`)
      .then((r) => {
        if (alive) setThumb(r.url)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [file.uuid])

  const badge = file.extension
    ? `.${file.extension}`
    : KIND_LABEL[file.kind] || 'Файл'

  return (
    <div className="masonry-item">
      <article
        className={`tile tile--file tile--static${active ? ' tile--active' : ''}`}
      >
        <button
          type="button"
          className="tile-hit"
          onClick={() => onPreview(file)}
          aria-label={`Предпросмотр: ${file.original_name}`}
        >
          {file.kind === 'photo' && thumb ? (
            <div className="tile-preview">
              <img src={thumb} alt={file.original_name} loading="lazy" />
            </div>
          ) : (
            <div className="tile-preview">
              <span className="tile-ext">{badge}</span>
            </div>
          )}
          <div className="tile-body">
            <p className="tile-name" title={file.original_name}>
              {file.original_name}
            </p>
            <p className="tile-meta">
              {KIND_LABEL[file.kind] || 'Файл'} · {formatSize(file.size_bytes)}
            </p>
          </div>
        </button>
        <div className="tile-actions">
          <button
            type="button"
            className="tile-action"
            onClick={() => onPreview(file)}
          >
            Просмотр
          </button>
          <a
            className="tile-action"
            href={`/f/${file.share_hash}`}
            onClick={(e) => e.stopPropagation()}
          >
            Ссылка
          </a>
          <button
            type="button"
            className="tile-action"
            onClick={() => onAction('move', file)}
          >
            Переместить
          </button>
          <button
            type="button"
            className="tile-action tile-action--danger"
            onClick={() => onAction('delete', file)}
          >
            Удалить
          </button>
        </div>
      </article>
    </div>
  )
}

function FolderTile({ folder, onOpen, onDelete }) {
  return (
    <div className="masonry-item">
      <article className="tile tile--folder tile--static">
        <button
          type="button"
          className="tile"
          onClick={() => onOpen(folder)}
          style={{ padding: 0 }}
        >
          <div className="tile-body">
            <p className="tile-name tile-name--lg" title={folder.name}>
              {folder.name}
            </p>
            <p className="tile-meta">{pluralFiles(folder.files_count)}</p>
          </div>
        </button>
        <div className="tile-actions">
          <a
            className="tile-action"
            href={`/a/${folder.share_hash}`}
            onClick={(e) => e.stopPropagation()}
          >
            Ссылка
          </a>
          <button
            type="button"
            className="tile-action tile-action--danger"
            onClick={() => onDelete(folder)}
          >
            Удалить
          </button>
        </div>
      </article>
    </div>
  )
}

export default function BucketView({
  bucketUuid,
  renameOnMount = false,
  onBack,
  user,
  onLogout,
}) {
  const [data, setData] = useState(null)
  const [folder, setFolder] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [newFolder, setNewFolder] = useState('')
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [moving, setMoving] = useState(null)
  const [renaming, setRenaming] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [preview, setPreview] = useState(null)
  const titleInputRef = useRef(null)
  const renameStartedRef = useRef(false)

  const load = useCallback(async () => {
    try {
      const query = folder ? `?folder=${folder}` : ''
      setData(await api(`/api/buckets/${bucketUuid}/contents${query}`))
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [bucketUuid, folder])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (data && renameOnMount && !renameStartedRef.current) {
      renameStartedRef.current = true
      setNameDraft(data.bucket.name)
      setRenaming(true)
    }
  }, [data, renameOnMount])

  useEffect(() => {
    if (renaming && titleInputRef.current) {
      titleInputRef.current.focus()
      titleInputRef.current.select()
    }
  }, [renaming])

  useEffect(() => {
    setPreview(null)
  }, [folder])

  async function saveName() {
    const trimmed = nameDraft.trim()
    setRenaming(false)
    if (!data || !trimmed || trimmed === data.bucket.name) return
    try {
      const updated = await api(`/api/buckets/${bucketUuid}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: trimmed }),
      })
      setData((d) => (d ? { ...d, bucket: updated } : d))
    } catch (err) {
      setError(err.message)
    }
  }

  async function createFolder(e) {
    e.preventDefault()
    const name = newFolder.trim()
    if (!name) return
    try {
      await api(`/api/buckets/${bucketUuid}/folders`, {
        method: 'POST',
        body: JSON.stringify({ name }),
      })
      setNewFolder('')
      setShowNewFolder(false)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteFolder(target) {
    if (!window.confirm(`Удалить папку «${target.name}» со всем содержимым?`)) {
      return
    }
    try {
      await api(`/api/folders/${target.uuid}`, { method: 'DELETE' })
      if (folder === target.uuid) setFolder(null)
      else await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function onUpload(e) {
    const picked = Array.from(e.target.files || [])
    e.target.value = ''
    if (!picked.length) return
    setBusy(true)
    setError(null)
    try {
      await Promise.all(
        picked.map(async (f) => {
          const contentType = f.type || 'application/octet-stream'
          const created = await api(`/api/buckets/${bucketUuid}/files`, {
            method: 'POST',
            body: JSON.stringify({
              folder_uuid: folder,
              original_name: f.name,
              size_bytes: f.size,
              content_type: contentType,
            }),
          })
          const res = await fetch(`/api/files/${created.uuid}/upload`, {
            method: 'PUT',
            headers: { 'Content-Type': contentType },
            body: f,
            credentials: 'include',
          })
          if (!res.ok) {
            const body = await res.json().catch(() => ({}))
            throw new Error(body.detail || `HTTP ${res.status}`)
          }
        }),
      )
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function onFileAction(action, file) {
    if (action === 'delete') {
      if (!window.confirm(`Удалить «${file.original_name}»?`)) return
      try {
        await api(`/api/files/${file.uuid}`, { method: 'DELETE' })
        if (preview?.uuid === file.uuid) setPreview(null)
        await load()
      } catch (err) {
        setError(err.message)
      }
      return
    }
    if (action === 'move') setMoving(file)
  }

  async function doMove(targetFolderUuid) {
    if (!moving) return
    try {
      await api(`/api/files/${moving.uuid}`, {
        method: 'PATCH',
        body: JSON.stringify({ folder_uuid: targetFolderUuid }),
      })
      setMoving(null)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  if (!data) {
    return (
      <div className="home-root">
        <div className="home-topbar">
          <TopBar user={user} onLogout={onLogout} />
        </div>
        <main className="storage-main">
          {error ? (
            <p className="storage-error">{error}</p>
          ) : (
            <p className="muted">…</p>
          )}
          <button type="button" className="btn" onClick={onBack}>
            Вёдра
          </button>
        </main>
      </div>
    )
  }

  const { bucket, folders, files, current_folder: currentFolder } = data
  const isEmpty = folders.length === 0 && files.length === 0
  const previewOpen = Boolean(preview)

  return (
    <div className="home-root">
      <div className="home-topbar">
        <TopBar user={user} onLogout={onLogout} />
      </div>

      <main className="storage-main">
        <div className="storage-top">
          <button type="button" className="btn" onClick={onBack}>
            Вёдра
          </button>
          <div className="storage-actions">
            <button
              type="button"
              className="btn"
              onClick={() => setShowNewFolder((s) => !s)}
            >
              Новая папка
            </button>
            <label className={`btn btn--primary${busy ? ' btn--disabled' : ''}`}>
              {busy ? 'Загрузка…' : 'Загрузить'}
              <input
                type="file"
                multiple
                hidden
                disabled={busy}
                onChange={onUpload}
              />
            </label>
          </div>
        </div>

        <nav className="crumbs" aria-label="Путь">
          <button
            type="button"
            className="crumb"
            onClick={() => setFolder(null)}
          >
            {bucket.name}
          </button>
          {currentFolder && (
            <>
              <span className="crumb-sep">/</span>
              <span className="crumb crumb--current">{currentFolder.name}</span>
            </>
          )}
        </nav>

        {renaming ? (
          <input
            ref={titleInputRef}
            className="underline-input underline-input--title"
            value={nameDraft}
            onChange={(e) => setNameDraft(e.target.value)}
            onBlur={saveName}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.target.blur()
              if (e.key === 'Escape') {
                setNameDraft(data.bucket.name)
                e.target.blur()
              }
            }}
            maxLength={255}
            aria-label="Название Вёдра"
          />
        ) : (
          <h1 className="storage-title">
            {currentFolder ? currentFolder.name : bucket.name}
          </h1>
        )}
        <p className="storage-sub">
          {ACCESS_LABEL[bucket.access] || bucket.access}
          {' · '}
          <a className="tile-link" href={`/b/${bucket.share_hash}`}>
            /b/{bucket.share_hash}
          </a>
        </p>

        {showNewFolder && (
          <form className="storage-toolbar" onSubmit={createFolder}>
            <input
              className="underline-input underline-input--sm"
              placeholder="Имя папки"
              value={newFolder}
              onChange={(e) => setNewFolder(e.target.value)}
              maxLength={255}
              autoFocus
            />
            <button
              type="submit"
              className="btn btn--primary"
              disabled={!newFolder.trim()}
            >
              Создать
            </button>
          </form>
        )}

        {error && <p className="storage-error">{error}</p>}

        <div className={`split${previewOpen ? ' split--preview' : ''}`}>
          <div className="split-list">
            <div className={`masonry${previewOpen ? ' masonry--single' : ''}`}>
              {folders.map((f) => (
                <FolderTile
                  key={f.uuid}
                  folder={f}
                  onOpen={(target) => setFolder(target.uuid)}
                  onDelete={deleteFolder}
                />
              ))}
              {files.map((f) => (
                <FileTile
                  key={f.uuid}
                  file={f}
                  onAction={onFileAction}
                  onPreview={setPreview}
                  active={preview?.uuid === f.uuid}
                />
              ))}
            </div>

            {isEmpty && (
              <p className="storage-empty">
                {currentFolder
                  ? 'В папке пусто — загрузите файлы'
                  : 'Пусто — создайте папку или загрузите файлы'}
              </p>
            )}
          </div>

          {previewOpen && (
            <PreviewPanel file={preview} onClose={() => setPreview(null)} />
          )}
        </div>
      </main>

      {moving && (
        <div
          className="modal-backdrop"
          onClick={() => setMoving(null)}
          role="presentation"
        >
          <div
            className="modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <p className="modal-title">Переместить «{moving.original_name}»</p>
            {folders.length === 0 ? (
              <p className="modal-empty">В ведре пока нет других папок</p>
            ) : (
              <div className="modal-list">
                {folders
                  .filter((f) => f.uuid !== moving.folder_uuid)
                  .map((f) => (
                    <button
                      key={f.uuid}
                      type="button"
                      className="modal-option"
                      onClick={() => doMove(f.uuid)}
                    >
                      {f.name}
                    </button>
                  ))}
              </div>
            )}
            <button
              type="button"
              className="btn"
              onClick={() => setMoving(null)}
            >
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
