import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { AlertCircle, X } from 'lucide-react'
import { Link } from 'react-router'
import { ApiError } from './api'

export function RequestFailure({ error, retry }: { error: Error; retry?: () => void }) {
  return <div className="notice" role="alert">
    <AlertCircle size={20} aria-hidden="true" />
    <div><strong>{error.message}</strong>
      {error instanceof ApiError && error.fields.length > 0 && <ul className="error-fields">
        {error.fields.map((field) => <li key={field}>{field.replaceAll('_', ' ')}</li>)}
      </ul>}
      <div className="row">
        {error instanceof ApiError && error.code === 'DEVELOPMENT_IDENTITY_UNAVAILABLE' && <Link to="/workspace/help">Workspace setup</Link>}
        {retry && <button type="button" className="button secondary" onClick={retry}>Try again</button>}
      </div>
    </div>
  </div>
}

export function Modal({ title, onDismiss, children }: { title: string; onDismiss: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])
  return <dialog ref={dialog} aria-label={title} onCancel={(event) => { event.preventDefault(); onDismiss() }}>
    <div className="dialog-heading"><h2>{title}</h2><button type="button" className="icon-button" aria-label="Close dialog" onClick={onDismiss}><X size={20} /></button></div>
    {children}
  </dialog>
}

export function Pagination({ offset, limit, total, more, change }: {
  offset: number; limit: number; total: number; more: boolean; change: (offset: number) => void
}) {
  if (offset === 0 && !more) return null
  return <div className="pagination">
    <span>{total ? Math.min(offset + 1, total) : 0}–{Math.min(offset + limit, total)} of {total}</span>
    <div className="row">
      <button className="button secondary" disabled={offset === 0} onClick={() => change(Math.max(0, offset - limit))}>Previous</button>
      <button className="button secondary" disabled={!more} onClick={() => change(offset + limit)}>Next</button>
    </div>
  </div>
}
