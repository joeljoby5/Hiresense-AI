import { useQuery } from '@tanstack/react-query'
import { request } from '../../services/api'

export interface JobInput {
  title: string
  company: string
  description: string
  listing_url: string | null
  location: string
  employment_type: string
  notes: string
}

export interface JobSummary {
  id: string
  title: string
  company: string
  archived: boolean
  revision: number
  created_at: string
  updated_at: string
}

export interface Job extends JobSummary { details: JobInput }
export type JobSort = 'updated_desc' | 'title_asc'
interface JobsPage { items: JobSummary[]; total: number; has_more: boolean }
const path = (id: string) => '/jobs/' + encodeURIComponent(id)

export const jobApi = {
  create: (details: JobInput) => request<Job>('/jobs', 'POST', details),
  get: (id: string, signal?: AbortSignal) => request<Job>(path(id), 'GET', undefined, signal),
  change: (id: string, expected_revision: number, changes: { details?: JobInput; archived?: boolean }) =>
    request<Job>(path(id), 'PATCH', { expected_revision, ...changes }),
  remove: (id: string, expectedRevision: number) => request<void>(path(id) + '?expected_revision=' + expectedRevision, 'DELETE'),
}

export function useJobs(archived: boolean, search: string, sort: JobSort, offset: number, limit: number) {
  const params = new URLSearchParams({ archived: String(archived), search, sort, offset: String(offset), limit: String(limit) })
  return useQuery({
    queryKey: ['jobs', 'list', archived, search, sort, offset, limit],
    queryFn: ({ signal }) => request<JobsPage>('/jobs?' + params, 'GET', undefined, signal),
  })
}

export function useJob(id: string) {
  return useQuery({ queryKey: ['jobs', 'detail', id], queryFn: ({ signal }) => jobApi.get(id, signal) })
}
