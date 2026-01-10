// JSON values from the canonical backend document. Field definitions come from its generated schema.
export type DocumentValue = string | number | boolean | null | DocumentObject | DocumentValue[]
export interface DocumentObject { [key: string]: DocumentValue }
export interface ResumeDocument extends DocumentObject { schema_version: 1 }
