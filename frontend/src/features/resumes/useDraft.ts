import { useCallback, useEffect, useRef, useState } from 'react'
import { useBeforeUnload, useBlocker } from 'react-router'
import { ApiError, resumeApi, useResumeCache } from './api'
import type { Resume } from './api'
import type { ResumeDocument } from './document'

export interface WorkingDraft { title: string; content: ResumeDocument }
interface History { past: WorkingDraft[]; current: WorkingDraft; future: WorkingDraft[] }
const emptyHistory = (resume: Resume): History => ({
  past: [], current: { title: resume.title, content: resume.content }, future: [],
})

export function useDraft(initial: Resume) {
  const [history, setHistory] = useState(() => emptyHistory(initial))
  const [confirmed, setConfirmed] = useState(() => ({ draft: history.current, revision: initial.draft_revision }))
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<{ draft: WorkingDraft; error: Error }>()
  const [latest, setLatest] = useState<Resume>()
  const [checking, setChecking] = useState(false)
  const writing = useRef(false)
  const { update } = useResumeCache()
  const draft = history.current
  const dirty = draft !== confirmed.draft
  const conflict = failure?.error instanceof ApiError && failure.error.status === 409
  const blocked = conflict || failure?.draft === draft
  const blocker = useBlocker(dirty || saving)
  useBeforeUnload(useCallback((event) => {
    if (dirty || saving) { event.preventDefault(); event.returnValue = '' }
  }, [dirty, saving]))

  function edit(next: WorkingDraft) {
    setHistory((state) => ({ past: [...state.past.slice(-49), state.current], current: next, future: [] }))
  }

  function undo() {
    setHistory((state) => {
      const previous = state.past.at(-1)
      return previous ? { past: state.past.slice(0, -1), current: previous, future: [state.current, ...state.future] } : state
    })
  }

  function redo() {
    setHistory((state) => {
      const next = state.future[0]
      return next ? { past: [...state.past, state.current], current: next, future: state.future.slice(1) } : state
    })
  }

  async function loadLatest() {
    setChecking(true)
    try { setLatest(await resumeApi.get(initial.id)) }
    catch { setLatest(undefined) }
    finally { setChecking(false) }
  }

  async function save() {
    if (writing.current || !dirty || conflict || !draft.title.trim()) return
    writing.current = true
    setSaving(true)
    setFailure(undefined)
    try {
      const persisted = await resumeApi.update(initial.id, confirmed.revision, { ...draft, title: draft.title.trim() })
      setConfirmed({ draft, revision: persisted.draft_revision })
      update(persisted)
    } catch (error) {
      setFailure({ draft, error: error instanceof Error ? error : new Error('The resume could not be saved.') })
      if (error instanceof ApiError && error.status === 409) void loadLatest()
    } finally {
      writing.current = false
      setSaving(false)
    }
  }

  useEffect(() => {
    if (!dirty || saving || blocked || !draft.title.trim()) return
    const timer = window.setTimeout(() => void save(), 750)
    return () => window.clearTimeout(timer)
  })

  function reloadLatest() {
    if (!latest) return
    const state = emptyHistory(latest)
    setHistory(state)
    setConfirmed({ draft: state.current, revision: latest.draft_revision })
    update(latest)
    setLatest(undefined)
    setFailure(undefined)
  }

  return {
    draft, dirty, saving, failure: blocked ? failure?.error : undefined, conflict, latest, checking,
    edit, undo, redo, canUndo: Boolean(history.past.length), canRedo: Boolean(history.future.length),
    save, loadLatest, reloadLatest, revision: confirmed.revision, blocker,
  }
}
