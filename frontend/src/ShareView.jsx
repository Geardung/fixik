import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import { formatSize, pluralFiles } from './BucketView.jsx'
import './storage.css'

const KIND_LABEL = { photo: 'Фото', video: 'Видео', text: 'Текст', other: 'Файл' }

function useShare(type, hash) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      setData(await api(`/api/share/${type}/${hash}`))
      setError(null)
    } catch (e) {
      setError(e.message)
      setData(null)
    }
  }, [type, hash])

  useEffect(() => {
    load()
  }, [load])

  return { data, error, reload: load }
}

function FileRow({ file, bucketName }) {
  const [url, setUrl] = useState(null)

  useEffect(() => {
    if (file.kind !== 'photo' && file.kind !== 'video') return undefined
    let alive = true
    api(`/api/share/f/${file.share_hash}`)
      .then((r) => {
        if (alive) setUrl(r.url)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [file.share_hash, file.kind])

  return (
    <article className="tile tile--file tile--static">
      {file.kind === 'photo' && url ? (
        <div className="tile-preview">
          <img src={url} alt={file.original_name} loading="lazy" />
        </div>
      ) : file.kind === 'video' && url ? (
        <div className="tile-preview">
          <video src={url} controls preload="metadata" />
        </div>
      ) : (
        <div className="tile-preview">
          <span className="tile-ext">
            {file.extension ? `.${file.extension}` : KIND_LABEL[file.kind] || 'Файл'}
          </span>
        </div>
      )}
      <div className="tile-body">
        <p className="tile-name" title={file.original_name}>
          {file.original_name}
        </p>
        <p className="tile-meta">
          {KIND_LABEL[file.kind] || 'Файл'} · {formatSize(file.size_bytes)}
        </p>
        <a className="tile-link" href={`/f/${file.share_hash}`}>
          Открыть файл →
        </a>
      </div>
    </article>
  )
}

export function FileSharePage({ hash }) {
  const { data, error } = useShare('f', hash)

  if (error) {
    return (
      <div className="share-root">
        <main className="share-main">
          <p className="storage-error">{error}</p>
          <a className="btn" href="/">
            На главную
          </a>
        </main>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="share-root">
        <main className="share-main">
          <p className="muted">…</p>
        </main>
      </div>
    )
  }

  const { file, bucket_name: bucketName, folder_name: folderName, url } = data

  return (
    <div className="share-root">
      <main className="share-main">
        <header className="storage-header">
          <div>
            <p className="storage-sub">
              {bucketName}
              {folderName ? ` / ${folderName}` : ''}
            </p>
            <h1 className="storage-title">{file.original_name}</h1>
            <p className="storage-sub">
              {KIND_LABEL[file.kind] || 'Файл'} · {formatSize(file.size_bytes)}
            </p>
          </div>
        </header>

        <div className="share-file-view">
          {file.kind === 'photo' && url && (
            <img className="share-file-img" src={url} alt={file.original_name} />
          )}
          {file.kind === 'video' && url && (
            <video className="share-file-video" src={url} controls autoPlay />
          )}
          {file.kind === 'text' && url && <TextBody url={url} />}
          {(!url || file.kind === 'other') && (
            <div className="share-file-fallback">
              <p className="tile-ext">
                {file.extension ? `.${file.extension}` : 'Файл'}
              </p>
              {url && (
                <a className="btn btn--primary" href={url} download={file.original_name}>
                  Скачать
                </a>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function TextBody({ url }) {
  const [text, setText] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    fetch(url)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((t) => {
        if (alive) setText(t)
      })
      .catch((e) => {
        if (alive) setErr(e.message)
      })
    return () => {
      alive = false
    }
  }, [url])

  if (err) return <p className="storage-error">{err}</p>
  if (text === null) return <p className="muted">…</p>
  return <pre className="share-text">{text}</pre>
}

export function FolderSharePage({ hash }) {
  const { data, error } = useShare('a', hash)

  if (error) {
    return (
      <div className="share-root">
        <main className="share-main">
          <p className="storage-error">{error}</p>
          <a className="btn" href="/">На главную</a>
        </main>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="share-root">
        <main className="share-main">
          <p className="muted">…</p>
        </main>
      </div>
    )
  }

  const { folder, bucket_name: bucketName, files } = data

  return (
    <div className="share-root">
      <main className="share-main">
        <header className="storage-header">
          <div>
            <p className="storage-sub">{bucketName}</p>
            <h1 className="storage-title">{folder.name || 'Корень'}</h1>
            <p className="storage-sub">{pluralFiles(folder.files_count || files.length)}</p>
          </div>
        </header>

        <div className="masonry">
          {files.map((f) => (
            <div className="masonry-item" key={f.uuid}>
              <FileRow file={f} bucketName={bucketName} />
            </div>
          ))}
        </div>
        {files.length === 0 && <p className="storage-empty">Пусто</p>}
      </main>
    </div>
  )
}

export function BucketSharePage({ hash }) {
  const [folder, setFolder] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const q = folder ? `?folder=${folder}` : ''
      setData(await api(`/api/share/b/${hash}${q}`))
      setError(null)
    } catch (e) {
      setError(e.message)
      setData(null)
    }
  }, [hash, folder])

  useEffect(() => {
    load()
  }, [load])

  if (error) {
    return (
      <div className="share-root">
        <main className="share-main">
          <p className="storage-error">{error}</p>
          <a className="btn" href="/">На главную</a>
        </main>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="share-root">
        <main className="share-main">
          <p className="muted">…</p>
        </main>
      </div>
    )
  }

  const { bucket, folders, files, current_folder: currentFolder } = data

  return (
    <div className="share-root">
      <main className="share-main">
        <nav className="crumbs" aria-label="Путь">
          <button type="button" className="crumb" onClick={() => setFolder(null)}>
            {bucket.name}
          </button>
          {currentFolder && (
            <>
              <span className="crumb-sep">/</span>
              <span className="crumb crumb--current">{currentFolder.name}</span>
            </>
          )}
        </nav>
        <h1 className="storage-title">
          {currentFolder ? currentFolder.name : bucket.name}
        </h1>

        <div className="masonry">
          {folders.map((f) => (
            <div className="masonry-item" key={f.uuid}>
              <button
                type="button"
                className="tile tile--folder tile--static"
                onClick={() => setFolder(f.uuid)}
              >
                <div className="tile-body">
                  <p className="tile-name tile-name--lg" title={f.name}>
                    {f.name}
                  </p>
                  <p className="tile-meta">{pluralFiles(f.files_count)}</p>
                </div>
              </button>
            </div>
          ))}
          {files.map((f) => (
            <div className="masonry-item" key={f.uuid}>
              <FileRow file={f} bucketName={bucket.name} />
            </div>
          ))}
        </div>
        {folders.length === 0 && files.length === 0 && (
          <p className="storage-empty">Пусто</p>
        )}
      </main>
    </div>
  )
}
