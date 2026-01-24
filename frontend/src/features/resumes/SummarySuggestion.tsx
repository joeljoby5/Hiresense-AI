import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { request } from '../../services/api'
import { Modal, RequestFailure } from './ResumeUi'

interface Status {
  provider: string
  available: boolean
  mock: boolean
}

interface Suggestion {
  original: string
  proposed: string
  explanation: string
  source_revision: number
  provider: string
  model: string | null
  mock: boolean
}

interface Props {
  resumeId: string
  revision: number
  summary: string
  canSuggest: boolean
  apply: (summary: string) => void
}

export function SummarySuggestion({ resumeId, revision, summary, canSuggest, apply }: Props) {
  const [consent, setConsent] = useState(false)
  const [open, setOpen] = useState(false)
  const status = useQuery({
    queryKey: ['writing-provider'],
    queryFn: ({ signal }) => request<Status>('/ai/status', 'GET', undefined, signal, 15_000),
  })
  const mutation = useMutation({
    mutationFn: () => request<Suggestion>('/ai/resumes/' + encodeURIComponent(resumeId) + '/summary', 'POST',
      { expected_revision: revision, consent }, undefined, 35_000),
  })
  const result = mutation.data
  const stale = result && (!canSuggest || result.source_revision !== revision || result.original !== summary.trim())
  const unchanged = result && result.proposed === result.original
  return <section className="surface stack" aria-label="Summary assistance">
    <h2>Summary assistance</h2>
    {status.isPending && <p role="status">Checking provider…</p>}
    {status.error && <RequestFailure error={status.error} retry={() => void status.refetch()} />}
    {status.data && <p>{status.data.mock ? 'Mock provider · deterministic formatting' :
      status.data.available ? 'Connected local provider' : 'Writing provider unavailable'}</p>}
    {status.data?.available && !status.data.mock && <label className="check-label">
      <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
      Send only my saved summary to the configured local provider
    </label>}
    <button className="button secondary" disabled={!summary.trim() || !canSuggest || !status.data?.available || (!status.data.mock && !consent)}
      onClick={() => { mutation.reset(); setOpen(true); mutation.mutate() }}>Review summary suggestion</button>
    {(!summary.trim() || !canSuggest) && <p className="muted">Save a summary to request a suggestion.</p>}
    {open && <Modal title="Summary suggestion" onDismiss={() => setOpen(false)}>
      <div className="stack">
        {mutation.isPending && <p role="status">Preparing suggestion…</p>}
        {mutation.error && <RequestFailure error={mutation.error} />}
        {result && <>
          <p>{result.mock ? 'Mock suggestion' : 'Local provider suggestion'} · {result.model ?? result.provider}</p>
          <div className="form-columns suggestion-comparison">
            <div><h2>Original</h2><p>{result.original}</p></div>
            <div><h2>Proposed</h2><p>{result.proposed}</p></div>
          </div>
          <p>{result.explanation}</p>
          {stale && <p>The draft changed. Request a suggestion for the current saved summary.</p>}
          {unchanged && <p>The provider proposed the same wording.</p>}
        </>}
        <div className="dialog-actions">
          <button className="button secondary" onClick={() => setOpen(false)}>{result ? 'Reject' : 'Close'}</button>
          {result && <button className="button primary" disabled={Boolean(stale || unchanged)} onClick={() => {
            apply(result.proposed)
            setOpen(false)
          }}>Apply to draft</button>}
        </div>
      </div>
    </Modal>}
  </section>
}
