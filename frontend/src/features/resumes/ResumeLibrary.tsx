import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Copy, FileText, Grid2X2, List, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { resumeApi, useResumeCache, useResumes } from './api'
import type { ResumeSummary, Sort } from './api'
import { Modal, Pagination, RequestFailure } from './ResumeUi'
import { formatDate } from './format'

type Action = { kind: 'create' } | { kind: 'rename' | 'duplicate' | 'delete'; resume: ResumeSummary }
const labels = { create: 'Create resume', rename: 'Rename resume', duplicate: 'Duplicate resume', delete: 'Delete resume' }
const limit = 9

function ResumeAction({ action, close, removed }: { action: Action; close: () => void; removed: () => void }) {
  const navigate = useNavigate()
  const cache = useResumeCache()
  const [title, setTitle] = useState(action.kind === 'rename' ? action.resume.title : '')
  const mutation = useMutation({
    mutationFn: async () => {
      switch (action.kind) {
        case 'create': return resumeApi.create(title.trim())
        case 'rename': return resumeApi.update(action.resume.id, action.resume.draft_revision, { title: title.trim() })
        case 'duplicate': return resumeApi.duplicate(action.resume.id)
        case 'delete': await resumeApi.remove(action.resume.id, action.resume.draft_revision); return undefined
      }
    },
    onSuccess: (result) => {
      cache.update(result, action.kind === 'delete' ? action.resume.id : undefined)
      if (action.kind === 'delete') removed()
      close()
      if (result && (action.kind === 'create' || action.kind === 'duplicate')) void navigate('/workspace/resumes/' + result.id)
    },
    onError: () => cache.update(),
  })
  const titled = action.kind === 'create' || action.kind === 'rename'
  return <Modal title={labels[action.kind]} onDismiss={() => { if (!mutation.isPending) close() }}>
    <form className="stack" onSubmit={(event) => { event.preventDefault(); if (!mutation.isPending && (!titled || title.trim())) mutation.mutate() }}>
      {titled && <label>Resume title<input autoFocus required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} /></label>}
      {action.kind === 'duplicate' && <p>Make an independent copy of <strong>{action.resume.title}</strong>.</p>}
      {action.kind === 'delete' && <p>Permanently delete <strong>{action.resume.title}</strong> and its checkpoints?</p>}
      {mutation.error && <RequestFailure error={mutation.error} />}
      <div className="dialog-actions">
        <button className="button secondary" type="button" autoFocus={!titled} disabled={mutation.isPending} onClick={close}>Cancel</button>
        <button className={'button ' + (action.kind === 'delete' ? 'danger' : 'primary')} disabled={mutation.isPending || (titled && !title.trim())}>
          {mutation.isPending ? 'Working…' : labels[action.kind]}
        </button>
      </div>
    </form>
  </Modal>
}

export function Overview() {
  const query = useResumes('', 'updated_desc', 0, 4)
  return <>
    <header className="page-heading"><div><h1>Overview</h1><p>Pick up where you left off.</p></div><Link className="button primary" to="/workspace/resumes">Open resume library</Link></header>
    {query.isPending && <p role="status">Loading workspace…</p>}
    {query.error && <RequestFailure error={query.error} retry={() => void query.refetch()} />}
    {query.data && <div className="overview-grid">
      <section className="surface stat"><FileText /><h2>Total resumes</h2><strong>{query.data.total}</strong></section>
      <section className="surface recent"><h2>Recent resumes</h2>
        {query.data.items.length ? <ul>{query.data.items.map((item) => <li key={item.id}>
          <Link to={'/workspace/resumes/' + item.id}>{item.title}</Link><time dateTime={item.updated_at}>{formatDate(item.updated_at)}</time>
        </li>)}</ul> : <p>Your recent resumes will appear here. Start a new draft in the library.</p>}
      </section>
    </div>}
  </>
}

