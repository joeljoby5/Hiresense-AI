import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import type { DocumentObject, DocumentValue, ResumeDocument } from './document'
import { array, identifier, label, object, sections, string } from './schema'
import { getTemplate } from './templates'

const dates = new Intl.DateTimeFormat('en', { month: 'short', timeZone: 'UTC' })

function date(value: DocumentValue | undefined) {
  const { year, month } = object(value)
  if (typeof year !== 'number') return ''
  return typeof month === 'number' ? dates.format(new Date(Date.UTC(2000, month - 1))) + ' ' + year : String(year)
}

function text(values: Array<DocumentValue | undefined>, separator = ' · ') {
  return values.map(string).map((value) => value.trim()).filter(Boolean).join(separator)
}

function Links({ values }: { values: DocumentValue[] }) {
  return values.map((value, index) => {
    const link = object(value)
    const url = string(link.url)
    if (!/^https?:\/\//i.test(url)) return null
    return <a key={identifier(value) || index} href={url} target="_blank" rel="noreferrer">{string(link.label) || url}</a>
  })
}

function Entry({ entry }: { entry: DocumentObject }) {
  const headline = text([entry.position || entry.degree || entry.title || entry.name, entry.field_of_study])
  const org = text([entry.organization || entry.institution || entry.issuer, entry.location])
  const period = [date(entry.start_date), entry.ongoing ? 'Present' : date(entry.end_date)].filter(Boolean).join(' – ')
  const extra = [
    date(entry.issue_date), entry.expiration_date && 'Expires ' + date(entry.expiration_date),
    entry.expected_graduation && 'Expected ' + date(entry.expected_graduation),
    date(entry.date), entry.employment_type, entry.proficiency, entry.status, entry.category,
    text([object(entry.score).value, object(entry.score).system, object(entry.score).scale], ' '),
    entry.credential_id,
  ]
  const meta = text([...extra, period])
  const bullets = [...array(entry.bullets), ...array(entry.contributions)].filter((value) => string(object(value).text))
  const tags = [...array(entry.technologies), ...array(entry.coursework).map((value) => object(value).name)].map(string).filter(Boolean).join(', ')
  const links = [...array(entry.links), ...(entry.credential_url ? [{ url: entry.credential_url }] : [])]
  if (!headline && !org && !meta && !entry.description && !bullets.length && !tags && !links.length) return null
  return <div className="paper-entry">
    {headline && <h4>{headline}</h4>}
    {org && <p>{org}</p>}
    {meta && <p className="paper-meta">{meta}</p>}
    {entry.description && <p>{string(entry.description)}</p>}
    {!!bullets.length && <ul>{bullets.map((value, index) => <li key={identifier(value) || index}>{string(object(value).text)}</li>)}</ul>}
    {tags && <p>{tags}</p>}
    {!!links.length && <div className="paper-links"><Links values={links} /></div>}
  </div>
}

function sectionBody(id: string, document: ResumeDocument): ReactNode {
  const value = document[id]
  if (typeof value === 'string') return value.trim() ? <p>{value}</p> : null
  const section = object(array(document.custom_sections).find((item) => identifier(item) === id))
  const entries = array(value ?? section.entries)
  if (!entries.length && !section.description) return null
  if (id === 'skills' || id === 'relevant_coursework') {
    const names = entries.map((item) => string(object(item).name)).filter(Boolean).join(', ')
    return names ? <p>{names}</p> : null
  }
  return <>{section.description && <p>{string(section.description)}</p>}{entries.map((entry, index) => <Entry key={identifier(entry) || index} entry={object(entry)} />)}</>
}

export function ResumePreview({ document }: { document: ResumeDocument }) {
  const [zoom, setZoom] = useState(100)
  const viewport = useRef<HTMLDivElement>(null)
  const sheet = useRef<HTMLElement>(null)
  const [pageCount, setPageCount] = useState(1)
  const settings = object(document.presentation_settings)
  const margins = object(settings.margins)
  const config = array(document.section_configuration).map(object)
  const configuration = (id: string) => config.find((item) => item.section_id === id)
  const custom = array(document.custom_sections)
  const person = object(document.personal_information)
  const selected = getTemplate(string(settings.template_id))
  const letter = settings.page_size === 'Letter'
  const pageHeight = (letter ? 279.4 : 297) * (96 / 25.4) * zoom / 100
  useEffect(() => {
    const paperElement = sheet.current
    if (!paperElement) return
    const observer = new ResizeObserver(() => {
      setPageCount(Math.max(1, Math.ceil((paperElement.getBoundingClientRect().height - 1) / pageHeight)))
    })
    observer.observe(paperElement)
    return () => observer.disconnect()
  }, [pageHeight])
  const paper: CSSProperties = {
    '--paper-accent': string(settings.accent_color) || '#243B53',
    '--paper-section': Number(settings.section_spacing ?? 8) + 'pt',
    '--paper-padding': ['top', 'right', 'bottom', 'left'].map((side) => Number(margins[side] ?? 20) + 'mm').join(' '),
    fontSize: Number(settings.font_size ?? 11) + 'pt',
    fontFamily: string(settings.font_family) || 'Arial',
    lineHeight: Number(settings.line_spacing ?? 1.15),
    width: letter ? '215.9mm' : '210mm',
    minHeight: letter ? '279.4mm' : '297mm',
    zoom: zoom / 100,
  } as CSSProperties
  return <section className="surface preview-panel" aria-label="Resume preview">
    <div className="preview-heading"><h2>Live preview</h2><label>Zoom<select value={zoom} onChange={(event) => setZoom(Number(event.target.value))}>
      {[35, 50, 65, 80, 100, 125].map((level) => <option key={level} value={level}>{level}%</option>)}
    </select></label></div>
    <p className="muted">Estimated pagination · {string(settings.page_size) || 'A4'}</p>
    {pageCount > 1 && <p className="muted">About {pageCount} pages. Consider shortening entries if you need a one-page resume.</p>}
    <div className="paper-viewport" ref={viewport} tabIndex={0} aria-label="Scroll document preview">
      <article ref={sheet} className={'paper template-' + selected.id} style={paper}>
        {sections(document).filter((id) => configuration(id)?.visible !== false).map((id) => {
          if (id === 'personal_information') return <header className="paper-header" key={id}>
          {person.full_name && <h2>{string(person.full_name)}</h2>}
          {person.headline && <p className="paper-headline">{string(person.headline)}</p>}
          {text([person.email, person.phone, person.location]) && <p>{text([person.email, person.phone, person.location])}</p>}
          <div className="paper-links"><Links values={array(person.links)} /></div>
          </header>
          const body = sectionBody(id, document)
          if (!body) return null
          return <section className="paper-section" key={id}>
            <h3>{string(configuration(id)?.title) || string(object(custom.find((item) => identifier(item) === id)).title) || label(id)}</h3>
            {body}
          </section>
        })}
      </article>
    </div>
    {pageCount > 1 && <label className="preview-pages">Go to preview page
      <select value="" onChange={(event) => viewport.current?.scrollTo({ top: (Number(event.target.value) - 1) * pageHeight })}>
        <option value="" disabled>Select page</option>
        {Array.from({ length: Math.min(pageCount, 500) }, (_, index) => <option key={index} value={index + 1}>{index + 1}</option>)}
      </select>
    </label>}
  </section>
}
