import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { observer } from 'mobx-react-lite'
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, ChevronDown, ChevronRight, Download, EyeOff, Plus, RefreshCw, Save, Trash2, X } from 'lucide-react'
import type { AppStore, GenerationStore } from './store'
import { MAX_CHARACTERS } from './store'
import { CharacterPositions } from './CharacterPositions'
import { PromptEditor } from './PromptEditor'
import { SectionAssistantButton, type OpenSectionAssistant } from './SectionAssistant'
import {
  CHARACTER_SECTION_KEYS, SHARED_SECTION_KEYS, SECTION_LABELS, compatibleEntries, sectionAt, sectionReferenceKey,
  snapshotEntries, snapshotGroupKey, type PromptSection, type PromptSnapshot, type PromptSnapshotCreate,
  type PromptSnapshotEntry, type PromptTextTarget, type SectionReference, type SnapshotImportMode,
} from './prompt-sections'

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const dialog = dialogRef.current
    dialog?.showModal()
    return () => {
      dialog?.close()
      if (opener?.isConnected) opener.focus({ preventScroll: true })
      else document.getElementById('prompt-drawer-toggle')?.focus({ preventScroll: true })
    }
  }, [])
  return createPortal(<dialog className="snapshot-dialog" ref={dialogRef} aria-labelledby="snapshot-dialog-title"
    onCancel={event => { event.preventDefault(); closeRef.current() }}
    onKeyDown={event => { if (event.key === 'Escape') event.stopPropagation() }}
    onClick={event => { if (event.target === event.currentTarget) closeRef.current() }}>
    <div className="snapshot-dialog-content">
      <header className="snapshot-dialog-header"><h2 id="snapshot-dialog-title">{title}</h2>
        <button className="icon-button" type="button" aria-label="关闭快照窗口" onClick={onClose}><X size={18} aria-hidden="true" /></button></header>
      {children}
    </div>
  </dialog>, document.body)
}

function EntryPreview({ entries }: { entries: PromptSnapshotEntry[] }) {
  return <ul className="snapshot-entry-preview">{entries.map((entry, index) => <li key={index}>
    <strong>{entry.scope === 'shared' ? '公共' : `来源人物 ${entry.character_index + 1}`} · {SECTION_LABELS[entry.section]}</strong>
    <span>{entry.text || '（留空）'}</span>
  </li>)}</ul>
}

const SaveSnapshot = observer(({ store, entries, onClose }: { store: AppStore; entries: PromptSnapshotEntry[]; onClose: () => void }) => {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const pending = useRef<PromptSnapshotCreate | null>(null)
  const alive = useRef(true)
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  const library = store.promptSnapshots
  const [submitted, setSubmitted] = useState(false)

  async function save() {
    if (library.saving || library.deletingId !== null) return
    setError('')
    if (!name.trim() || name.trim().length > 100) { setError('请输入快照名称（最多 100 字符）。'); return }
    try {
      // Keep the exact ID/content for an explicit retry after a lost response.
      pending.current ??= { id: crypto.randomUUID(), name: name.trim(), entries: entries.map(entry => ({ ...entry })) }
    } catch { setError('浏览器无法创建快照编号，请通过 HTTPS 使用支持的浏览器。'); return }
    setSubmitted(true)
    const saved = await library.save(pending.current)
    if (saved && alive.current) onClose()
  }

  return <Modal title="保存提示词快照" onClose={onClose}>
    <div className="snapshot-dialog-scroll">
      <p className="prompt-hint">保存所选分区的文字与分类，保留 // 标签注释；分区隐藏状态和生成设置不会保存。快照仅对当前账号可见。</p>
      <label className="field"><span>快照名称</span><input value={name} maxLength={100} autoComplete="off" autoFocus
        disabled={submitted} onChange={event => setName(event.target.value)} onKeyDown={event => {
          if (event.key === 'Enter') { event.preventDefault(); void save() }
        }} /></label>
      <EntryPreview entries={entries} />
      {(error || library.mutationError) && <p role="alert" className="alert">{error || library.mutationError}</p>}
      {submitted && library.mutationError && <p className="prompt-hint">可再次点击保存核对同一份快照；修改名称请关闭后重新保存。</p>}
    </div>
    <footer className="snapshot-dialog-footer"><button className="secondary" type="button" onClick={onClose}>取消</button>
      <button className="primary" type="button" disabled={library.saving || library.deletingId !== null} onClick={() => void save()}>
        <Save size={15} aria-hidden="true" />{library.saving ? '正在保存...' : '保存快照'}</button></footer>
  </Modal>
})

