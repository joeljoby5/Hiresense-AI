import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { request } from '../../services/api'
import { useJobs } from '../jobs/api'
import { useResumes, useVersions } from '../resumes/api'
import { formatDate } from '../resumes/format'
import { Pagination, RequestFailure } from '../resumes/ResumeUi'
import { label } from '../resumes/schema'

interface Summary {
  id: string
  resume_id: string
  resume_revision: number
  resume_version_id: string | null
  job_id: string
  job_revision: number
  created_at: string
}
interface Dimension {
  score: number | null
  coverage: number
  provisional: boolean
  components: Array<{ name: string; weight: number; score: number | null; finding: string; status: string }>
}
interface Report {
  algorithm_version: string
  configuration_version: string
  lexical_version: string
  readability: Dimension
  compatibility: Dimension
  skill_names: Record<string, string>
  notices: string[]
  skills: Array<{
    priority: string
    alternatives: string[]
    status: string
    evidence: Record<string, Array<{ section: string; entry_id: string | null }>>
    source_text: string
  }>
}
interface Detail extends Summary { report: Report }

function Breakdown({ title, dimension }: { title: string; dimension: Dimension }) {
  const { score, coverage, provisional, components } = dimension
  return <section className="surface stack">
    <h2>{title}</h2>
    <p><strong>{score === null ? 'Insufficient evidence to score' : score + ' / 100'}</strong> · {coverage}% evaluated{score !== null && provisional ? ' · Provisional' : ''}</p>
    {score !== null && <meter min={0} max={100} value={score} aria-label={title} />}
    <ul className="stack">{components.map((component) => <li key={component.name}>
      <strong>{component.name} · {component.weight}% weight</strong>
      <p>{component.score === null ? component.status.replaceAll('_', ' ') : Math.round(component.score) + ' / 100'}</p>
      <p>{component.finding}</p>
    </li>)}</ul>
  </section>
}

function Versions({ id, value, change }: { id: string; value: string; change: (id: string) => void }) {
  const [offset, setOffset] = useState(0)
  const versions = useVersions(id, offset)
  return <div className="stack">
    <label>Resume source<select value={value} onChange={(event) => change(event.target.value)}>
      <option value="">Current draft</option>
      {versions.data?.items.map((item) => <option key={item.id} value={item.id}>Version {item.version_number}</option>)}
    </select></label>
    {versions.error && <RequestFailure error={versions.error} retry={() => void versions.refetch()} />}
    {versions.data && <Pagination offset={offset} limit={10} total={versions.data.total} more={versions.data.has_more}
      change={(next) => { change(''); setOffset(next) }} />}
  </div>
}

