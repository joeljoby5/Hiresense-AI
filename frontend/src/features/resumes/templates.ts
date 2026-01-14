export const templates = [
  { id: 'professional-classic', name: 'Professional Classic', font: 'Georgia', size: 11, line: 1.2, spacing: 10 },
  { id: 'minimalist', name: 'Minimalist', font: 'Arial', size: 11, line: 1.35, spacing: 14 },
  { id: 'modern-technical', name: 'Modern Technical', font: 'Calibri', size: 11, line: 1.2, spacing: 10 },
  { id: 'graduate', name: 'Graduate and Fresher', font: 'Georgia', size: 11, line: 1.3, spacing: 12 },
  { id: 'software', name: 'Software Engineering', font: 'Arial', size: 10, line: 1.2, spacing: 9 },
  { id: 'compact', name: 'Compact One-Page', font: 'Helvetica', size: 9, line: 1.1, spacing: 6 },
] as const

export function getTemplate(id: string) {
  return templates.find((template) => template.id === id) ?? templates[0]
}
