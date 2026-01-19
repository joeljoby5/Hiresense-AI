import { RequestFailure } from '../resumes/ResumeUi'
import { useJobRequirements } from './api'

export function JobRequirements({ id }: { id: string }) {
  const result = useJobRequirements(id)
  const data = result.data
  return <section className="surface recent job-form">
    <h2>Extracted requirements</h2>
    {result.isPending && <p role="status">Reading saved listing…</p>}
    {result.error && <RequestFailure error={result.error} retry={() => void result.refetch()} />}
    {data && <>
      <p>Review these rule-based findings against the saved description.</p>
      {(data.seniority || data.role_category) && <p>{[data.seniority, data.role_category].filter(Boolean).join(' · ')}</p>}
      {data.requirements.length ? <ul className="requirement-list">{data.requirements.map((item, index) => <li key={index}>
        <div><strong>{item.alternatives.length ? item.alternatives.map((skill) => data.skill_names[skill] ?? skill).join(' or ') : item.kind}</strong>
          <p>{item.evidence}</p></div><span className="muted">{item.priority}</span>
      </li>)}</ul> : <p>No known requirements were extracted.</p>}
    </>}
  </section>
}
