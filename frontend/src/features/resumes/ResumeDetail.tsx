import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useLocation, useParams } from 'react-router'
import { resumeApi, useResume, useResumeCache, useVersions } from './api'
import { Modal, Pagination, RequestFailure } from './ResumeUi'
import { formatDate } from './format'

export function ResumeDetail() {
  const { resumeId = '' } = useParams()
  return <ResumeDetailContent key={resumeId} id={resumeId} />
}

function ResumeDetailContent({ id }: { id: string }) {
  const query = useResume(id)
  const cache = useResumeCache()
  const [offset, setOffset] = useState(0)
  const [dialog, setDialog] = useState(false)
  const [summary, setSummary] = useState('')
  const versions = useVersions(id, offset)
  const { hash } = useLocation()
  const checkpoint = useMutation({
    mutationFn: (revision: number) => resumeApi.checkpoint(id, revision, summary.trim() || null),
    onSuccess: () => { setDialog(false); setSummary(''); setOffset(0); cache.versions(id) },
    onError: () => { void query.refetch() },
  })
  const resume = query.data
  useEffect(() => {
    if (resume && hash === '#versions') document.getElementById(hash.slice(1))?.scrollIntoView()
  }, [hash, resume])
  if (query.isPending) return <p role="status">Loading resume…</p>
  if (query.error || !resume) return <RequestFailure error={query.error ?? new Error('Resume unavailable.')} retry={() => void query.refetch()} />
  return <>
    <Link to="/workspace/resumes">My resumes</Link>
    <header className="page-heading"><div><h1>{resume.title}</h1><p>Draft {resume.draft_revision} · Updated {formatDate(resume.updated_at)}</p></div>
      <div className="row"><button className="button secondary" onClick={() => { checkpoint.reset(); setDialog(true) }}>Save checkpoint</button></div>
    </header>
    <section className="surface recent" id="versions">
      <h2>Version history</h2>
      {versions.isPending && <p role="status">Loading checkpoints…</p>}
      {versions.error && <RequestFailure error={versions.error} retry={() => void versions.refetch()} />}
      {versions.data?.items.length ? <ul>{versions.data.items.map((version) => <li key={version.id}>
        <div><strong>Version {version.version_number}</strong><p>Draft {version.source_draft_revision}{version.change_summary ? ' · ' + version.change_summary : ''}</p></div>
        <time dateTime={version.created_at}>{formatDate(version.created_at)}</time>
      </li>)}</ul> : versions.data && <p>Save a checkpoint to keep a record of this draft.</p>}
      {versions.data && <Pagination offset={offset} limit={10} total={versions.data.total} more={versions.data.has_more} change={setOffset} />}
    </section>
    {dialog && <Modal title="Save checkpoint" onDismiss={() => { if (!checkpoint.isPending) setDialog(false) }}>
    <form className="stack" onSubmit={(event) => { event.preventDefault(); if (!checkpoint.isPending) checkpoint.mutate(resume.draft_revision) }}>
        <p>Keep a permanent snapshot of draft {resume.draft_revision}.</p>
        <label>Change summary (optional)<textarea maxLength={500} value={summary} onChange={(event) => setSummary(event.target.value)} /></label>
        {checkpoint.error && <RequestFailure error={checkpoint.error} />}
        <div className="dialog-actions"><button className="button secondary" type="button" disabled={checkpoint.isPending} onClick={() => setDialog(false)}>Cancel</button>
          <button className="button primary" disabled={checkpoint.isPending}>{checkpoint.isPending ? 'Saving…' : 'Save checkpoint'}</button></div>
      </form>
    </Modal>}
  </>
}