const ImportSnapshots = observer(({ store, destination, onClose }: { store: AppStore; destination?: SectionReference; onClose: () => void }) => {
  const library = store.promptSnapshots
  const generation = store.generation
  const [selected, setSelected] = useState<string[]>([])
  const selectedRef = useRef<string[]>([])
  const [details, setDetails] = useState<Record<string, PromptSnapshot>>({})
  const [mappings, setMappings] = useState<Record<string, string>>({})
  const [mode, setMode] = useState<SnapshotImportMode>('append')
  const [error, setError] = useState('')
  const [applying, setApplying] = useState(false)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    void library.load(0)
    return () => { alive.current = false }
  }, [library])

  async function fetchDetail(id: string) {
    const epoch = library.sessionEpoch
    const snapshot = await library.detail(id)
    if (snapshot && alive.current && epoch === library.sessionEpoch && selectedRef.current.includes(id)) setDetails(current => ({ ...current, [id]: snapshot }))
  }

  function select(id: string, checked: boolean) {
    setError('')
    const next = selectedRef.current.filter(value => value !== id)
    if (checked) next.push(id)
    selectedRef.current = next
    setSelected(next)
    if (!checked) setDetails(current => { const next = { ...current }; delete next[id]; return next })
    if (checked) void fetchDetail(id)
  }

  function move(index: number, step: number) {
    const next = [...selectedRef.current]
    const destination = index + step
    if (destination < 0 || destination >= next.length) return
    const moved = next[index]
    next[index] = next[destination]
    next[destination] = moved
    selectedRef.current = next
    setSelected(next)
  }

  async function remove(id: string) {
    if (!window.confirm('确定永久删除这份提示词快照？')) return
    if (await library.delete(id) && alive.current) {
      select(id, false)
    }
  }

  async function apply() {
    if (applying || !selected.length || library.deletingId !== null) return
    const epoch = library.sessionEpoch
    setApplying(true)
    setError('')
    try {
      // Re-read each immutable snapshot to reject deleted/stale selections before editing.
      const snapshots = await Promise.all(selected.map(id => library.detail(id, true)))
      if (!alive.current || epoch !== library.sessionEpoch) return
      if (snapshots.some(snapshot => snapshot === null)) throw new Error('部分快照已被删除或无法读取，请检查所选快照；草稿未修改。')
      generation.importSnapshots(snapshots.filter((snapshot): snapshot is PromptSnapshot => snapshot !== null), mode, mappings, destination)
      onClose()
    } catch (caught) {
      if (alive.current && epoch === library.sessionEpoch) setError(caught instanceof Error ? caught.message : '无法导入快照，草稿未修改。')
    } finally { if (alive.current && epoch === library.sessionEpoch) setApplying(false) }
  }

  const destinationValid = !destination || Boolean(sectionAt(generation.draft, destination))
  const ready = selected.length > 0 && selected.every(id => details[id] && (!destination || compatibleEntries(details[id], destination).length > 0))
  return <Modal title={destination ? `导入到${SECTION_LABELS[destination.section]}` : '导入提示词快照'} onClose={onClose}>
    <div className="snapshot-dialog-scroll">
      <p className="prompt-hint">选择快照后，按下方显示顺序导入。{destination ? '只导入相同分类的分区。' : '公共按分区归位；每组来源人物需要选择目标。'}现有分区的隐藏状态会保留。</p>
      <fieldset className="snapshot-import-options" disabled={applying}>
        <legend className="sr-only">快照选择与导入方式</legend>
        <div className="snapshot-library-heading"><h3>账号快照库</h3>
          <button className="icon-button" type="button" aria-label="刷新快照列表" disabled={library.loading || library.deletingId !== null}
            onClick={() => void library.load()}><RefreshCw size={16} aria-hidden="true" /></button></div>
        {library.listError && <p role="alert" className="alert">{library.listError}</p>}
        {library.mutationError && <p role="alert" className="alert">{library.mutationError}</p>}
        {library.loading && <p role="status" className="subtle">正在加载快照...</p>}
        {!library.loading && !library.listError && !library.items.length && <p className="subtle">暂无快照，可先选择提示词分区并保存。</p>}
        <div className="snapshot-library-list">{library.items.map(item => <div className="snapshot-library-row" key={item.id}>
          <label><input type="checkbox" checked={selected.includes(item.id)} disabled={library.deletingId !== null}
            onChange={event => select(item.id, event.target.checked)} /><span><strong>{item.name}</strong>
              <small>{item.entry_count} 个分区 · {new Date(item.created_at * 1000).toLocaleString()}</small></span></label>
          <button className="icon-button danger" type="button" aria-label={`删除快照 ${item.name}`} disabled={library.deletingId !== null || library.saving}
            onClick={() => void remove(item.id)}><Trash2 size={15} aria-hidden="true" /></button>
        </div>)}</div>
        <div className="pager"><button type="button" className="icon-button" aria-label="上一页快照" disabled={library.loading || library.deletingId !== null || library.offset === 0}
          onClick={() => void library.load(Math.max(0, library.offset - 20))}><ArrowLeft size={17} aria-hidden="true" /></button>
          <span>第 {Math.floor(library.offset / 20) + 1} 页</span>
          <button type="button" className="icon-button" aria-label="下一页快照" disabled={library.loading || library.deletingId !== null || library.nextOffset === null}
            onClick={() => { if (library.nextOffset !== null) void library.load(library.nextOffset) }}><ArrowRight size={17} aria-hidden="true" /></button></div>
        <label className="field"><span>导入方式</span><select value={mode} onChange={event => setMode(event.target.value as SnapshotImportMode)}>
          <option value="append">追加（默认，保留重复词条）</option><option value="replace">替换所导入的分区</option>
        </select></label>
        <p className="prompt-hint">{mode === 'append' ? '按顺序追加非空文字，以逗号分隔。' : '只替换涉及的分区；重复目标以最后一条为准，包括空文本。'}</p>
        <h3 className="snapshot-selection-title">导入顺序与目标 · {selected.length} 份</h3>
        <ol className="snapshot-selected-list">{selected.map((id, index) => {
          const snapshot = details[id]
          const entries = snapshot ? destination ? compatibleEntries(snapshot, destination) : snapshot.entries : []
          const groups = [...new Set(entries.flatMap(entry => entry.scope === 'character' ? [entry.character_index] : []))]
          return <li key={id} className="snapshot-selected-item">
            <div className="snapshot-selected-heading"><strong>{index + 1}. {snapshot?.name ?? library.items.find(item => item.id === id)?.name ?? '快照'}</strong>
              <div><button className="icon-button" type="button" aria-label={`上移第 ${index + 1} 份快照`} disabled={index === 0} onClick={() => move(index, -1)}><ArrowUp size={14} aria-hidden="true" /></button>
                <button className="icon-button" type="button" aria-label={`下移第 ${index + 1} 份快照`} disabled={index + 1 === selected.length} onClick={() => move(index, 1)}><ArrowDown size={14} aria-hidden="true" /></button>
                <button className="icon-button" type="button" aria-label={`取消选择第 ${index + 1} 份快照`} onClick={() => select(id, false)}><X size={14} aria-hidden="true" /></button></div></div>
            {library.loadingDetails.has(id) && <p role="status" className="subtle">正在读取分区...</p>}
            {library.detailErrors.get(id) && <p role="alert" className="alert">{library.detailErrors.get(id)}
              <button className="text-action" type="button" onClick={() => void fetchDetail(id)}>重新读取</button></p>}
            {snapshot && !entries.length && <p className="alert">此快照没有匹配的分区，请取消选择。</p>}
            {!destination && groups.map(characterIndex => {
              const key = snapshotGroupKey(id, characterIndex)
              const target = mappings[key] ?? ''
              const missing = target !== '' && target !== 'new' && !generation.draft.character_prompts.some(person => person.id === target)
              return <label className="field snapshot-mapping" key={key}><span>来源人物 {characterIndex + 1} 导入到</span>
                <select value={target} onChange={event => setMappings(current => ({ ...current, [key]: event.target.value }))}>
                  <option value="" disabled>请选择目标人物</option>
                  {missing && <option value={target} disabled>原目标已被移除，请重新选择</option>}
                  {generation.draft.character_prompts.map((person, personIndex) => <option value={person.id} key={person.id}>现有人物 {personIndex + 1}</option>)}
                  <option value="new">新建独立人物</option>
                </select></label>
            })}
            {entries.length > 0 && <EntryPreview entries={entries} />}
          </li>
        })}</ol>
      </fieldset>
      {!destinationValid && <p role="alert" className="alert">目标分区已移除，请关闭后重新选择。</p>}
      {error && <p role="alert" className="alert">{error}</p>}
    </div>
    <footer className="snapshot-dialog-footer"><button className="secondary" type="button" onClick={onClose}>取消</button>
      <button className="primary" type="button" disabled={applying || !ready || !destinationValid || library.deletingId !== null}
        onClick={() => void apply()}><Download size={15} aria-hidden="true" />{applying ? '正在核对...' : '导入所选快照'}</button></footer>
  </Modal>
})

