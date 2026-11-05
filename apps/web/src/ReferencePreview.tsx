import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ApiFailure, type WorkspaceApi } from './api'

/** Loads the small WebP preview of one reference image; retries once when previews are busy. */
export function useReferenceThumbnail(api: WorkspaceApi, id: string): { url: string | null; failed: boolean } {
  const [state, setState] = useState<{ id: string; url: string | null; failed: boolean }>({ id, url: null, failed: false })
  useEffect(() => {
    const controller = new AbortController()
    let created: string | null = null
    const load = (attempt: number): void => {
      api.referenceThumbnail(id, controller.signal).then(blob => {
        if (controller.signal.aborted) return
        created = URL.createObjectURL(blob)
        setState({ id, url: created, failed: false })
      }).catch(exception => {
        if (controller.signal.aborted) return
        if (exception instanceof ApiFailure && exception.retryable && attempt === 0) {
          window.setTimeout(() => { if (!controller.signal.aborted) load(1) }, 1500)
          return
        }
        setState({ id, url: null, failed: true })
      })
    }
    setState({ id, url: null, failed: false })
    load(0)
    return () => {
      controller.abort()
      if (created) URL.revokeObjectURL(created)
    }
  }, [api, id])
  return state.id === id ? state : { url: null, failed: false }
}

/** Thumbnail button; clicking opens the full-size reference image in a dialog. */
export function ReferenceThumb({ api, id, label, className }: {
  api: WorkspaceApi; id: string; label: string; className?: string
}) {
  const { url, failed } = useReferenceThumbnail(api, id)
  const [open, setOpen] = useState(false)
  return <>
    <button className={`reference-thumb${className ? ` ${className}` : ''}`} type="button" title="点击放大查看" aria-label={`放大查看${label}`}
      onClick={event => { event.preventDefault(); event.stopPropagation(); setOpen(true) }}>
      {url ? <img src={url} alt={label} /> : <span className="reference-placeholder">{failed ? '预览不可用' : '加载中'}</span>}
    </button>
    {open && <ReferencePreviewDialog api={api} id={id} label={label} onClose={() => setOpen(false)} />}
  </>
}

/** Full-size reference image, fetched only while the dialog is open. */
function ReferencePreviewDialog({ api, id, label, onClose }: {
  api: WorkspaceApi; id: string; label: string; onClose: () => void
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeRef = useRef(onClose)
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { closeRef.current = onClose }, [onClose])

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const dialog = dialogRef.current
    dialog?.showModal()
    return () => {
      dialog?.close()
      if (opener?.isConnected) opener.focus({ preventScroll: true })
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let created: string | null = null
    api.referenceImage(id, controller.signal).then(blob => {
      if (controller.signal.aborted) return
      created = URL.createObjectURL(blob)
      setUrl(created)
    }).catch(() => { if (!controller.signal.aborted) setError('参考图加载失败，可能已被删除。') })
    return () => {
      controller.abort()
      if (created) URL.revokeObjectURL(created)
    }
  }, [api, id])

  return createPortal(<dialog className="snapshot-dialog reference-preview-dialog" ref={dialogRef} aria-label={label}
    onCancel={event => { event.preventDefault(); closeRef.current() }}
    onKeyDown={event => { if (event.key === 'Escape') event.stopPropagation() }}
    onClick={event => { if (event.target === event.currentTarget) closeRef.current() }}>
    <div className="snapshot-dialog-content">
      <header className="snapshot-dialog-header"><h2>{label}</h2>
        <button className="icon-button" type="button" aria-label="关闭预览" onClick={onClose}><X size={18} aria-hidden="true" /></button></header>
      <div className="reference-preview-body">
        {url ? <img src={url} alt={label} /> : <p className={error ? 'alert' : 'subtle'} role="status">{error || '正在加载原图...'}</p>}
      </div>
    </div>
  </dialog>, document.body)
}