export function AnalysisPage() {
  const [resumeSearch, setResumeSearch] = useState('')
  const [jobSearch, setJobSearch] = useState('')
  const [resumeId, setResumeId] = useState('')
  const [jobId, setJobId] = useState('')
  const [versionId, setVersionId] = useState('')
  const [selected, setSelected] = useState('')
  const resumes = useResumes(resumeSearch.trim(), 'updated_desc', 0, 100)
  const jobs = useJobs(false, jobSearch.trim(), 'updated_desc', 0, 100)
  const history = useQuery({ queryKey: ['analyses', 'history'], queryFn: ({ signal }) => request<Summary[]>('/analyses', 'GET', undefined, signal) })
  const result = useQuery({
    enabled: Boolean(selected),
    queryKey: ['analyses', 'detail', selected],
    queryFn: ({ signal }) => request<Detail>('/analyses/' + encodeURIComponent(selected), 'GET', undefined, signal),
  })
  const cache = useQueryClient()
  const resume = resumes.data?.items.find((item) => item.id === resumeId)
  const job = jobs.data?.items.find((item) => item.id === jobId)
  const analyze = useMutation({
    mutationFn: () => request<Detail>('/analyses', 'POST', {
      job_id: job!.id, job_revision: job!.revision, resume_id: resume!.id,
      ...(versionId ? { resume_version_id: versionId } : { resume_revision: resume!.draft_revision }),
    }),
    onSuccess: (analysis) => {
      cache.setQueryData(['analyses', 'detail', analysis.id], analysis)
      void cache.invalidateQueries({ queryKey: ['analyses', 'history'] })
      setSelected(analysis.id)
    },
    onError: () => { void resumes.refetch(); void jobs.refetch() },
  })
  const data = result.data
  return <div className="stack">
    <header className="page-heading"><div><h1>Resume analyzer</h1><p>Review resume readability and documented evidence against a saved job.</p></div></header>
    <form className="surface stack" onSubmit={(event) => { event.preventDefault(); if (resume && job && !analyze.isPending) analyze.mutate() }}>
      <div className="form-columns">
        <div className="stack">
          <label>Find resume<input maxLength={200} value={resumeSearch} onChange={(event) => { setResumeId(''); setVersionId(''); setResumeSearch(event.target.value) }} /></label>
          <label>Resume<select value={resumeId} required onChange={(event) => { setResumeId(event.target.value); setVersionId('') }}>
            <option value="">Select resume</option>{resumes.data?.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select></label>
          {resumeId && <Versions key={resumeId} id={resumeId} value={versionId} change={setVersionId} />}
        </div>
        <div className="stack">
          <label>Find active job<input maxLength={200} value={jobSearch} onChange={(event) => { setJobId(''); setJobSearch(event.target.value) }} /></label>
          <label>Target job<select value={jobId} required onChange={(event) => setJobId(event.target.value)}>
            <option value="">Select target job</option>{jobs.data?.items.map((item) => <option key={item.id} value={item.id}>{item.title} · {item.company}</option>)}
          </select></label>
        </div>
      </div>
      {resumes.error && <RequestFailure error={resumes.error} retry={() => void resumes.refetch()} />}
      {jobs.error && <RequestFailure error={jobs.error} retry={() => void jobs.refetch()} />}
      {analyze.error && <RequestFailure error={analyze.error} />}
      {resumes.data?.total === 0 && <p><Link to="/workspace/resumes">Open resume library</Link> to find or create a resume.</p>}
      {jobs.data?.total === 0 && <p><Link to="/workspace/jobs">Open job workspace</Link> to find or add a job.</p>}
      <div><button className="button primary" disabled={!resume || !job || analyze.isPending}>{analyze.isPending ? 'Analyzing…' : 'Run analysis'}</button></div>
    </form>
    <section className="surface stack">
      <h2>Saved analyses</h2>
      {history.isPending && <p role="status">Loading history…</p>}
      {history.error && <RequestFailure error={history.error} retry={() => void history.refetch()} />}
      {history.data?.length ? <label>Analysis<select value={selected} onChange={(event) => setSelected(event.target.value)}>
        <option value="">Choose from history</option>
        {history.data.map((item) => <option key={item.id} value={item.id}>
          {formatDate(item.created_at)} · Resume draft {item.resume_revision} · Job revision {item.job_revision}
        </option>)}
      </select></label> : history.data && <p>Run an analysis to save your first result.</p>}
    </section>
    {selected && result.isPending && <p role="status">Loading result…</p>}
    {result.error && <RequestFailure error={result.error} retry={() => void result.refetch()} />}
    {data && <div className="stack">
      {data.report.notices.map((notice) => <p key={notice}>{notice}</p>)}
      <div className="form-columns">
        <Breakdown title="Document readability" dimension={data.report.readability} />
        <Breakdown title="Job compatibility" dimension={data.report.compatibility} />
      </div>
      <section className="surface recent">
        <h2>Skill evidence</h2>
        {data.report.skills.length ? <ul>{data.report.skills.map((item, index) => <li key={index}>
          <div><strong>{item.alternatives.map((key) => data.report.skill_names[key] ?? key).join(' or ')}</strong>
            <p>{item.priority} · {item.status.replaceAll('_', ' ')}</p><p>{item.source_text}</p>
            {item.status === 'not_evidenced' && <p>Verify the requirement and add a concrete example only if you have relevant experience.</p>}
            {Object.entries(item.evidence).map(([key, entries]) => <p key={key}>
              {data.report.skill_names[key] ?? key} · {[...new Set(entries.map((entry) => entry.section))].map((section, position) =>
                <span key={section}>{position > 0 && ', '}<Link to={'/workspace/resumes/' + data.resume_id + '/edit?section=' + encodeURIComponent(section)}>{label(section)}</Link></span>)}
            </p>)}
          </div>
        </li>)}</ul> : <p>No non-optional skills from the current taxonomy could be evaluated.</p>}
      </section>
      <p className="muted">Resume revision {data.resume_revision} · Job revision {data.job_revision} · {data.report.algorithm_version} · {data.report.configuration_version}</p>
    </div>}
  </div>
}
