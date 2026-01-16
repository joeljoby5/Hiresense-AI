import { base, request } from '../../services/api'
export { ApiError } from '../../services/api'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { ResumeDocument } from './document'

export interface ResumeSummary {
  id: string
  title: string
  draft_revision: number
  parent_resume_id: string | null
  created_at: string
  updated_at: string
}

export interface Resume extends ResumeSummary { content: ResumeDocument }

export interface Version {
  id: string
  version_number: number
  source_draft_revision: number
  change_summary: string | null
  created_at: string
}

export type ExportFormat = 'pdf' | 'docx' | 'txt' | 'json'

export interface ResumeExport {
  id: string
  source_revision: number
  source_version_id: string | null
  format: ExportFormat
  created_at: string
  size_bytes: number
}

interface Page<T> { items: T[]; total: number; has_more: boolean }
export type Sort = 'updated_desc' | 'updated_asc' | 'title_asc' | 'title_desc'

const path = (id: string) => '/resumes/' + encodeURIComponent(id)

export const resumeApi = {
  get: (id: string, signal?: AbortSignal) => request<Resume>(path(id), 'GET', undefined, signal),
  create: (title: string) => request<Resume>('/resumes', 'POST', { title }),
  update: (id: string, expected_revision: number, changes: { title?: string; content?: ResumeDocument }) =>
    request<Resume>(path(id), 'PATCH', { expected_revision, ...changes }),
  duplicate: (id: string) => request<Resume>(path(id) + '/duplicate', 'POST', {}),
  remove: (id: string, revision: number) => request<void>(path(id) + '?expected_revision=' + revision, 'DELETE'),
  checkpoint: (id: string, expected_revision: number, change_summary: string | null) =>
    request<Version>(path(id) + '/versions', 'POST', { expected_revision, change_summary }),
  export: (id: string, format: ExportFormat, source: { expected_revision: number } | { version_id: string }) =>
    request<ResumeExport>(path(id) + '/exports', 'POST', { format, ...source }),
  downloadUrl: (id: string, exportId: string) => base + path(id) + '/exports/' + encodeURIComponent(exportId),
}

export function useResumes(search = '', sort: Sort = 'updated_desc', offset = 0, limit = 9) {
  const params = new URLSearchParams({ search, sort, offset: String(offset), limit: String(limit) })
  return useQuery({
    queryKey: ['resumes', 'list', search, sort, offset, limit],
    queryFn: ({ signal }) => request<Page<ResumeSummary>>('/resumes?' + params, 'GET', undefined, signal),
  })
}

export function useResume(id: string) {
  return useQuery({ queryKey: ['resumes', 'detail', id], queryFn: ({ signal }) => resumeApi.get(id, signal) })
}

export function useVersions(id: string, offset: number) {
  return useQuery({
    queryKey: ['versions', id, offset],
    queryFn: ({ signal }) => request<Page<Version>>(path(id) + '/versions?limit=10&offset=' + offset, 'GET', undefined, signal),
  })
}

export function useExports(id: string) {
  return useQuery({
    queryKey: ['exports', id],
    queryFn: ({ signal }) => request<ResumeExport[]>(path(id) + '/exports', 'GET', undefined, signal),
  })
}

export function useResumeCache() {
  const cache = useQueryClient()
  return {
    update(resume?: Resume, removedId?: string) {
      if (resume) cache.setQueryData(['resumes', 'detail', resume.id], resume)
      if (removedId) {
        cache.removeQueries({ queryKey: ['resumes', 'detail', removedId] })
        cache.removeQueries({ queryKey: ['versions', removedId] })
        cache.removeQueries({ queryKey: ['exports', removedId] })
      }
      void cache.invalidateQueries({ queryKey: ['resumes', 'list'] })
    },
    versions(id: string) { void cache.invalidateQueries({ queryKey: ['versions', id] }) },
  }
}
