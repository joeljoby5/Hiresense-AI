import { useState } from 'react'
import { ArrowDown, ArrowUp, Redo2, Undo2 } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useResume } from './api'
import type { Resume } from './api'
import { DocumentField } from './DocumentField'
import type { DocumentValue, ResumeDocument } from './document'
import { Modal, RequestFailure } from './ResumeUi'
import { array, fields, identifier, label, move, newValue, object, removeStaleReferences, resolve, sections, string } from './schema'
import { useDraft } from './useDraft'
import { ResumePreview } from './ResumePreview'
import { getTemplate, templates } from './templates'
import { SummarySuggestion } from './SummarySuggestion'

export function ResumeEditor() {
  const { resumeId = '' } = useParams()
  const query = useResume(resumeId)
  if (query.isPending) return <p role="status">Loading resume…</p>
  if (!query.data) return <RequestFailure error={query.error ?? new Error('Resume unavailable.')} retry={() => void query.refetch()} />
  return <Editor key={resumeId} resume={query.data} />
}

function Editor({ resume }: { resume: Resume }) {
  const draft = useDraft(resume)
  const document = draft.draft.content
  const [params] = useSearchParams()
  const [selected, setSelected] = useState(() => params.get('section') || 'personal_information')
  const [preview, setPreview] = useState(false)
  const [discard, setDiscard] = useState(false)
  const [copied, setCopied] = useState('')
  const sectionIds = sections(document)
  const custom = array(document.custom_sections)
  const section = sectionIds.includes(selected) ? selected : 'personal_information'
  const config = array(document.section_configuration)
  const current = object(config.find((value) => object(value).section_id === section))
  const title = (key: string) => string(object(config.find((value) => object(value).section_id === key)).title)
    || string(object(custom.find((value) => identifier(value) === key)).title) || label(key)
  const update = (content: ResumeDocument) => draft.edit({ ...draft.draft, content })
  const configure = (changes: { title?: string | null; visible?: boolean }) => update({
    ...document,
    section_configuration: [...config.filter((value) => object(value).section_id !== section),
      { ...current, section_id: section, ...changes }],
  })

  function changeSection(value: DocumentValue) {
    const content = fields[section]
      ? { ...document, [section]: value }
      : { ...document, custom_sections: custom.map((item) => identifier(item) === section ? value : item) }
    update(removeStaleReferences(content))
  }

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(draft.draft, null, 2))
      setCopied('Local draft copied.')
    } catch { setCopied('Clipboard access failed. Your draft is still open.') }
  }

  const status = draft.conflict ? 'Revision conflict' : draft.saving ? 'Saving…'
    : draft.failure ? 'Save failed' : draft.dirty ? 'Unsaved changes' : 'Saved'
  return <div className="stack">
    <div className="row"><Link to={'/workspace/resumes/' + resume.id}>Resume history</Link><span className="muted">/</span><span>Editor</span></div>
    <header className="page-heading editor-heading"><div><h1>Resume editor</h1>
      <label>Resume title<input maxLength={200} value={draft.draft.title} onChange={(event) => draft.edit({ ...draft.draft, title: event.target.value })} /></label></div>
      <div className="row">
        <span className="muted" role="status">{status} · Draft {draft.revision}</span>
        <button className="icon-button" aria-label="Undo" disabled={!draft.canUndo} onClick={draft.undo}><Undo2 size={19} /></button>
        <button className="icon-button" aria-label="Redo" disabled={!draft.canRedo} onClick={draft.redo}><Redo2 size={19} /></button>
        <button className="button primary" disabled={!draft.dirty || draft.saving || draft.conflict || !draft.draft.title.trim()} onClick={() => void draft.save()}>Save draft</button>
        <Link className="button secondary" to={'/workspace/resumes/' + resume.id + '#exports'}>Export saved draft</Link>
      </div>
    </header>
    {draft.failure && <RequestFailure error={draft.failure} />}
    {draft.conflict && <div className="surface stack">
      <p>Your edits are still in this editor. {draft.latest ? 'The latest saved version is draft ' + draft.latest.draft_revision + '.' : 'Retrieve the latest saved version before reloading.'}</p>
      <div className="row">
        <button className="button secondary" onClick={() => void copyDraft()}>Copy local draft</button>
        {draft.latest ? <button className="button secondary" onClick={() => setDiscard(true)}>Load latest draft</button>
          : <button className="button secondary" disabled={draft.checking} onClick={() => void draft.loadLatest()}>Check latest draft</button>}
      </div>
      {copied && <p role="status">{copied}</p>}
    </div>}
    <div className="toggle editor-toggle" role="group" aria-label="Editor mode">
      <button className="button secondary" aria-pressed={!preview} onClick={() => setPreview(false)}>Edit</button>
      <button className="button secondary" aria-pressed={preview} onClick={() => setPreview(true)}>Preview</button>
    </div>
    <div className={'editor-grid' + (preview ? ' editor-preview-mode' : '')}>
      <nav className="surface editor-sections" aria-label="Resume sections">
        {sectionIds.map((key) => <button key={key} className="section-link" aria-current={key === section ? 'true' : undefined} onClick={() => setSelected(key)}>{title(key)}</button>)}
        <button className="button secondary" disabled={custom.length >= 185} onClick={() => {
          const value = { ...object(newValue(fields.custom_sections!.items!, true)), title: 'Custom section' }
          update({ ...document, custom_sections: [...custom, value] })
          setSelected(identifier(value))
        }}>Add custom section</button>
        <button className="button secondary section-link" aria-current={selected === 'presentation_settings' ? 'true' : undefined} onClick={() => setSelected('presentation_settings')}>Presentation</button>
      </nav>
      <section className="surface stack editor-fields" aria-label="Section fields">
        <h2>{selected === 'presentation_settings' ? 'Presentation' : title(section)}</h2>
        {selected === 'presentation_settings' ? <>
          <label>Template<select value={string(object(document.presentation_settings).template_id)} onChange={(event) => {
            const template = getTemplate(event.target.value)
            update({ ...document, presentation_settings: {
              ...object(document.presentation_settings), template_id: event.target.value, font_family: template.font,
              font_size: template.size, line_spacing: template.line, section_spacing: template.spacing,
            } })
          }}><option value="default">Classic (default)</option>{templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}</select></label>
          <DocumentField name="" schema={{
            ...fields.presentation_settings,
            $ref: undefined,
            type: 'object',
            properties: Object.fromEntries(Object.entries(resolvePresentation()).filter(([key]) => key !== 'template_id')),
          }} value={document.presentation_settings ?? null} change={(value) => update({ ...document, presentation_settings: value })} />
        </> : <>
          <div className="row">
            <button className="icon-button" aria-label="Move section up" disabled={sectionIds[0] === section} onClick={() => update({ ...document, section_order: move(sectionIds, sectionIds.indexOf(section), sectionIds.indexOf(section) - 1) })}><ArrowUp size={18} /></button>
            <button className="icon-button" aria-label="Move section down" disabled={sectionIds.at(-1) === section} onClick={() => update({ ...document, section_order: move(sectionIds, sectionIds.indexOf(section), sectionIds.indexOf(section) + 1) })}><ArrowDown size={18} /></button>
            <label className="check-label"><input type="checkbox" checked={current.visible !== false} onChange={(event) => configure({ visible: event.target.checked })} /> Show in document</label>
            {!fields[section] && <button className="button secondary" onClick={() => {
              update(removeStaleReferences({ ...document, custom_sections: custom.filter((value) => identifier(value) !== section) }))
              setSelected('personal_information')
            }}>Remove section</button>}
          </div>
          <label>Display heading<input maxLength={200} value={string(current.title)} placeholder={title(section)} onChange={(event) => configure({ title: event.target.value || null })} /></label>
          <DocumentField name={fields[section] ? section : ''} schema={fields[section] ?? fields.custom_sections!.items!} value={document[section] ?? custom.find((value) => identifier(value) === section) ?? null} change={changeSection} />
          {section === 'professional_summary' && <SummarySuggestion resumeId={resume.id} revision={draft.revision}
            summary={string(document.professional_summary)} canSuggest={!draft.dirty && !draft.saving && !draft.conflict}
            apply={changeSection} />}
        </>}
      </section>
      <div className="editor-preview"><ResumePreview document={document} /></div>
    </div>
    {draft.blocker.state === 'blocked' && <Modal title="Leave editor?" onDismiss={draft.blocker.reset}>
      <p>Unsaved edits may be lost when you leave.</p>
      <div className="dialog-actions"><button className="button secondary" onClick={draft.blocker.reset}>Keep editing</button>
        <button className="button danger" onClick={draft.blocker.proceed}>Leave editor</button></div>
    </Modal>}
    {discard && <Modal title="Replace local draft?" onDismiss={() => setDiscard(false)}>
      <p>Loading the saved draft will discard the edits currently in this editor.</p>
      <div className="dialog-actions"><button className="button secondary" onClick={() => setDiscard(false)}>Cancel</button>
        <button className="button danger" onClick={() => { draft.reloadLatest(); setDiscard(false) }}>Load saved draft</button></div>
    </Modal>}
  </div>
}

function resolvePresentation() {
  return resolve(fields.presentation_settings!).properties ?? {}
}
