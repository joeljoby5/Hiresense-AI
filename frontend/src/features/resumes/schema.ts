import rawSchema from './resume-schema.json'
import type { DocumentObject, DocumentValue, ResumeDocument } from './document'

export interface FieldSchema {
  type?: string
  format?: string
  '$ref'?: string
  anyOf?: FieldSchema[]
  properties?: Record<string, FieldSchema>
  required?: string[]
  items?: FieldSchema
  enum?: string[]
  default?: DocumentValue
  minLength?: number
  maxLength?: number
  minimum?: number
  maximum?: number
}

const root = rawSchema as FieldSchema & { '$defs': Record<string, FieldSchema> }
export const fields = root.properties!
export const names: Record<string, string> = {
  personal_information: 'Personal information',
  professional_summary: 'Professional summary',
  career_objective: 'Career objective',
  experience: 'Experience',
  education: 'Education',
  skills: 'Skills',
  projects: 'Projects',
  certifications: 'Certifications',
  achievements: 'Achievements',
  publications: 'Publications',
  research: 'Research',
  volunteer_experience: 'Volunteering',
  leadership_experience: 'Leadership',
  languages: 'Languages',
  relevant_coursework: 'Coursework',
  custom_sections: 'Custom sections',
}
export const label = (key: string) => names[key] ?? key.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())

export function resolve(schema: FieldSchema): FieldSchema {
  if (schema.$ref) return root.$defs[schema.$ref.split('/').at(-1)!]!
  const nonNull = schema.anyOf?.find((option) => option.type !== 'null')
  return nonNull ? resolve(nonNull) : schema
}

export function newValue(schema: FieldSchema, initialize = false): DocumentValue {
  if (!initialize && schema.default !== undefined) return schema.default
  if (!initialize && schema.anyOf?.some((option) => option.type === 'null')) return null
  const field = resolve(schema)
  switch (field.type) {
    case 'object': return Object.fromEntries(Object.entries(field.properties ?? {}).map(([key, item]) =>
      [key, key === 'id' ? crypto.randomUUID() : newValue(item)]))
    case 'array': return []
    case 'boolean': return false
    case 'number':
    case 'integer': return field.default ?? null
    default: return field.enum?.[0] ?? ''
  }
}

export const object = (value: DocumentValue | undefined): DocumentObject =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {}
export const array = (value: DocumentValue | undefined): DocumentValue[] => Array.isArray(value) ? value : []
export const string = (value: DocumentValue | undefined) => typeof value === 'string' ? value : ''
export const identifier = (value: DocumentValue) => string(object(value).id)
export const sections = (document: ResumeDocument) => [...new Set([
  ...array(document.section_order).map(string),
  ...Object.keys(names).filter((key) => key !== 'custom_sections'),
  ...array(document.custom_sections).map(identifier),
])]

export function removeStaleReferences(document: ResumeDocument): ResumeDocument {
  const ids = new Set<string>()
  function visit(value: DocumentValue) {
    if (Array.isArray(value)) { value.forEach(visit); return }
    if (!value || typeof value !== 'object') return
    if (typeof value.id === 'string') ids.add(value.id)
    Object.values(value).forEach(visit)
  }
  visit(document)
  const validSections = new Set(sections({ ...document, section_order: [] }))
  return {
    ...document,
    skills: array(document.skills).map((value) => {
      const skill = object(value)
      return { ...skill, evidence: array(skill.evidence).filter((evidence) => ids.has(string(object(evidence).entry_id))) }
    }),
    section_order: array(document.section_order).filter((key) => validSections.has(string(key))),
    section_configuration: array(document.section_configuration).filter((value) => validSections.has(string(object(value).section_id))),
  }
}

export function duplicateEntry(value: DocumentValue): DocumentValue {
  if (Array.isArray(value)) return value.map(duplicateEntry)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.entries(value).map(([key, child]) =>
    [key, key === 'id' ? crypto.randomUUID() : duplicateEntry(child)]))
}

export function move<T>(values: T[], index: number, target: number): T[] {
  if (target < 0 || target >= values.length) return values
  const result = [...values]
  result.splice(target, 0, ...result.splice(index, 1))
  return result
}