const SectionEditor = observer(({ generation, reference, section, label, selected, onSelect, onSave, onImport, assistantTarget, onAssistant }: {
  generation: GenerationStore; reference: SectionReference; section: PromptSection; label: string; selected: boolean
  onSelect: (selected: boolean) => void; onSave: () => void; onImport: () => void
  assistantTarget: PromptTextTarget | null; onAssistant: OpenSectionAssistant
}) => {
  const id = `prompt-section-${sectionReferenceKey(reference)}`
  return <section className={`prompt-section-card${section.enabled ? '' : ' section-disabled'}`} aria-label={label}>
    <div className="prompt-section-heading"><label className="section-selection"><input type="checkbox" checked={selected}
      aria-label={`选择${label}用于保存快照`} onChange={event => onSelect(event.target.checked)} /><span>{SECTION_LABELS[reference.section]}</span></label>
      <div className="prompt-section-actions"><SectionAssistantButton target={reference} label={label} activeTarget={assistantTarget} onOpen={onAssistant} />
        <button className="text-action section-visibility-toggle" type="button" aria-pressed={!section.enabled}
        aria-label={`${section.enabled ? '隐藏' : '显示'}${label}`} onClick={() => generation.setSectionEnabled(reference, !section.enabled)}>{section.enabled ? '隐藏' : '显示'}</button>
        <button className="text-action" type="button" aria-label={`保存${label}快照`} onClick={onSave}>保存</button>
        <button className="text-action" type="button" aria-label={`导入快照到${label}`} onClick={onImport}>导入</button></div></div>
    {!section.enabled && <p className="section-hidden-note"><EyeOff size={14} aria-hidden="true" /><span>已隐藏 · 保留文字，不参与生成</span></p>}
    <div className="field"><PromptEditor id={id} label={label} value={section.text} placeholder={`填写${SECTION_LABELS[reference.section]}提示词`} rows={2}
      onFocus={() => { if (section.enabled) generation.setPositiveTagTarget(sectionReferenceKey(reference)) }}
      onChange={text => generation.setSectionText(reference, text)} /></div>
  </section>
})

