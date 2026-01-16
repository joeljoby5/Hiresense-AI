import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { resumeApi, useExports } from './api'
import type { ExportFormat, Resume, Version } from './api'
import { formatDate } from './format'
import { Modal, RequestFailure } from './ResumeUi'

export function ResumeExports({ resume, version }: { resume: Resume; version?: Version }) {
  const { id, draft_revision } = resume
  const cache = useQueryClient()
  const query = useExports(id)
  const [open, setOpen] = useState(false)
  const [format, setFormat] = useState<ExportFormat>('pdf')
  const mutation = useMutation({
    mutationFn: () => resumeApi.export(id, format, version ? { version_id: version.id } : { expected_revision: draft_revision }),
    onSuccess: () => { void cache.invalidateQueries({ queryKey: ['exports'] }) },
  })
  const generated = mutation.data
  return <section className="surface recent" id="exports">
    <div className="pagination"><h2>Exports</h2><button className="button secondary" onClick={() => { mutation.reset(); setOpen(true) }}>Generate export</button></div>
    {query.isPending && <p role="status">Loading exports…</p>}
    {query.error && <RequestFailure error={query.error} retry={() => void query.refetch()} />}
    {query.data?.length ? <ul>{query.data.map((item) => <li key={item.id}>
      <div><a href={resumeApi.downloadUrl(id, item.id)} download>{item.format.toUpperCase()} · Draft {item.source_revision}</a>
        <p className="muted">{Math.ceil(item.size_bytes / 1024)} KB</p></div>
      <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
    </li>)}</ul> : query.data && <p>Generate a PDF, DOCX, TXT or JSON file from a saved draft.</p>}
    {query.data && <p className="muted">The workspace retains your 20 most recent exports across all resumes.</p>}
    {open && <Modal title="Generate export" onDismiss={() => { if (!mutation.isPending) setOpen(false) }}>
      <form className="stack" onSubmit={(event) => { event.preventDefault(); if (!mutation.isPending && !generated) mutation.mutate() }}>
        <p>{version ? 'Version ' + version.version_number : 'Saved draft ' + draft_revision}</p>
        {mutation.error && <RequestFailure error={mutation.error} />}
        {generated ? <a className="button primary" download href={resumeApi.downloadUrl(id, generated.id)}>Download {generated.format.toUpperCase()}</a> :
          <label>File format<select value={format} disabled={mutation.isPending} onChange={(event) => setFormat(event.target.value as ExportFormat)}>
            <option value="pdf">PDF</option><option value="docx">Word (.docx)</option><option value="txt">Plain text</option><option value="json">Structured JSON</option>
          </select></label>}
        <div className="dialog-actions"><button className="button secondary" type="button" onClick={() => setOpen(false)} disabled={mutation.isPending}>{generated ? 'Done' : 'Cancel'}</button>
          {!generated && <button className="button primary" disabled={mutation.isPending}>{mutation.isPending ? 'Generating…' : 'Generate'}</button>}</div>
      </form>
    </Modal>}
  </section>
}