export function ResumeLibrary() {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<Sort>('updated_desc')
  const [offset, setOffset] = useState(0)
  const [list, setList] = useState(false)
  const [action, setAction] = useState<Action | null>(null)
  const query = useResumes(search.trim(), sort, offset, limit)
  const items = query.data?.items ?? []
  return <>
    <header className="page-heading"><div><h1>My resumes</h1><p>Find drafts, manage copies, and review saved checkpoints.</p></div>
      <button className="button primary" onClick={() => setAction({ kind: 'create' })}><Plus size={18} /> New resume</button>
    </header>
    <div className="library-toolbar">
      <label className="search"><Search size={18} aria-hidden="true" /><input aria-label="Search resume titles" placeholder="Search resume titles" maxLength={200} value={search}
        onChange={(event) => { setSearch(event.target.value); setOffset(0) }} /></label>
      <label className="sort"><span>Sort by</span><select aria-label="Sort resumes" value={sort} onChange={(event) => { setSort(event.target.value as Sort); setOffset(0) }}>
        <option value="updated_desc">Recently updated</option><option value="updated_asc">Oldest updated</option>
        <option value="title_asc">Title A–Z</option><option value="title_desc">Title Z–A</option>
      </select></label>
      <div className="toggle" role="group" aria-label="Resume view">
        <button className="icon-button" aria-label="Grid view" aria-pressed={!list} onClick={() => setList(false)}><Grid2X2 size={18} /></button>
        <button className="icon-button" aria-label="List view" aria-pressed={list} onClick={() => setList(true)}><List size={19} /></button>
      </div>
    </div>
    {query.isPending && <p className="surface empty" role="status">Loading resumes…</p>}
    {query.error && <RequestFailure error={query.error} retry={() => void query.refetch()} />}
    {query.data && !items.length && <div className="surface empty">
      <FileText size={32} />
      <h2>{search.trim() || offset ? 'No resumes on this page' : 'Create your first resume'}</h2>
      <p>{search.trim() ? 'Try another title or clear the search.' : 'Start with a blank draft and give it a name.'}</p>
      {!search.trim() && !offset && <button className="button primary" onClick={() => setAction({ kind: 'create' })}>New resume</button>}
    </div>}
    <div className={list ? 'resume-grid resume-list' : 'resume-grid'}>
      {items.map((resume) => <article key={resume.id} className="surface resume-card">
        <div className="resume-card-heading"><span className="file-icon"><FileText size={22} /></span>
          <div><Link className="resume-title" to={'/workspace/resumes/' + resume.id}>{resume.title}</Link><div className="muted">{resume.parent_resume_id ? 'Independent copy' : 'Resume'} · Draft {resume.draft_revision}</div></div>
        </div>
        <time className="muted" dateTime={resume.updated_at}>Updated {formatDate(resume.updated_at)}</time>
        <div className="card-actions">
          <div className="row">
            <Link to={'/workspace/resumes/' + resume.id + '#versions'}>History</Link>
            <Link to={'/workspace/resumes/' + resume.id + '#exports'}>Export</Link>
          </div>
          <div className="row">
            <button className="icon-button" aria-label={'Rename ' + resume.title} title="Rename" onClick={() => setAction({ kind: 'rename', resume })}><Pencil size={17} /></button>
            <button className="icon-button" aria-label={'Duplicate ' + resume.title} title="Duplicate" onClick={() => setAction({ kind: 'duplicate', resume })}><Copy size={17} /></button>
            <button className="icon-button" aria-label={'Delete ' + resume.title} title="Delete" onClick={() => setAction({ kind: 'delete', resume })}><Trash2 size={17} /></button>
          </div>
        </div>
      </article>)}
    </div>
    {query.data && <Pagination offset={offset} limit={limit} total={query.data.total} more={query.data.has_more} change={setOffset} />}
    {action && <ResumeAction action={action} close={() => setAction(null)} removed={() => {
      if (items.length <= 1 && offset) setOffset(offset - limit)
    }} />}
  </>
}