function CharacterCard({ label, onRemove, children }: { label: string; onRemove: () => void; children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const bodyId = useId()
  return <section className={`character-card${collapsed ? ' character-card-collapsed' : ''}`} aria-label={label}>
    <div className="character-card-heading"><h4><button className="character-disclosure" type="button"
      aria-expanded={!collapsed} aria-controls={bodyId} onClick={event => {
        // Keep focus outside the hidden editors and their portaled assistant.
        event.currentTarget.focus({ preventScroll: true })
        setCollapsed(current => !current)
      }}>
      {collapsed ? <ChevronRight size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}
      {label}<span>{collapsed ? '展开' : '收起'}</span>
    </button></h4><button className="icon-button danger" type="button" aria-label={`移除${label}`} onClick={onRemove}>
      <X size={15} aria-hidden="true" /></button></div>
    <div className="section-grid character-card-body" id={bodyId} hidden={collapsed}>{children}</div>
  </section>
}

export const PromptSectionsEditor = observer(({ store, assistantTarget, onAssistant }: {
  store: AppStore; assistantTarget: PromptTextTarget | null; onAssistant: OpenSectionAssistant
}) => {
  const generation = store.generation
  const draft = generation.draft
  const [selected, setSelected] = useState<SectionReference[]>([])
  const [dialog, setDialog] = useState<{ mode: 'save'; entries: PromptSnapshotEntry[] } | { mode: 'import'; destination?: SectionReference } | null>(null)
  const [error, setError] = useState('')
  const currentSelection = selected.filter(reference => sectionAt(draft, reference))
  const selectedKeys = new Set(currentSelection.map(sectionReferenceKey))

  function select(reference: SectionReference, checked: boolean) {
    const key = sectionReferenceKey(reference)
    setSelected(current => [...current.filter(item => sectionReferenceKey(item) !== key), ...(checked ? [reference] : [])])
  }

  function save(references: SectionReference[]) {
    setError('')
    try {
      const entries = snapshotEntries(draft, references)
      if (!entries.length || !entries.some(entry => entry.text.trim())) throw new Error('请选择至少一个有文字的分区。')
      store.promptSnapshots.clearMutationError()
      setDialog({ mode: 'save', entries })
    } catch (caught) { setError(caught instanceof Error ? caught.message : '无法读取所选分区。') }
  }

  function openImport(destination?: SectionReference) {
    setError('')
    store.promptSnapshots.clearMutationError()
    setDialog({ mode: 'import', destination })
  }

  function section(reference: SectionReference, label: string) {
    const value = sectionAt(draft, reference)
    if (!value) return null
    return <SectionEditor key={sectionReferenceKey(reference)} generation={generation} reference={reference} section={value} label={label}
      selected={selectedKeys.has(sectionReferenceKey(reference))} onSelect={checked => select(reference, checked)}
      assistantTarget={assistantTarget} onAssistant={onAssistant}
      onSave={() => save([reference])} onImport={() => openImport(reference)} />
  }

  return <div className="section-composer">
    <div className="section-composer-toolbar"><span>提示词分区</span><div>
      <button className="secondary" type="button" disabled={!currentSelection.length} onClick={() => save(currentSelection)}><Save size={14} aria-hidden="true" />保存所选{currentSelection.length ? ` (${currentSelection.length})` : ''}</button>
      <button className="secondary" type="button" onClick={() => openImport()}><Download size={14} aria-hidden="true" />导入快照</button>
    </div></div>
    {error && <p role="alert" className="alert">{error}</p>}
    <section className="shared-sections" aria-labelledby="shared-sections-title"><h3 id="shared-sections-title">公共</h3>
      <div className="section-grid">{SHARED_SECTION_KEYS.map(key => section({ scope: 'shared', section: key }, `公共 · ${SECTION_LABELS[key]}`))}</div>
    </section>
    <p className="prompt-hint">画风和启用的公共提示词至少填写一项，合计最多 3000 字符。每个人物启用的分区合计最多 3000 字符。</p>
    <section className="character-section" aria-labelledby="characters-title">
      <div className="character-heading"><h3 id="characters-title">人物 <span>{draft.character_prompts.length} / {MAX_CHARACTERS}</span></h3>
        <button className="text-action" id="add-character" type="button" disabled={draft.character_prompts.length >= MAX_CHARACTERS}
          onClick={() => {
            const id = generation.addCharacter()
            if (id) requestAnimationFrame(() => document.getElementById(`prompt-section-character:${id}:character`)?.focus())
          }}><Plus size={15} aria-hidden="true" />添加人物</button>
      </div>
      <p className="prompt-hint">每个人物独立填写分区，可自动安排或手动定位。没有启用文字的人物保留在草稿中，不参与生成。</p>
      <CharacterPositions generation={generation} />
      <div className="section-character-list">{draft.character_prompts.map((person, index) => <CharacterCard key={person.id} label={`人物 ${index + 1}`}
        onRemove={() => { generation.removeCharacter(person.id); requestAnimationFrame(() => document.getElementById('add-character')?.focus()) }}>
        {CHARACTER_SECTION_KEYS.map(key => section({ scope: 'character', characterId: person.id, section: key }, `人物 ${index + 1} · ${SECTION_LABELS[key]}`))}
      </CharacterCard>)}</div>
    </section>
    {dialog?.mode === 'save' && <SaveSnapshot store={store} entries={dialog.entries} onClose={() => setDialog(null)} />}
    {dialog?.mode === 'import' && <ImportSnapshots store={store} destination={dialog.destination} onClose={() => setDialog(null)} />}
  </div>
})
