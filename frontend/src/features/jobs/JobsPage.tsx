import { useCallback, useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { BriefcaseBusiness, Plus, Search } from 'lucide-react'
import { Link, useBeforeUnload, useBlocker, useNavigate, useParams } from 'react-router'
import { Modal, Pagination, RequestFailure } from '../resumes/ResumeUi'
import { formatDate } from '../resumes/format'
import { jobApi, useJob, useJobs } from './api'
import type { Job, JobInput, JobSort } from './api'
import { JobRequirements } from './JobRequirements'

const pageSize = 12
const empty: JobInput = { title: '', company: '', description: '', listing_url: null, location: '', employment_type: '', notes: '' }

export function JobsPage() {
  const [archived, setArchived] = useState(false)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<JobSort>('updated_desc')
  const [offset, setOffset] = useState(0)
  const result = useJobs(archived, search.trim(), sort, offset, pageSize)
  return <>
    <header className="page-heading"><div><h1>Job workspace</h1><p>Save job descriptions and keep notes for each role.</p></div>
      <Link className="button primary" to="new"><Plus size={18} /> Add job</Link>
    </header>
    <div className="library-toolbar">
      <label className="search"><Search size={18} aria-hidden="true" /><input aria-label="Search job titles or companies" placeholder="Search by title or company" maxLength={200} value={search}
        onChange={(event) => { setSearch(event.target.value); setOffset(0) }} /></label>
      <label className="sort">Sort by<select value={sort} onChange={(event) => { setSort(event.target.value as JobSort); setOffset(0) }}>
        <option value="updated_desc">Recently updated</option><option value="title_asc">Title A–Z</option>
      </select></label>
      <div className="toggle" role="group" aria-label="Job status">
        <button className="button secondary" aria-pressed={!archived} onClick={() => { setArchived(false); setOffset(0) }}>Active</button>
        <button className="button secondary" aria-pressed={archived} onClick={() => { setArchived(true); setOffset(0) }}>Archived</button>
      </div>
    </div>
    {result.isPending && <p className="surface empty" role="status">Loading jobs…</p>}
    {result.error && <RequestFailure error={result.error} retry={() => void result.refetch()} />}
    {result.data && <>
      <section className="surface recent" aria-label="Saved jobs">
        {result.data.items.length ? <ul>{result.data.items.map((job) => <li key={job.id}>
          <div><Link to={job.id}>{job.title}</Link><p>{job.company}</p></div>
          <time dateTime={job.updated_at}>{formatDate(job.updated_at)}</time>
        </li>)}</ul> : <div className="empty"><BriefcaseBusiness size={30} /><h2>No {archived ? 'archived' : 'active'} jobs found</h2>
          <p>{search.trim() ? 'Try a different title or company.' : 'Saved listings appear here.'}</p></div>}
      </section>
      <Pagination offset={offset} limit={pageSize} total={result.data.total} more={result.data.has_more} change={setOffset} />
    </>}
  </>
}

export function NewJob() { return <JobEditor /> }

export function EditJob() {
  const { jobId = '' } = useParams()
  const result = useJob(jobId)
  if (result.isPending) return <p role="status">Loading job…</p>
  if (!result.data) return <RequestFailure error={result.error ?? new Error('Job unavailable.')} retry={() => void result.refetch()} />
  return <JobEditor key={jobId} initial={result.data} />
}

function JobEditor({ initial }: { initial?: Job }) {
  const [saved, setSaved] = useState(initial)
  const [form, setForm] = useState(initial?.details ?? empty)
  const [confirm, setConfirm] = useState(false)
  const [message, setMessage] = useState('')
  const cache = useQueryClient()
  const navigate = useNavigate()
  const dirty = form !== (saved?.details ?? empty)
  const allowNavigation = useBlocker(dirty)
  useEffect(() => {
    if (!initial && saved) void navigate('/workspace/jobs/' + saved.id, { replace: true })
  }, [initial, saved, navigate])
  useBeforeUnload(useCallback((event) => { if (dirty) { event.preventDefault(); event.returnValue = '' } }, [dirty]))
  const save = useMutation({
    mutationFn: (archive?: boolean) => saved
      ? jobApi.change(saved.id, saved.revision, archive === undefined ? { details: form } : { archived: archive })
      : jobApi.create(form),
    onSuccess: (job) => {
      cache.setQueryData(['jobs', 'detail', job.id], job)
      void cache.invalidateQueries({ queryKey: ['jobs', 'list'] })
      void cache.invalidateQueries({ queryKey: ['jobs', 'requirements', job.id] })
      setSaved(job)
      setForm(job.details)
      setMessage(job.archived ? 'Saved to archived jobs.' : 'Listing saved.')
    },
  })
  const remove = useMutation({
    mutationFn: () => jobApi.remove(saved!.id, saved!.revision),
    onSuccess: () => {
      cache.removeQueries({ queryKey: ['jobs', 'detail', saved!.id] })
      void cache.invalidateQueries({ queryKey: ['jobs', 'list'] })
      void navigate('/workspace/jobs', { replace: true })
    },
  })
  const change = (name: keyof JobInput, value: string) => setForm({ ...form, [name]: name === 'listing_url' && !value ? null : value })
  const canSave = Boolean(form.title.trim() && form.company.trim() && form.description.trim())
  return <>
    <Link to="/workspace/jobs">Job workspace</Link>
    <header className="page-heading"><div><h1>{saved ? saved.title : 'Add job'}</h1>
      {saved && <p>{saved.company} · {saved.archived ? 'Archived' : 'Active'} · Revision {saved.revision}</p>}</div>
      {saved && <div className="row">
        <button className="button secondary" disabled={dirty || save.isPending} onClick={() => save.mutate(!saved.archived)}>{saved.archived ? 'Restore job' : 'Archive job'}</button>
        <button className="button danger" disabled={dirty || save.isPending} onClick={() => { remove.reset(); setConfirm(true) }}>Delete job</button>
      </div>}
    </header>
    <form className="surface stack job-form" onSubmit={(event) => { event.preventDefault(); if (dirty && canSave && !save.isPending) save.mutate(undefined) }}>
      <fieldset className="stack" disabled={save.isPending}>
      <div className="form-columns">
        <label>Job title<input required maxLength={200} value={form.title} onChange={(event) => change('title', event.target.value)} /></label>
        <label>Company<input required maxLength={200} value={form.company} onChange={(event) => change('company', event.target.value)} /></label>
        <label>Location<input maxLength={200} value={form.location} onChange={(event) => change('location', event.target.value)} /></label>
        <label>Employment type<input maxLength={100} value={form.employment_type} onChange={(event) => change('employment_type', event.target.value)} /></label>
      </div>
      <label>Listing URL<input type="url" maxLength={2083} value={form.listing_url ?? ''} onChange={(event) => change('listing_url', event.target.value)} /></label>
      <label>Job description<textarea className="job-description" required maxLength={40_000} value={form.description} onChange={(event) => change('description', event.target.value)} /></label>
      <label>Notes<textarea maxLength={5_000} value={form.notes} onChange={(event) => change('notes', event.target.value)} /></label>
      </fieldset>
      {save.error && <RequestFailure error={save.error} />}
      <div className="row"><button className="button primary" disabled={!dirty || !canSave || save.isPending}>{save.isPending ? 'Saving…' : 'Save job'}</button>
        {message && <p role="status">{message}</p>}</div>
    </form>
    {saved && <JobRequirements id={saved.id} />}
    {confirm && saved && <Modal title="Delete job" onDismiss={() => { if (!remove.isPending) setConfirm(false) }}>
      <div className="stack"><p>Permanently delete this listing and its notes?</p>
        {remove.error && <RequestFailure error={remove.error} />}
        <div className="dialog-actions">
          <button className="button secondary" disabled={remove.isPending} onClick={() => setConfirm(false)}>Cancel</button>
          <button className="button danger" disabled={remove.isPending} onClick={() => remove.mutate()}>Delete job</button>
        </div>
      </div>
    </Modal>}
    {allowNavigation.state === 'blocked' && <Modal title="Leave job listing?" onDismiss={allowNavigation.reset}>
      <p>You have unsaved changes.</p>
      <div className="dialog-actions"><button className="button secondary" onClick={allowNavigation.reset}>Keep editing</button>
        <button className="button danger" onClick={allowNavigation.proceed}>Leave listing</button></div>
    </Modal>}
  </>
}
