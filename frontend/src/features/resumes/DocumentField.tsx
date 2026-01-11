import { useId } from 'react'
import { ArrowDown, ArrowUp, Copy, Plus, Trash2 } from 'lucide-react'
import type { DocumentValue } from './document'
import { array, duplicateEntry, identifier, label, move, newValue, object, resolve } from './schema'
import type { FieldSchema } from './schema'

interface Props {
  name: string
  schema: FieldSchema
  value: DocumentValue
  change: (value: DocumentValue) => void
  required?: boolean
}

export function DocumentField({ name, schema, value, change, required }: Props) {
  const id = useId()
  const field = resolve(schema)
  const title = label(name)
  if (field.type === 'array' && field.items) {
    const items = array(value)
    const itemSchema = field.items
    const isObject = resolve(itemSchema).type === 'object'
    return <fieldset className="field-group">
      <legend>{title}</legend>
      {items.map((item, index) => <div key={identifier(item) || index} className="array-entry">
        <div className="entry-actions row">
          <span>{title} {index + 1}</span>
          <button className="icon-button" disabled={!index} aria-label={'Move ' + title + ' ' + (index + 1) + ' up'} onClick={() => change(move(items, index, index - 1))}><ArrowUp size={16} /></button>
          <button className="icon-button" disabled={index === items.length - 1} aria-label={'Move ' + title + ' ' + (index + 1) + ' down'} onClick={() => change(move(items, index, index + 1))}><ArrowDown size={16} /></button>
          <button className="icon-button" disabled={items.length >= 200} aria-label={'Duplicate ' + title + ' ' + (index + 1)} onClick={() => change([...items.slice(0, index + 1), duplicateEntry(item), ...items.slice(index + 1)])}><Copy size={16} /></button>
          <button className="icon-button" aria-label={'Remove ' + title + ' ' + (index + 1)} onClick={() => change(items.filter((_, position) => position !== index))}><Trash2 size={16} /></button>
        </div>
        <DocumentField name={isObject ? '' : 'value'} schema={itemSchema} value={item} required
          change={(next) => change(items.map((current, position) => position === index ? next : current))} />
      </div>)}
      <button className="button secondary" disabled={items.length >= 200} onClick={() => change([...items, newValue(itemSchema, true)])}><Plus size={16} /> Add item to {title.toLowerCase()}</button>
    </fieldset>
  }
  if (field.type === 'object') {
    const current = object(value)
    const nullable = schema.anyOf?.some((option) => option.type === 'null')
    return <fieldset className={name ? 'field-group' : 'field-inline'}>
      {name && <legend>{title}</legend>}
      {value !== null && Object.entries(field.properties ?? {}).filter(([key]) =>
        !['id', 'canonical_skill_id', 'evidence'].includes(key) && !(key === 'end_date' && current.ongoing),
      ).map(([key, child]) => <DocumentField key={key} name={key} schema={child} value={current[key] ?? newValue(child)}
        required={field.required?.includes(key)} change={(next) => change({
          ...current, [key]: next, ...(key === 'ongoing' && next ? { end_date: null } : {}),
        })} />)}
      {nullable && <button className="button secondary" onClick={() => change(value === null ? newValue(schema, true) : null)}>
        {value === null ? 'Set' : 'Clear'} {title.toLowerCase()}
      </button>}
    </fieldset>
  }

  if (field.type === 'boolean') return <label className="check-label"><input type="checkbox" checked={value === true} onChange={(event) => change(event.target.checked)} />{title}</label>
  if (field.enum) return <label>{title}<select value={String(value ?? '')} onChange={(event) => change(event.target.value)}>
    {field.enum.map((option) => <option key={option}>{option}</option>)}
  </select></label>
  const numeric = field.type === 'number' || field.type === 'integer'
  const nullable = schema.anyOf?.some((option) => option.type === 'null')
  const text = String(value ?? '')
  const multiline = ['description', 'text', 'professional_summary', 'career_objective'].includes(name)
  const update = (input: string) => change(input === '' && (numeric || nullable) ? null : numeric ? Number(input) : input)
  const options = { id, required: required || Boolean(field.minLength), value: text, maxLength: field.maxLength,
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => update(event.target.value) }
  return <label htmlFor={id}>{title}
    {multiline ? <textarea {...options} /> : <input {...options}
      type={numeric ? 'number' : field.format === 'email' ? 'email' : field.format === 'uri' ? 'url' : 'text'}
      min={field.minimum} max={field.maximum} step={field.type === 'number' ? 'any' : undefined} />}
    {multiline && field.maxLength && <small className="muted">{text.length.toLocaleString()} / {field.maxLength.toLocaleString()} characters</small>}
  </label>
}
