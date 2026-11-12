import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowUp, Copy, Dices, Download, FileUp, Languages, ListChecks, Plus, Redo2, Save, Search, Shuffle, Trash2, Undo2, X } from 'lucide-react'
import { ApiFailure, errorText, type SearchResults, type WorkspaceApi } from './api'
import {
  DEFAULT_REGIONS, EFFECT_LABELS, LIST_EFFECTS, SKIP_REASONS, bulkAllowOptions, bulkCondition, bulkListEffect, bulkWeight,
  clone, deleteOption, deletePartition, describeCondition, describeEffects, emptyRecipe, findReferences, glossOption, glossTag,
  missingGlosses, moveOrCopy, newId, optionRef, previewStyle, splitTags, targetOptions,
  type BulkTarget, type Condition, type Effects, type ListEffect, type Partition, type Recipe, type RecipeOption, type RecipeSummary,
  type Rule, type SampleItem, type SampleResult,
} from './recipe'
import { MAX_DATASET_ITEMS } from './dataset-run'

const MAX_UNDO = 50

/** Undoable recipe state: every change pushes the previous snapshot. */
function useHistory(initial: Recipe) {
  type State = { past: Recipe[]; present: Recipe; future: Recipe[] }
  const [state, setState] = useState<State>({ past: [], present: initial, future: [] })
  // Mutations run exactly once outside React updaters (they may generate ids or set other
  // state), against the latest committed state kept in a ref.
  const latest = useRef(state)
  const commit = (next: State) => { latest.current = next; setState(next) }
  return {
    recipe: state.present,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
    change(mutate: (draft: Recipe) => void) {
      const current = latest.current
      const next = clone(current.present)
      mutate(next)
      commit({ past: [...current.past, current.present].slice(-MAX_UNDO), present: next, future: [] })
    },
    reset(recipe: Recipe) { commit({ past: [], present: recipe, future: [] }) },
    undo() {
      const current = latest.current
      if (current.past.length) commit({ past: current.past.slice(0, -1), present: current.past[current.past.length - 1], future: [current.present, ...current.future] })
    },
    redo() {
      const current = latest.current
      if (current.future.length) commit({ past: [...current.past, current.present], present: current.future[0], future: current.future.slice(1) })
    },
  }
}

type History = ReturnType<typeof useHistory>
type Tab = 'partitions' | 'order' | 'rules' | 'slots' | 'regions' | 'glossary' | 'json'

export interface RecipeDraftResult {
  items: SampleItem[]
  recipe: { id: string; name: string }
  replace: boolean
}

/** Full-screen recipe editor; sampled items are handed back to the dataset draft list. */
export function RecipeEditor({ api, open, onClose, style, onGenerate }: {
  api: WorkspaceApi
  open: boolean
  onClose: () => void
  /** Current style (first of the pool) for resolved-style previews. */
  style: string
  onGenerate: (result: RecipeDraftResult) => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const history = useHistory(emptyRecipe())
  const { recipe } = history
  const [list, setList] = useState<RecipeSummary[] | null>(null)
  const [currentId, setCurrentId] = useState<string>(() => crypto.randomUUID())
  const [name, setName] = useState('')
  const [loadedAt, setLoadedAt] = useState<number | undefined>(undefined)
  const [saved, setSaved] = useState<string>('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('partitions')
  const [busy, setBusy] = useState(false)
  const dirty = JSON.stringify({ recipe, name }) !== saved
  const initialized = useRef(false)

  useEffect(() => {
    const element = dialog.current
    if (!element) return
    if (open && !element.open) element.showModal()
    if (!open && element.open) element.close()
  }, [open])

  async function refreshList() {
    try { setList(await api.listRecipes()) } catch (failure) { setError(errorText(failure)) }
  }

  async function startFromTemplate(blank: boolean) {
    setError('')
    try {
      const next = blank ? emptyRecipe() : await api.basicRecipeTemplate()
      history.reset(next)
      setCurrentId(crypto.randomUUID())
      setName(blank ? '新配方' : '基础模板')
      setLoadedAt(undefined)
      setSaved('')
      setMessage(blank ? '已新建空白配方（未保存）。' : '已从基础模板新建（未保存）。')
    } catch (failure) { setError(errorText(failure)) }
  }

  useEffect(() => {
    if (!open || initialized.current) return
    initialized.current = true
    void (async () => {
      try {
        const recipes = await api.listRecipes()
        setList(recipes)
        if (recipes.length) await load(recipes[0].id)
        else await startFromTemplate(false)
      } catch (failure) { setError(errorText(failure)) }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  async function load(id: string) {
    if (dirty && saved && !window.confirm('当前配方有未保存的修改，确定切换？')) return
    setError('')
    try {
      const stored = await api.getRecipe(id)
      history.reset(stored.recipe)
      setCurrentId(stored.id)
      setName(stored.name)
      setLoadedAt(stored.updated_at)
      setSaved(JSON.stringify({ recipe: stored.recipe, name: stored.name }))
      setMessage('')
    } catch (failure) { setError(errorText(failure)) }
  }

  async function save(asNew = false) {
    setError('')
    setBusy(true)
    try {
      const id = asNew ? crypto.randomUUID() : currentId
      const label = (asNew ? `${name} 副本` : name).trim() || '未命名配方'
      const stored = await api.saveRecipe(id, label.slice(0, 100), recipe, asNew ? undefined : loadedAt)
      setCurrentId(stored.id)
      setName(stored.name)
      setLoadedAt(stored.updated_at)
      setSaved(JSON.stringify({ recipe: stored.recipe, name: stored.name }))
      history.reset(stored.recipe)
      setMessage(asNew ? '已另存为新配方。' : '已保存。')
      await refreshList()
    } catch (failure) {
      setError(failure instanceof ApiFailure && failure.code === 'recipe_conflict'
        ? '配方已在其他页面修改，请先另存为新配方或重新载入。'
        : errorText(failure))
    } finally { setBusy(false) }
  }

  async function remove() {
    if (!loadedAt || !window.confirm(`删除配方「${name}」？已生成的训练集不受影响。`)) return
    try {
      await api.deleteRecipe(currentId)
      setMessage('已删除配方。')
      setLoadedAt(undefined)
      setSaved('')
      await refreshList()
    } catch (failure) { setError(errorText(failure)) }
  }

  function close() {
    if (dirty && !window.confirm('有未保存的修改，确定关闭？（草稿保留在本页，直到刷新）')) return
    onClose()
  }

  const tabs: Array<[Tab, string]> = [
    ['partitions', '分区与选项'], ['order', '顺序'], ['rules', '规则'], ['slots', '属性槽'],
    ['regions', '部位/资源/状态'], ['glossary', `翻译${missingGlosses(recipe).length ? `（缺 ${missingGlosses(recipe).length}）` : ''}`], ['json', '导入导出'],
  ]

  return <dialog ref={dialog} className="recipe-dialog" aria-labelledby="recipe-title" onCancel={event => { event.preventDefault(); close() }}>
    <div className="recipe-shell">
      <header className="recipe-header">
        <h2 id="recipe-title"><Shuffle size={16} aria-hidden="true" /> 随机训练集配方</h2>
        <select value={loadedAt ? currentId : ''} aria-label="选择配方" onChange={event => { if (event.target.value) void load(event.target.value) }}>
          <option value="">{loadedAt ? '—' : '（未保存的草稿）'}</option>
          {list?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <input className="recipe-name" value={name} maxLength={100} aria-label="配方名称" onChange={event => setName(event.target.value)} />
        <span className="recipe-header-actions">
          <button className="icon-button" type="button" title="撤销" aria-label="撤销" disabled={!history.canUndo} onClick={history.undo}><Undo2 size={15} /></button>
          <button className="icon-button" type="button" title="重做" aria-label="重做" disabled={!history.canRedo} onClick={history.redo}><Redo2 size={15} /></button>
          <button className="secondary" type="button" disabled={busy} onClick={() => void save()}><Save size={14} aria-hidden="true" /> 保存{dirty ? ' *' : ''}</button>
          <button className="text-action" type="button" disabled={busy} onClick={() => void save(true)}><Copy size={13} aria-hidden="true" /> 另存为</button>
          <button className="text-action" type="button" onClick={() => void startFromTemplate(false)}>从基础模板新建</button>
          <button className="text-action" type="button" onClick={() => void startFromTemplate(true)}>新建空白</button>
          <button className="text-action" type="button" disabled={!loadedAt} onClick={() => void remove()}><Trash2 size={13} aria-hidden="true" /> 删除</button>
          <button className="icon-button" type="button" title="关闭" aria-label="关闭" onClick={close}><X size={16} /></button>
        </span>
      </header>
      {(error || message) && <p className={error ? 'alert recipe-message' : 'subtle recipe-message'} role={error ? 'alert' : 'status'}>{error || message}</p>}
      <nav className="recipe-tabs" role="tablist">
        {tabs.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>)}
      </nav>
      <div className="recipe-body">
        <div className="recipe-main">
          {tab === 'partitions' && <PartitionsTab history={history} />}
          {tab === 'order' && <OrderTab history={history} />}
          {tab === 'rules' && <RulesTab history={history} />}
          {tab === 'slots' && <SlotsTab history={history} />}
          {tab === 'regions' && <RegionsTab history={history} />}
          {tab === 'glossary' && <GlossaryTab history={history} api={api} />}
          {tab === 'json' && <JsonTab history={history} name={name} setName={setName} />}
        </div>
        <SamplePanel api={api} recipe={recipe} style={style} recipeRef={{ id: currentId, name: name.trim() || '未命名配方' }}
          saved={Boolean(loadedAt) && !dirty} onGenerate={result => { onGenerate(result); onClose() }} />
      </div>
    </div>
  </dialog>
}

// ------------------------------------------------------------------ partitions and options

function PartitionsTab({ history }: { history: History }) {
  const { recipe } = history
  const [active, setActive] = useState<string>(recipe.draw_order[0] ?? '')
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  const [filter, setFilter] = useState('')
  const [allPartitions, setAllPartitions] = useState(false)
  const anchor = useRef<string | null>(null)
  const part = recipe.partitions.find(item => item.id === active) ?? recipe.partitions[0]

  useEffect(() => {
    if (!recipe.partitions.some(item => item.id === active) && recipe.partitions[0]) setActive(recipe.partitions[0].id)
  }, [recipe, active])

  const rows = useMemo(() => {
    const parts = allPartitions ? recipe.draw_order.map(id => recipe.partitions.find(item => item.id === id)!).filter(Boolean) : part ? [part] : []
    const needle = filter.trim().toLowerCase()
    return parts.flatMap(p => p.options.filter(option => !needle || [option.id, option.label, option.tags, ...glossOption(recipe, option).map(g => g.zh ?? '')]
      .some(text => text?.toLowerCase().includes(needle))).map(option => ({ part: p, option, key: optionRef(p.id, option.id) })))
  }, [recipe, part, filter, allPartitions])

  const targets: BulkTarget[] = [...selected].map(key => { const [partition, option] = key.split('.'); return { partition, option } })

  function toggle(key: string, shift: boolean) {
    setSelected(current => {
      const next = new Set(current)
      if (shift && anchor.current) {
        const keys = rows.map(row => row.key)
        const [from, to] = [keys.indexOf(anchor.current), keys.indexOf(key)].sort((a, b) => a - b)
        if (from >= 0) keys.slice(from, to + 1).forEach(item => next.add(item))
      } else if (next.has(key)) next.delete(key)
      else next.add(key)
      anchor.current = key
      return next
    })
  }

  function addPartition() {
    const label = window.prompt('新分区的中文名（之后可改名）', '新分区')
    if (!label) return
    history.change(draft => {
      const id = newId('partition', draft.partitions.map(item => item.id))
      draft.partitions.push({ id, label, mode: 'one', options: [{ id: NONE, none: true, label: '无', weight: 1 }] })
      draft.draw_order.push(id)
      if (draft.prompt_order) draft.prompt_order.push(id)
      setActive(id)
    })
  }

  function removePartition(target: Partition) {
    const references = findReferences(recipe, target.id)
    if (!window.confirm(`删除分区「${target.label || target.id}」及其 ${target.options.length} 个选项？${references.length ? `\n将同时删除 ${references.length} 处引用：\n${references.map(r => `· ${r.where} 的${r.text}`).join('\n')}` : ''}`)) return
    history.change(draft => deletePartition(draft, target.id))
  }

  function addOption() {
    if (!part) return
    history.change(draft => {
      const p = draft.partitions.find(item => item.id === part.id)!
      p.options.push({ id: newId('option', p.options.map(item => item.id)), label: '', tags: '', weight: 1 })
    })
  }

  function addNone() {
    if (!part || part.options.some(option => option.none)) return
    history.change(draft => { draft.partitions.find(item => item.id === part.id)!.options.push({ id: NONE, none: true, label: '无', weight: 1 }) })
  }

  return <div className="recipe-partitions">
    <aside className="recipe-partition-list" aria-label="分区（按抽取顺序）">
      {recipe.draw_order.map((id, index) => {
        const item = recipe.partitions.find(p => p.id === id)
        if (!item) return null
        return <button key={id} type="button" className={item.id === part?.id && !allPartitions ? 'active' : ''} onClick={() => { setActive(id); setAllPartitions(false) }}>
          <span>{index + 1}. {item.label || item.id}</span><small>{item.options.length}</small>
        </button>
      })}
      <button type="button" className="text-action" onClick={addPartition}><Plus size={13} aria-hidden="true" /> 新建分区</button>
      <button type="button" className={allPartitions ? 'active' : ''} onClick={() => setAllPartitions(true)}><ListChecks size={13} aria-hidden="true" /> 全部选项</button>
    </aside>
    <section className="recipe-partition-detail">
      {part && !allPartitions && <PartitionSettings history={history} part={part} onRemove={() => removePartition(part)} />}
      <div className="recipe-toolbar">
        <input type="search" value={filter} placeholder="筛选选项：tag、中文名" aria-label="筛选选项" onChange={event => setFilter(event.target.value)} />
        <button className="text-action" type="button" onClick={() => setSelected(new Set(rows.map(row => row.key)))}>按筛选全选（{rows.length}）</button>
        <button className="text-action" type="button" disabled={!selected.size} onClick={() => setSelected(new Set())}>清空选择</button>
        {!allPartitions && <button className="text-action" type="button" onClick={addOption}><Plus size={13} aria-hidden="true" /> 新增选项</button>}
        {!allPartitions && part && !part.options.some(option => option.none) && <button className="text-action" type="button" onClick={addNone}><Plus size={13} aria-hidden="true" /> 添加「无」</button>}
      </div>
      {selected.size > 0 && <BulkPanel history={history} targets={targets} onDone={() => setSelected(new Set())} />}
      <ul className="recipe-options">
        {rows.map(row => <OptionRow key={row.key} history={history} part={row.part} option={row.option} showPartition={allPartitions}
          checked={selected.has(row.key)} onToggle={shift => toggle(row.key, shift)} />)}
        {!rows.length && <li className="subtle">没有选项。</li>}
      </ul>
    </section>
  </div>
}

const NONE = 'none'

function PartitionSettings({ history, part, onRemove }: { history: History; part: Partition; onRemove: () => void }) {
  const { recipe } = history
  const update = (mutate: (p: Partition) => void) => history.change(draft => mutate(draft.partitions.find(item => item.id === part.id)!))
  const references = findReferences(recipe, part.id)
  return <div className="recipe-partition-settings">
    <label>名称 <input value={part.label ?? ''} maxLength={100} onChange={event => update(p => { p.label = event.target.value })} /></label>
    <span className="recipe-id" title="分区 ID，引用都用它，改名不影响">id: {part.id}</span>
    <label>抽取方式 <select value={part.mode ?? 'one'} onChange={event => update(p => { p.mode = event.target.value as 'one' | 'fill'; p.max_draws = p.mode === 'one' ? 1 : Math.max(2, p.max_draws ?? 2); if (p.mode === 'fill') p.quota = false })}>
      <option value="one">只抽一个</option><option value="fill">重复抽（资源用完 / 抽到「无」/ 达上限停止）</option></select></label>
    {part.mode === 'fill' && <label>上限 <input type="number" min={2} max={10} value={part.max_draws ?? 2} onChange={event => update(p => { p.max_draws = Math.min(10, Math.max(2, Number(event.target.value) || 2)) })} /></label>}
    <label className="recipe-check"><input type="checkbox" checked={Boolean(part.quota)} disabled={part.mode === 'fill'}
      onChange={event => update(p => { p.quota = event.target.checked })} /> 配额（按 N 精确分配占比；不能带条件）</label>
    <RegionPicker label="需要部位" recipe={recipe} value={part.needs ?? []} onChange={needs => update(p => { p.needs = needs })} />
    <ConditionField label="分区条件" recipe={recipe} value={part.when ?? null} onChange={when => update(p => { p.when = when })} />
    <button className="text-action danger-text" type="button" onClick={onRemove}><Trash2 size={13} aria-hidden="true" /> 删除分区</button>
    {references.length > 0 && <details className="recipe-refs"><summary>谁引用了它（{references.length}）</summary>
      <ul>{references.map((reference, index) => <li key={index}>{reference.where} 的{reference.text}
        <button className="text-action" type="button" onClick={() => history.change(draft => findReferences(draft, part.id)[index]?.remove(draft))}>删除引用</button></li>)}</ul>
      <button className="text-action" type="button" onClick={() => history.change(draft => findReferences(draft, part.id).forEach(r => r.remove(draft)))}>全部删除</button>
    </details>}
  </div>
}

function OptionRow({ history, part, option, checked, onToggle, showPartition }: {
  history: History; part: Partition; option: RecipeOption; checked: boolean; onToggle: (shift: boolean) => void; showPartition: boolean
}) {
  const { recipe } = history
  const [expanded, setExpanded] = useState(false)
  const update = (mutate: (o: RecipeOption) => void) => history.change(draft => mutate(draft.partitions.find(p => p.id === part.id)!.options.find(o => o.id === option.id)!))
  const glosses = glossOption(recipe, option)
  const total = part.options.filter(o => !o.disabled).reduce((sum, o) => sum + o.weight, 0)
  const share = option.disabled || !total ? 0 : option.weight / total
  const effects = describeEffects(recipe, option.effects)
  const condition = describeCondition(recipe, option.when)
  const references = findReferences(recipe, part.id, option.id)

  function remove() {
    if (references.length && !window.confirm(`选项被 ${references.length} 处引用：\n${references.map(r => `· ${r.where} 的${r.text}`).join('\n')}\n删除选项并同时删除这些引用？`)) return
    history.change(draft => deleteOption(draft, part.id, option.id))
  }

  return <li className={`recipe-option${option.disabled ? ' muted' : ''}${option.none ? ' none' : ''}`}>
    <input type="checkbox" checked={checked} aria-label={`选择 ${option.label || option.tags || option.id}`}
      onClick={event => { event.preventDefault(); onToggle(event.shiftKey) }} onChange={() => {}} />
    <div className="recipe-option-main">
      <div className="recipe-option-line">
        {showPartition && <span className="recipe-badge">{part.label || part.id}</span>}
        {option.none
          ? <strong className="recipe-none">无（主动跳过此分区）</strong>
          : <input className="recipe-tags" value={option.tags ?? ''} placeholder="英文 tag，可用 {color} 等属性槽" spellCheck={false} aria-label="tag"
            onChange={event => update(o => { o.tags = event.target.value })} />}
        <input className="recipe-label" value={option.label ?? ''} placeholder={glosses.map(g => g.zh ?? g.tag).join('，') || '中文名'} maxLength={100} aria-label="中文名"
          onChange={event => update(o => { o.label = event.target.value })} />
        <input className="recipe-weight" type="number" min={0.001} step="any" value={option.weight} aria-label="占比"
          onChange={event => { const value = Number(event.target.value); if (value > 0) update(o => { o.weight = value }) }} />
        <span className="recipe-share" title="本分区内的目标占比">{(share * 100).toFixed(1)}%</span>
        <button className="icon-button" type="button" title="展开规则" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? '−' : '⋯'}</button>
        <button className="icon-button danger" type="button" title="删除选项" aria-label="删除选项" onClick={remove}><Trash2 size={13} /></button>
      </div>
      <div className="recipe-option-meta">
        {!option.none && glosses.map((gloss, index) => <span key={index} className={gloss.zh === null ? 'missing' : ''}>{gloss.zh ?? `${gloss.tag}（未翻译）`}</span>)}
        {option.disabled && <b>已停用</b>}
        {condition && <span className="recipe-cond">条件：{condition}</span>}
        {effects.map(text => <span key={text} className="recipe-effect">{text}</span>)}
        {option.slots && Object.entries(option.slots).map(([slot, use]) => <span key={slot} className="recipe-effect">
          {slot}{use.exclude?.length ? ` 排除 ${use.exclude.join('、')}` : ''}{use.only?.length ? ` 只允许 ${use.only.join('、')}` : ''}{use.set_state ? ` →${use.set_state}` : ''}{use.exclude_state ? ` ≠${use.exclude_state}` : ''}</span>)}
        {references.length > 0 && <span className="recipe-ref-count">被 {references.length} 处引用</span>}
      </div>
      {expanded && <OptionDetail history={history} part={part} option={option} update={update} />}
    </div>
  </li>
}

function OptionDetail({ history, part, option, update }: { history: History; part: Partition; option: RecipeOption; update: (mutate: (o: RecipeOption) => void) => void }) {
  const { recipe } = history
  const placeholders = [...(option.tags ?? '').matchAll(/\{([a-z0-9-]+)\}/g)].map(match => match[1])
  return <div className="recipe-option-detail">
    <div className="recipe-detail-row">
      <label className="recipe-check"><input type="checkbox" checked={Boolean(option.disabled)} onChange={event => update(o => { o.disabled = event.target.checked })} /> 停用</label>
      <label className="recipe-check"><input type="checkbox" checked={Boolean(option.child)} onChange={event => update(o => {
        o.child = event.target.checked
        o.effects = { ...o.effects, set: { ...o.effects?.set, ...(event.target.checked ? { age: 'child' } : {}) } }
      })} /> 儿童（自动设置 age=child）</label>
      <label>画幅 <select value={option.size ?? ''} onChange={event => update(o => { o.size = (event.target.value || null) as RecipeOption['size'] })}>
        <option value="">自动</option><option value="portrait">竖图</option><option value="square">方图</option><option value="landscape">横图</option></select></label>
      <span className="recipe-id">id: {option.id}</span>
    </div>
    {!option.none && <RegionPicker label="需要部位" recipe={recipe} value={option.needs ?? []} onChange={needs => update(o => { o.needs = needs })} />}
    <ConditionField label="选项条件" recipe={recipe} value={option.when ?? null} onChange={when => update(o => { o.when = when })} />
    <WeightModsField recipe={recipe} option={option} update={update} />
    <EffectsEditor recipe={recipe} effects={option.effects ?? {}} ownPartition={part.id} allowStructural onChange={effects => update(o => { o.effects = effects })} />
    {placeholders.map(slotId => <SlotUseEditor key={slotId} recipe={recipe} slotId={slotId} option={option} update={update} />)}
  </div>
}

function WeightModsField({ recipe, option, update }: { recipe: Recipe; option: RecipeOption; update: (mutate: (o: RecipeOption) => void) => void }) {
  const mods = option.weight_mods ?? []
  return <div className="recipe-field-block">
    <span className="recipe-field-title">条件权重（满足条件时占比 × 系数）</span>
    {mods.map((mod, index) => <div key={index} className="recipe-detail-row">
      <span>{describeCondition(recipe, mod.when)}</span>
      <label>× <input type="number" min={0} step="any" value={mod.factor} onChange={event => update(o => { o.weight_mods![index].factor = Math.max(0, Number(event.target.value) || 0) })} /></label>
      <button className="text-action" type="button" onClick={() => update(o => { o.weight_mods = o.weight_mods!.filter((_, i) => i !== index) })}>删除</button>
    </div>)}
    <ConditionBuilder recipe={recipe} buttonLabel="添加条件权重" onAdd={when => update(o => { o.weight_mods = [...(o.weight_mods ?? []), { when, factor: 0.5 }] })} />
  </div>
}

function SlotUseEditor({ recipe, slotId, option, update }: { recipe: Recipe; slotId: string; option: RecipeOption; update: (mutate: (o: RecipeOption) => void) => void }) {
  const slot = recipe.slots?.find(item => item.id === slotId)
  if (!slot) return <p className="alert">属性槽 {`{${slotId}}`} 不存在，请在「属性槽」页新建。</p>
  const use = option.slots?.[slotId] ?? {}
  const states = stateKeys(recipe)
  const set = (mutate: (u: NonNullable<RecipeOption['slots']>[string]) => void) => update(o => {
    o.slots = { ...o.slots }
    const next = { ...(o.slots[slotId] ?? {}) }
    mutate(next)
    o.slots[slotId] = next
  })
  return <div className="recipe-field-block">
    <span className="recipe-field-title">属性槽 {slot.label || slot.id}</span>
    <div className="recipe-chips">{slot.values.map(value => {
      const state = use.exclude?.includes(value.id) ? 'exclude' : use.only?.includes(value.id) ? 'only' : ''
      return <button key={value.id} type="button" className={`recipe-chip ${state}`} title="点击切换：普通 → 只允许 → 排除"
        onClick={() => set(u => {
          const only = new Set(u.only ?? [])
          const exclude = new Set(u.exclude ?? [])
          if (!state) { only.add(value.id) } else if (state === 'only') { only.delete(value.id); exclude.add(value.id) } else exclude.delete(value.id)
          u.only = only.size ? [...only] : null
          u.exclude = [...exclude]
        })}>{state === 'exclude' ? '✕ ' : state === 'only' ? '✓ ' : ''}{value.label || value.tag}</button>
    })}</div>
    <div className="recipe-detail-row">
      <label>写入状态 <input value={use.set_state ?? ''} placeholder="如 top-color" list="recipe-states" onChange={event => set(u => { u.set_state = event.target.value.trim() || null })} /></label>
      <label>不能等于状态 <select value={use.exclude_state ?? ''} onChange={event => set(u => { u.exclude_state = event.target.value || null })}>
        <option value="">—</option>{states.map(key => <option key={key} value={key}>{recipe.states?.[key] || key}</option>)}</select></label>
    </div>
  </div>
}

function stateKeys(recipe: Recipe): string[] {
  const keys = new Set(Object.keys(recipe.states ?? {}))
  for (const part of recipe.partitions) for (const option of part.options) {
    Object.keys(option.effects?.set ?? {}).forEach(key => keys.add(key))
    Object.values(option.slots ?? {}).forEach(use => { if (use.set_state) keys.add(use.set_state) })
  }
  return [...keys]
}

function stateValues(recipe: Recipe, key: string): string[] {
  const values = new Set<string>()
  for (const part of recipe.partitions) for (const option of part.options) {
    const value = option.effects?.set?.[key]
    if (value) values.add(value)
    for (const [slotId, use] of Object.entries(option.slots ?? {})) {
      if (use.set_state === key) recipe.slots?.find(slot => slot.id === slotId)?.values.forEach(v => values.add(v.id))
    }
  }
  return [...values]
}

// ------------------------------------------------------------------ shared field editors

function RegionPicker({ label, recipe, value, onChange }: { label: string; recipe: Recipe; value: string[]; onChange: (value: string[]) => void }) {
  const regions = recipe.regions ?? DEFAULT_REGIONS
  return <div className="recipe-detail-row"><span className="recipe-field-title">{label}</span>
    <div className="recipe-chips">{regions.map(region => <button key={region.id} type="button" className={`recipe-chip ${value.includes(region.id) ? 'only' : ''}`}
      onClick={() => onChange(value.includes(region.id) ? value.filter(id => id !== region.id) : [...value, region.id])}>{region.label || region.id}</button>)}</div>
  </div>
}

function ConditionField({ label, recipe, value, onChange }: { label: string; recipe: Recipe; value: Condition | null; onChange: (value: Condition | null) => void }) {
  const clauses = value === null ? [] : 'all' in value ? value.all : [value]
  const set = (next: Condition[]) => onChange(next.length === 0 ? null : next.length === 1 ? next[0] : { all: next })
  return <div className="recipe-field-block">
    <span className="recipe-field-title">{label}（全部满足）</span>
    {clauses.map((clause, index) => <div key={index} className="recipe-detail-row">
      <span>{describeCondition(recipe, clause)}</span>
      <button className="text-action" type="button" onClick={() => set(clauses.filter((_, i) => i !== index))}>删除</button>
    </div>)}
    <ConditionBuilder recipe={recipe} buttonLabel="添加条件" onAdd={clause => set([...clauses, clause])} />
  </div>
}

type ConditionKind = 'chosen' | 'not-chosen' | 'drawn' | 'not-drawn' | 'state' | 'not-state' | 'visible' | 'hidden' | 'tag' | 'not-tag' | 'any-chosen'

/** Dropdown builder for one condition clause (nested any/not covered by the common forms). */
function ConditionBuilder({ recipe, onAdd, buttonLabel }: { recipe: Recipe; onAdd: (condition: Condition) => void; buttonLabel: string }) {
  const [kind, setKind] = useState<ConditionKind>('chosen')
  const [partition, setPartition] = useState(recipe.draw_order[0] ?? '')
  const [options, setOptions] = useState<string[]>([])
  const [state, setState] = useState(stateKeys(recipe)[0] ?? '')
  const [values, setValues] = useState<string[]>([])
  const [region, setRegion] = useState((recipe.regions ?? DEFAULT_REGIONS)[0]?.id ?? '')
  const [tag, setTag] = useState('')
  const part = recipe.partitions.find(item => item.id === partition)

  function build(): Condition | null {
    const chosen = options.map(option => ({ chosen: optionRef(partition, option) }) as Condition)
    switch (kind) {
      case 'chosen': return chosen.length === 1 ? chosen[0] : chosen.length ? { any: chosen } : null
      case 'any-chosen': return chosen.length ? { any: chosen } : null
      case 'not-chosen': return chosen.length ? { not: chosen.length === 1 ? chosen[0] : { any: chosen } } : null
      case 'drawn': return partition ? { partition_drawn: partition } : null
      case 'not-drawn': return partition ? { not: { partition_drawn: partition } } : null
      case 'state': return state && values.length ? { state, in: values } : null
      case 'not-state': return state && values.length ? { not: { state, in: values } } : null
      case 'visible': return region ? { visible: region } : null
      case 'hidden': return region ? { not: { visible: region } } : null
      case 'tag': return tag.trim() ? { tag: tag.trim() } : null
      case 'not-tag': return tag.trim() ? { not: { tag: tag.trim() } } : null
    }
  }
  const condition = build()
  return <div className="recipe-condition-builder">
    <select value={kind} aria-label="条件类型" onChange={event => setKind(event.target.value as ConditionKind)}>
      <option value="chosen">选了（任一）</option><option value="not-chosen">没选</option>
      <option value="drawn">分区有结果</option><option value="not-drawn">分区无结果</option>
      <option value="state">状态是</option><option value="not-state">状态不是</option>
      <option value="visible">部位可见</option><option value="hidden">部位不可见</option>
      <option value="tag">内容含 tag</option><option value="not-tag">内容不含 tag</option>
    </select>
    {['chosen', 'not-chosen', 'drawn', 'not-drawn', 'any-chosen'].includes(kind) && <select value={partition} aria-label="分区" onChange={event => { setPartition(event.target.value); setOptions([]) }}>
      {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>}
    {['chosen', 'not-chosen'].includes(kind) && part && <select multiple value={options} aria-label="选项" size={Math.min(6, part.options.length)}
      onChange={event => setOptions([...event.target.selectedOptions].map(item => item.value))}>
      {part.options.map(option => <option key={option.id} value={option.id}>{option.none ? '无' : option.label || option.tags || option.id}</option>)}</select>}
    {['state', 'not-state'].includes(kind) && <>
      <select value={state} aria-label="状态" onChange={event => { setState(event.target.value); setValues([]) }}>
        {stateKeys(recipe).map(key => <option key={key} value={key}>{recipe.states?.[key] || key}</option>)}</select>
      <select multiple value={values} aria-label="状态值" size={Math.min(6, Math.max(2, stateValues(recipe, state).length))} onChange={event => setValues([...event.target.selectedOptions].map(item => item.value))}>
        {stateValues(recipe, state).map(value => <option key={value} value={value}>{value}</option>)}</select>
    </>}
    {['visible', 'hidden'].includes(kind) && <select value={region} aria-label="部位" onChange={event => setRegion(event.target.value)}>
      {(recipe.regions ?? DEFAULT_REGIONS).map(item => <option key={item.id} value={item.id}>{item.label || item.id}</option>)}</select>}
    {['tag', 'not-tag'].includes(kind) && <input value={tag} placeholder="例如 smile" aria-label="tag" onChange={event => setTag(event.target.value)} />}
    <button className="text-action" type="button" disabled={!condition} onClick={() => { if (condition) onAdd(condition) }}><Plus size={13} aria-hidden="true" /> {buttonLabel}</button>
  </div>
}

function EffectsEditor({ recipe, effects, ownPartition, allowStructural, onChange }: {
  recipe: Recipe; effects: Effects; ownPartition: string | null; allowStructural: boolean; onChange: (effects: Effects) => void
}) {
  const set = (mutate: (e: Effects) => void) => { const next = clone(effects); mutate(next); onChange(next) }
  const regions = recipe.regions ?? DEFAULT_REGIONS
  const others = recipe.draw_order.filter(id => id !== ownPartition)
  const [allowPart, setAllowPart] = useState(others[0] ?? '')
  const allowTarget = recipe.partitions.find(part => part.id === allowPart)
  return <div className="recipe-field-block recipe-effects">
    <span className="recipe-field-title">效果</span>
    {allowStructural && <>
      <div className="recipe-detail-row"><span>{EFFECT_LABELS.hide}</span><div className="recipe-chips">{regions.map(region =>
        <button key={region.id} type="button" className={`recipe-chip ${effects.hide?.includes(region.id) ? 'exclude' : ''}`}
          onClick={() => set(e => { e.hide = e.hide?.includes(region.id) ? e.hide.filter(id => id !== region.id) : [...(e.hide ?? []), region.id] })}>{region.label || region.id}</button>)}</div></div>
      <KeyValueField label={EFFECT_LABELS.set} value={effects.set ?? {}} keyPlaceholder="状态 如 pose" valuePlaceholder="值 如 sitting"
        onChange={value => set(e => { e.set = value })} />
      <KeyValueField label={EFFECT_LABELS.consume} value={Object.fromEntries(Object.entries(effects.consume ?? {}).map(([k, v]) => [k, String(v)]))}
        keyPlaceholder="资源 如 hands" valuePlaceholder="数量" keys={Object.keys(recipe.resources ?? {})}
        onChange={value => set(e => { e.consume = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, Math.max(1, Number(v) || 1)])) })} />
    </>}
    <div className="recipe-detail-row"><span>{EFFECT_LABELS.remove_partitions}</span><div className="recipe-chips">{others.map(id =>
      <button key={id} type="button" className={`recipe-chip ${effects.remove_partitions?.includes(id) ? 'exclude' : ''}`}
        onClick={() => set(e => { e.remove_partitions = e.remove_partitions?.includes(id) ? e.remove_partitions.filter(item => item !== id) : [...(e.remove_partitions ?? []), id] })}>
        {recipe.partitions.find(p => p.id === id)?.label || id}</button>)}</div></div>
    <div className="recipe-detail-row"><span>{EFFECT_LABELS.allow_options}</span>
      <select value={allowPart} aria-label="限定的分区" onChange={event => setAllowPart(event.target.value)}>
        {others.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
      {allowTarget && <div className="recipe-chips">{allowTarget.options.map(option => {
        const listed = effects.allow_options?.[allowPart]?.includes(option.id)
        return <button key={option.id} type="button" className={`recipe-chip ${listed ? 'only' : ''}`} onClick={() => set(e => {
          const map = { ...(e.allow_options ?? {}) }
          const current = map[allowPart] ?? []
          const next = listed ? current.filter(id => id !== option.id) : [...current, option.id]
          if (next.length) map[allowPart] = next
          else delete map[allowPart]
          e.allow_options = map
        })}>{option.none ? '无' : option.label || option.tags || option.id}</button>
      })}</div>}
    </div>
    <div className="recipe-detail-row"><span>{EFFECT_LABELS.remove_options}</span>
      <TagListField value={effects.remove_options ?? []} placeholder="分区ID.选项ID，回车添加" onChange={value => set(e => { e.remove_options = value })} /></div>
    {(['content_add', 'remove_tags', 'style_add', 'style_remove'] as const).map(key => <div key={key} className="recipe-detail-row"><span>{EFFECT_LABELS[key]}</span>
      <TagListField value={effects[key] ?? []} placeholder="tag，回车添加" onChange={value => set(e => { e[key] = value })} /></div>)}
  </div>
}

function KeyValueField({ label, value, keyPlaceholder, valuePlaceholder, onChange, keys }: {
  label: string; value: Record<string, string>; keyPlaceholder: string; valuePlaceholder: string; onChange: (value: Record<string, string>) => void; keys?: string[]
}) {
  const [key, setKey] = useState('')
  const [val, setVal] = useState('')
  const valid = /^[a-z0-9][a-z0-9-]*$/
  return <div className="recipe-detail-row"><span>{label}</span>
    <div className="recipe-chips">{Object.entries(value).map(([k, v]) => <button key={k} type="button" className="recipe-chip only" title="点击删除"
      onClick={() => { const next = { ...value }; delete next[k]; onChange(next) }}>{k}={v} ✕</button>)}</div>
    {keys ? <select value={key} onChange={event => setKey(event.target.value)} aria-label={keyPlaceholder}><option value="">{keyPlaceholder}</option>{keys.map(k => <option key={k}>{k}</option>)}</select>
      : <input value={key} placeholder={keyPlaceholder} list="recipe-states" onChange={event => setKey(event.target.value.trim())} />}
    <input value={val} placeholder={valuePlaceholder} onChange={event => setVal(event.target.value.trim())} />
    <button className="text-action" type="button" disabled={!valid.test(key) || !val || (!keys && !valid.test(val))}
      onClick={() => { onChange({ ...value, [key]: val }); setKey(''); setVal('') }}><Plus size={12} aria-hidden="true" /></button>
  </div>
}

function TagListField({ value, placeholder, onChange }: { value: string[]; placeholder: string; onChange: (value: string[]) => void }) {
  const [text, setText] = useState('')
  const add = () => {
    const tags = splitTags(text).filter(tag => !value.includes(tag))
    if (tags.length) onChange([...value, ...tags])
    setText('')
  }
  return <div className="recipe-taglist">
    {value.map(tag => <button key={tag} type="button" className="recipe-chip only" title="点击删除" onClick={() => onChange(value.filter(item => item !== tag))}>{tag} ✕</button>)}
    <input value={text} placeholder={placeholder} spellCheck={false} onChange={event => setText(event.target.value)}
      onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); add() } }} onBlur={add} />
  </div>
}

// ------------------------------------------------------------------ bulk editing

function BulkPanel({ history, targets, onDone }: { history: History; targets: BulkTarget[]; onDone: () => void }) {
  const { recipe } = history
  const [kind, setKind] = useState<'effect' | 'allow' | 'condition' | 'weight' | 'move' | 'state'>('effect')
  const [effect, setEffect] = useState<ListEffect>('remove_tags')
  const [value, setValue] = useState('')
  const [partition, setPartition] = useState(recipe.draw_order[0] ?? '')
  const [allowed, setAllowed] = useState<string[]>([])
  const [weightMode, setWeightMode] = useState<'set' | 'multiply' | 'normalize'>('set')
  const [weight, setWeight] = useState('1')
  const [result, setResult] = useState('')
  const options = targetOptions(recipe, targets)
  const part = recipe.partitions.find(item => item.id === partition)

  function preview(mode: 'add' | 'remove'): string {
    const copy = clone(recipe)
    const opts = targetOptions(copy, targets)
    if (kind === 'effect') { const [c, s] = bulkListEffect(opts, effect, value, mode); return `${c} 个选项将${mode === 'add' ? '新增' : '删除'} ${EFFECT_LABELS[effect]}：${value}；${s} 个跳过` }
    if (kind === 'allow') { const [c, s] = bulkAllowOptions(opts, partition, allowed, mode); return `${c} 个选项将${mode === 'add' ? '设置' : '删除'}「只允许 ${part?.label}」；${s} 个跳过` }
    return ''
  }

  function apply(mode: 'add' | 'remove') {
    const text = preview(mode)
    if (text && !window.confirm(`${text}\n确定执行？（可撤销）`)) return
    history.change(draft => {
      const opts = targetOptions(draft, targets)
      if (kind === 'effect') bulkListEffect(opts, effect, value, mode)
      else if (kind === 'allow') bulkAllowOptions(opts, partition, allowed, mode)
    })
    setResult(text)
  }

  return <div className="recipe-bulk" role="region" aria-label="批量编辑">
    <strong>已选 {options.length} 个选项</strong>
    <select value={kind} aria-label="批量操作" onChange={event => setKind(event.target.value as typeof kind)}>
      <option value="effect">增删效果（tag / 画风 / 隐藏 / 移除）</option>
      <option value="allow">只允许选项</option>
      <option value="condition">增删条件</option>
      <option value="weight">调整占比</option>
      <option value="move">移动 / 复制 / 删除 / 停用</option>
    </select>
    {kind === 'effect' && <>
      <select value={effect} aria-label="效果" onChange={event => setEffect(event.target.value as ListEffect)}>
        {LIST_EFFECTS.map(key => <option key={key} value={key}>{EFFECT_LABELS[key]}</option>)}</select>
      {effect === 'hide' ? <select value={value} aria-label="部位" onChange={event => setValue(event.target.value)}><option value="">选择部位</option>
        {(recipe.regions ?? DEFAULT_REGIONS).map(region => <option key={region.id} value={region.id}>{region.label || region.id}</option>)}</select>
        : effect === 'remove_partitions' ? <select value={value} aria-label="分区" onChange={event => setValue(event.target.value)}><option value="">选择分区</option>
          {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
          : <input value={value} placeholder={effect === 'remove_options' ? '分区ID.选项ID' : 'tag'} spellCheck={false} onChange={event => setValue(event.target.value)} />}
      <button className="secondary" type="button" disabled={!value.trim()} onClick={() => apply('add')}>批量添加</button>
      <button className="text-action" type="button" disabled={!value.trim()} onClick={() => apply('remove')}>批量删除</button>
    </>}
    {kind === 'allow' && <>
      <select value={partition} aria-label="分区" onChange={event => { setPartition(event.target.value); setAllowed([]) }}>
        {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
      {part && <select multiple value={allowed} size={Math.min(6, part.options.length)} aria-label="允许的选项" onChange={event => setAllowed([...event.target.selectedOptions].map(item => item.value))}>
        {part.options.map(option => <option key={option.id} value={option.id}>{option.none ? '无' : option.label || option.tags}</option>)}</select>}
      <button className="secondary" type="button" disabled={!allowed.length} onClick={() => apply('add')}>批量设置</button>
      <button className="text-action" type="button" onClick={() => apply('remove')}>批量取消</button>
    </>}
    {kind === 'condition' && <ConditionBuilder recipe={recipe} buttonLabel="批量添加（且）" onAdd={clause => {
      history.change(draft => { const [c, s] = bulkCondition(targetOptions(draft, targets), clause, 'add'); setResult(`${c} 个选项已添加条件，${s} 个已存在`) })
    }} />}
    {kind === 'condition' && <ConditionBuilder recipe={recipe} buttonLabel="批量删除这条条件" onAdd={clause => {
      history.change(draft => { const [c, s] = bulkCondition(targetOptions(draft, targets), clause, 'remove'); setResult(`${c} 个选项已删除条件，${s} 个没有`) })
    }} />}
    {kind === 'weight' && <>
      <select value={weightMode} aria-label="方式" onChange={event => setWeightMode(event.target.value as typeof weightMode)}>
        <option value="set">设为</option><option value="multiply">乘以</option><option value="normalize">归一化到总和</option></select>
      <input type="number" min={0.001} step="any" value={weight} onChange={event => setWeight(event.target.value)} />
      <button className="secondary" type="button" disabled={!(Number(weight) > 0)} onClick={() => history.change(draft => bulkWeight(targetOptions(draft, targets), weightMode, Number(weight)))}>应用</button>
    </>}
    {kind === 'move' && <>
      <select value={partition} aria-label="目标分区" onChange={event => setPartition(event.target.value)}>
        {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
      <button className="secondary" type="button" onClick={() => { history.change(draft => setResult(`已移动 ${moveOrCopy(draft, targets, partition, false)} 个`)); onDone() }}>移动到</button>
      <button className="text-action" type="button" onClick={() => history.change(draft => setResult(`已复制 ${moveOrCopy(draft, targets, partition, true)} 个`))}>复制到</button>
      <button className="text-action" type="button" onClick={() => history.change(draft => targetOptions(draft, targets).forEach(o => { o.disabled = true }))}>停用</button>
      <button className="text-action" type="button" onClick={() => history.change(draft => targetOptions(draft, targets).forEach(o => { o.disabled = false }))}>启用</button>
      <button className="text-action danger-text" type="button" onClick={() => {
        const refs = targets.reduce((sum, t) => sum + findReferences(recipe, t.partition, t.option).length, 0)
        if (!window.confirm(`删除 ${targets.length} 个选项${refs ? `，同时删除 ${refs} 处引用` : ''}？（可撤销）`)) return
        history.change(draft => targets.forEach(t => deleteOption(draft, t.partition, t.option)))
        onDone()
      }}>删除</button>
    </>}
    {result && <span className="subtle">{result}</span>}
  </div>
}

// ------------------------------------------------------------------ other tabs

function OrderList({ title, order, recipe, onChange }: { title: string; order: string[]; recipe: Recipe; onChange: (order: string[]) => void }) {
  const [dragging, setDragging] = useState<number | null>(null)
  const move = (from: number, to: number) => {
    if (to < 0 || to >= order.length) return
    const next = [...order]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    onChange(next)
  }
  return <section className="recipe-order"><h4>{title}</h4><ol>{order.map((id, index) =>
    <li key={id} draggable onDragStart={() => setDragging(index)} onDragOver={event => event.preventDefault()}
      onDrop={() => { if (dragging !== null) move(dragging, index); setDragging(null) }}>
      <span>{recipe.partitions.find(p => p.id === id)?.label || id}</span>
      <button className="icon-button" type="button" aria-label="上移" disabled={index === 0} onClick={() => move(index, index - 1)}><ArrowUp size={13} /></button>
      <button className="icon-button" type="button" aria-label="下移" disabled={index === order.length - 1} onClick={() => move(index, index + 1)}><ArrowDown size={13} /></button>
    </li>)}</ol></section>
}

function OrderTab({ history }: { history: History }) {
  const { recipe } = history
  const prompt = recipe.prompt_order?.length ? recipe.prompt_order : recipe.draw_order
  return <div>
    <p className="prompt-hint">抽取顺序决定谁影响谁：隐藏部位、移除、只允许都要排在被影响的分区前面；抽取时的条件只能引用排在前面的分区。输出顺序只决定提示词里的排列。可拖动或用箭头调整。</p>
    <div className="recipe-orders">
      <OrderList title="抽取顺序" order={recipe.draw_order} recipe={recipe} onChange={order => history.change(draft => { draft.draw_order = order })} />
      <OrderList title="输出顺序" order={prompt} recipe={recipe} onChange={order => history.change(draft => { draft.prompt_order = order })} />
    </div>
    <button className="text-action" type="button" onClick={() => history.change(draft => { draft.prompt_order = [...draft.draw_order] })}>输出顺序与抽取顺序一致</button>
  </div>
}

function RulesTab({ history }: { history: History }) {
  const { recipe } = history
  const rules = recipe.rules ?? []
  const update = (id: string, mutate: (rule: Rule) => void) => history.change(draft => mutate(draft.rules!.find(rule => rule.id === id)!))
  return <div className="recipe-rules">
    <p className="prompt-hint">规则在全部分区抽完后按顺序执行，条件可以引用任何分区。规则不能隐藏部位、设置状态或占用资源。「加画风 tag」只发给模型、不进 caption，LoRA 会把它吸收为默认画法（例如 smile → gentle smile）。</p>
    {rules.map((rule, index) => <details key={rule.id} className={`recipe-rule${rule.disabled ? ' muted' : ''}`}>
      <summary>
        <input value={rule.label ?? ''} placeholder="规则名称" maxLength={100} onClick={event => event.stopPropagation()} onChange={event => update(rule.id, r => { r.label = event.target.value })} />
        <span className="subtle">当 {describeCondition(recipe, rule.when) || '（无条件）'} → {describeEffects(recipe, rule.effects).join('；') || '（无效果）'}</span>
      </summary>
      <div className="recipe-detail-row">
        <label className="recipe-check"><input type="checkbox" checked={Boolean(rule.disabled)} onChange={event => update(rule.id, r => { r.disabled = event.target.checked })} /> 停用</label>
        <button className="icon-button" type="button" aria-label="上移" disabled={index === 0} onClick={() => history.change(draft => { const r = draft.rules!; [r[index - 1], r[index]] = [r[index], r[index - 1]] })}><ArrowUp size={13} /></button>
        <button className="icon-button" type="button" aria-label="下移" disabled={index === rules.length - 1} onClick={() => history.change(draft => { const r = draft.rules!; [r[index + 1], r[index]] = [r[index], r[index + 1]] })}><ArrowDown size={13} /></button>
        <button className="text-action danger-text" type="button" onClick={() => history.change(draft => { draft.rules = draft.rules!.filter(r => r.id !== rule.id) })}>删除规则</button>
        <span className="recipe-id">id: {rule.id}</span>
      </div>
      <ConditionField label="条件" recipe={recipe} value={rule.when} onChange={when => update(rule.id, r => { r.when = when ?? { tag: 'never-matches' } })} />
      <EffectsEditor recipe={recipe} effects={rule.effects} ownPartition={null} allowStructural={false} onChange={effects => update(rule.id, r => { r.effects = effects })} />
    </details>)}
    <button className="text-action" type="button" onClick={() => history.change(draft => {
      draft.rules = [...(draft.rules ?? []), { id: newId('rule', (draft.rules ?? []).map(r => r.id)), label: '新规则', when: { tag: 'smile' }, effects: {} }]
    })}><Plus size={13} aria-hidden="true" /> 新建规则</button>
  </div>
}

function SlotsTab({ history }: { history: History }) {
  const { recipe } = history
  return <div className="recipe-slots">
    <p className="prompt-hint">属性槽是共享的取值列表（如颜色）。在选项 tag 里写 {'{color} china dress'}，每次抽中时从槽里抽一个值填进去，得到一个完整的 tag（如 red china dress）。每个选项可在「⋯」里排除或只允许某些值。</p>
    {(recipe.slots ?? []).map(slot => <section key={slot.id} className="recipe-slot">
      <div className="recipe-detail-row">
        <label>名称 <input value={slot.label ?? ''} onChange={event => history.change(draft => { draft.slots!.find(s => s.id === slot.id)!.label = event.target.value })} /></label>
        <span className="recipe-id">在 tag 中写：{`{${slot.id}}`}</span>
        <button className="text-action danger-text" type="button" onClick={() => history.change(draft => { draft.slots = draft.slots!.filter(s => s.id !== slot.id) })}>删除槽</button>
      </div>
      <table className="recipe-table"><thead><tr><th>英文</th><th>中文</th><th>占比</th><th /></tr></thead><tbody>
        {slot.values.map(value => <tr key={value.id}>
          <td><input value={value.tag} spellCheck={false} onChange={event => history.change(draft => { draft.slots!.find(s => s.id === slot.id)!.values.find(v => v.id === value.id)!.tag = event.target.value })} /></td>
          <td><input value={value.label ?? ''} placeholder={glossTag(recipe, value.tag) ?? ''} onChange={event => history.change(draft => { draft.slots!.find(s => s.id === slot.id)!.values.find(v => v.id === value.id)!.label = event.target.value })} /></td>
          <td><input type="number" min={0.001} step="any" value={value.weight} onChange={event => { const w = Number(event.target.value); if (w > 0) history.change(draft => { draft.slots!.find(s => s.id === slot.id)!.values.find(v => v.id === value.id)!.weight = w }) }} /></td>
          <td><button className="icon-button danger" type="button" aria-label="删除取值" disabled={slot.values.length <= 1}
            onClick={() => history.change(draft => { const s = draft.slots!.find(item => item.id === slot.id)!; s.values = s.values.filter(v => v.id !== value.id) })}><Trash2 size={13} /></button></td>
        </tr>)}
      </tbody></table>
      <button className="text-action" type="button" onClick={() => history.change(draft => { const s = draft.slots!.find(item => item.id === slot.id)!; s.values.push({ id: newId('value', s.values.map(v => v.id)), tag: 'new', label: '', weight: 1 }) })}>
        <Plus size={13} aria-hidden="true" /> 新增取值</button>
    </section>)}
    <button className="text-action" type="button" onClick={() => {
      const id = window.prompt('槽的 ID（英文小写，用于在 tag 里写 {id}，之后不能改）', 'color')?.trim()
      if (!id || !/^[a-z0-9][a-z0-9-]*$/.test(id) || recipe.slots?.some(s => s.id === id)) return
      history.change(draft => { draft.slots = [...(draft.slots ?? []), { id, label: id, values: [{ id: 'v-white', tag: 'white', label: '白色', weight: 1 }] }] })
    }}><Plus size={13} aria-hidden="true" /> 新建属性槽</button>
  </div>
}

function RegionsTab({ history }: { history: History }) {
  const { recipe } = history
  const regions = recipe.regions ?? DEFAULT_REGIONS
  return <div className="recipe-regions">
    <h4>部位（上级被隐藏时下级一起隐藏）</h4>
    <table className="recipe-table"><thead><tr><th>ID</th><th>名称</th><th>上级</th><th /></tr></thead><tbody>
      {regions.map(region => <tr key={region.id}>
        <td className="recipe-id">{region.id}</td>
        <td><input value={region.label ?? ''} onChange={event => history.change(draft => { (draft.regions ??= clone(DEFAULT_REGIONS)).find(r => r.id === region.id)!.label = event.target.value })} /></td>
        <td><select value={region.parent ?? ''} onChange={event => history.change(draft => { (draft.regions ??= clone(DEFAULT_REGIONS)).find(r => r.id === region.id)!.parent = event.target.value || null })}>
          <option value="">（无）</option>{regions.filter(r => r.id !== region.id).map(r => <option key={r.id} value={r.id}>{r.label || r.id}</option>)}</select></td>
        <td><button className="icon-button danger" type="button" aria-label="删除部位" onClick={() => history.change(draft => { draft.regions = (draft.regions ?? clone(DEFAULT_REGIONS)).filter(r => r.id !== region.id) })}><Trash2 size={13} /></button></td>
      </tr>)}
    </tbody></table>
    <button className="text-action" type="button" onClick={() => {
      const label = window.prompt('新部位名称，例如 尾巴', '')
      if (!label) return
      history.change(draft => { draft.regions = [...(draft.regions ?? clone(DEFAULT_REGIONS)), { id: newId('region', (draft.regions ?? []).map(r => r.id)), label, parent: 'person' }] })
    }}><Plus size={13} aria-hidden="true" /> 新增部位</button>
    <h4>资源（容量）</h4>
    <KeyValueField label="" value={Object.fromEntries(Object.entries(recipe.resources ?? {}).map(([k, v]) => [k, String(v)]))} keyPlaceholder="资源 ID 如 hands" valuePlaceholder="容量"
      onChange={value => history.change(draft => { draft.resources = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, Math.max(1, Math.min(100, Number(v) || 1))])) })} />
    <h4>状态名称（只用于显示）</h4>
    <KeyValueField label="" value={recipe.states ?? {}} keyPlaceholder="状态 ID 如 pose" valuePlaceholder="中文名 如 姿势"
      onChange={value => history.change(draft => { draft.states = value })} keys={stateKeys(recipe)} />
    <h4>画风 tag 绑定部位（部位看不到时，从这一条的画风里删掉）</h4>
    {(recipe.style_tags ?? []).map((binding, index) => <div key={index} className="recipe-detail-row">
      <code>{binding.tag}</code><span>需要</span>
      <select value={binding.needs} onChange={event => history.change(draft => { draft.style_tags![index].needs = event.target.value })}>
        {regions.map(r => <option key={r.id} value={r.id}>{r.label || r.id}</option>)}</select>
      <button className="text-action" type="button" onClick={() => history.change(draft => { draft.style_tags = draft.style_tags!.filter((_, i) => i !== index) })}>删除</button>
    </div>)}
    <TagListField value={[]} placeholder="输入画风 tag，回车添加（默认绑定眼睛）" onChange={tags => history.change(draft => {
      draft.style_tags = [...(draft.style_tags ?? []), ...tags.map(tag => ({ tag, needs: 'eyes' }))]
    })} />
    <datalist id="recipe-states">{stateKeys(recipe).map(key => <option key={key} value={key} />)}</datalist>
  </div>
}

function GlossaryTab({ history, api }: { history: History; api: WorkspaceApi }) {
  const { recipe } = history
  const missing = missingGlosses(recipe)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResults | null>(null)
  const [target, setTarget] = useState<string | null>(null)
  const [batch, setBatch] = useState<Array<{ tag: string; zh: string; accept: boolean }>>([])
  const [running, setRunning] = useState<AbortController | null>(null)
  const [status, setStatus] = useState('')
  const setGloss = (tag: string, zh: string) => history.change(draft => { draft.glossary = { ...(draft.glossary ?? {}), [tag.toLowerCase()]: zh } })

  async function search(text: string, forTag: string | null) {
    setTarget(forTag)
    setQuery(text)
    setStatus('')
    try { setResults(await api.search(text)) } catch (failure) { setStatus(errorText(failure)) }
  }

  async function lookupAll() {
    const controller = new AbortController()
    setRunning(controller)
    setBatch([])
    const found: Array<{ tag: string; zh: string; accept: boolean }> = []
    try {
      for (const tag of missing) {
        if (controller.signal.aborted) break
        setStatus(`正在查找 ${found.length + 1} / ${missing.length}：${tag}`)
        const response = await api.search(tag, controller.signal)
        const exact = response.results.find(item => item.tag.toLowerCase().replace(/_/g, ' ') === tag.toLowerCase()) ?? response.results[0]
        if (exact?.cn_name) found.push({ tag, zh: exact.cn_name, accept: exact.tag.toLowerCase().replace(/_/g, ' ') === tag.toLowerCase() })
        setBatch([...found])
      }
      setStatus(`查找完成：${found.length} / ${missing.length} 个有候选，确认后写入。`)
    } catch (failure) {
      if (failure instanceof ApiFailure && failure.status === 429) setStatus(`搜索过于频繁，已停止${failure.retryAfterSeconds !== null ? `，请 ${failure.retryAfterSeconds} 秒后再试` : ''}。已找到的可先确认。`)
      else if ((failure as Error)?.name !== 'AbortError') setStatus(errorText(failure))
      else setStatus('已取消。')
    } finally { setRunning(null) }
  }

  return <div className="recipe-glossary">
    <p className="prompt-hint">释义只用于显示，不会发给模型，也不进 caption。查找顺序：选项中文名 → 配方词典 → 内置词典；都没有时标为未翻译。</p>
    <div className="recipe-toolbar">
      <input value={query} placeholder="搜索 Danbooru 标签（可输入中文）" onChange={event => setQuery(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter' && query.trim()) void search(query.trim(), null) }} />
      <button className="secondary" type="button" disabled={!query.trim()} onClick={() => void search(query.trim(), null)}><Search size={13} aria-hidden="true" /> 搜索</button>
      <button className="secondary" type="button" disabled={!missing.length || Boolean(running)} onClick={() => void lookupAll()}><Languages size={13} aria-hidden="true" /> 查找全部未翻译（{missing.length}）</button>
      {running && <button className="text-action" type="button" onClick={() => running.abort()}>取消</button>}
    </div>
    {status && <p className="subtle" role="status">{status}</p>}
    {results && <ul className="recipe-search-results">{results.results.map(item => <li key={item.tag}>
      <code>{item.tag}</code> {item.cn_name ?? '—'} <span className="subtle">{item.category ?? ''} {item.count ?? ''}{item.is_nsfw ? ' NSFW' : ''}</span>
      {target && item.cn_name && <button className="text-action" type="button" onClick={() => { setGloss(target, item.cn_name!); setResults(null) }}>用作「{target}」的释义</button>}
    </li>)}{results.source_url && <li className="subtle">来源：<a href={results.source_url} target="_blank" rel="noreferrer">{results.source_url}</a></li>}</ul>}
    {batch.length > 0 && <div className="recipe-batch">
      <table className="recipe-table"><thead><tr><th /><th>tag</th><th>释义候选</th></tr></thead><tbody>
        {batch.map((row, index) => <tr key={row.tag}><td><input type="checkbox" checked={row.accept} onChange={event => setBatch(current => current.map((r, i) => i === index ? { ...r, accept: event.target.checked } : r))} /></td>
          <td><code>{row.tag}</code></td><td><input value={row.zh} onChange={event => setBatch(current => current.map((r, i) => i === index ? { ...r, zh: event.target.value } : r))} /></td></tr>)}
      </tbody></table>
      <button className="secondary" type="button" onClick={() => { history.change(draft => { draft.glossary = { ...(draft.glossary ?? {}), ...Object.fromEntries(batch.filter(r => r.accept && r.zh.trim()).map(r => [r.tag.toLowerCase(), r.zh.trim()])) } }); setBatch([]) }}>写入勾选的释义</button>
    </div>}
    <h4>未翻译（{missing.length}）</h4>
    <ul className="recipe-missing">{missing.map(tag => <MissingRow key={tag} tag={tag} onSave={zh => setGloss(tag, zh)} onSearch={() => void search(tag, tag)} />)}</ul>
    <h4>配方词典（{Object.keys(recipe.glossary ?? {}).length}）</h4>
    <ul className="recipe-missing">{Object.entries(recipe.glossary ?? {}).map(([tag, zh]) => <li key={tag}><code>{tag}</code> {zh}
      <button className="text-action" type="button" onClick={() => history.change(draft => { const g = { ...(draft.glossary ?? {}) }; delete g[tag]; draft.glossary = g })}>删除</button></li>)}</ul>
  </div>
}

function MissingRow({ tag, onSave, onSearch }: { tag: string; onSave: (zh: string) => void; onSearch: () => void }) {
  const [text, setText] = useState('')
  return <li><code>{tag}</code>
    <input value={text} placeholder="手动输入释义" maxLength={100} onChange={event => setText(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && text.trim()) onSave(text.trim()) }} />
    <button className="text-action" type="button" disabled={!text.trim()} onClick={() => onSave(text.trim())}>保存</button>
    <button className="text-action" type="button" onClick={onSearch}><Search size={12} aria-hidden="true" /> 查找</button>
  </li>
}

function JsonTab({ history, name, setName }: { history: History; name: string; setName: (name: string) => void }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const file = useRef<HTMLInputElement>(null)

  function exportJson() {
    const blob = new Blob([JSON.stringify({ name, recipe: history.recipe }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = Object.assign(document.createElement('a'), { href: url, download: `${name || 'recipe'}.recipe.json` })
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  function importJson(raw: string) {
    try {
      const parsed = JSON.parse(raw) as { name?: string; recipe?: Recipe } | Recipe
      const recipe = 'recipe' in parsed && parsed.recipe ? parsed.recipe : parsed as Recipe
      if (!Array.isArray(recipe.partitions) || !Array.isArray(recipe.draw_order)) throw new Error('不是配方 JSON：缺少 partitions 或 draw_order。')
      history.change(draft => { Object.keys(draft).forEach(key => delete (draft as unknown as Record<string, unknown>)[key]); Object.assign(draft, recipe) })
      if ('name' in parsed && typeof parsed.name === 'string') setName(parsed.name)
      setError('')
      setText('')
    } catch (failure) { setError(failure instanceof Error ? failure.message : '无法解析 JSON。') }
  }

  return <div className="recipe-json">
    <p className="prompt-hint">导入整个配方会保留原有 ID（可撤销），保存时由服务器完整校验。导出的文件可备份或在其他账号导入。</p>
    <div className="recipe-toolbar">
      <button className="secondary" type="button" onClick={exportJson}><Download size={13} aria-hidden="true" /> 导出 JSON</button>
      <input ref={file} type="file" accept=".json,application/json" hidden onChange={async event => { const f = event.target.files?.[0]; if (f) importJson(await f.text()); event.target.value = '' }} />
      <button className="secondary" type="button" onClick={() => file.current?.click()}><FileUp size={13} aria-hidden="true" /> 从文件导入</button>
    </div>
    <textarea rows={12} value={text} spellCheck={false} placeholder="或粘贴配方 JSON" onChange={event => setText(event.target.value)} />
    <button className="text-action" type="button" disabled={!text.trim()} onClick={() => importJson(text)}>导入粘贴的 JSON（替换当前配方）</button>
    {error && <p className="alert" role="alert">{error}</p>}
  </div>
}

// ------------------------------------------------------------------ sampling

function SamplePanel({ api, recipe, style, recipeRef, saved, onGenerate }: {
  api: WorkspaceApi; recipe: Recipe; style: string; recipeRef: { id: string; name: string }; saved: boolean; onGenerate: (result: RecipeDraftResult) => void
}) {
  const [n, setN] = useState('100')
  const [seed, setSeed] = useState(() => String(Math.floor(Math.random() * 4294967295)))
  const [result, setResult] = useState<SampleResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const count = Number(n)
  const seedValue = Number(seed)
  const valid = Number.isInteger(count) && count >= 1 && count <= MAX_DATASET_ITEMS && Number.isInteger(seedValue) && seedValue >= 0 && seedValue <= 4294967295

  async function run(size: number): Promise<SampleResult | null> {
    setError('')
    setBusy(true)
    try {
      const sampled = await api.sampleRecipe(recipe, size, seedValue)
      setResult(sampled)
      return sampled
    } catch (failure) {
      setError(errorText(failure))
      return null
    } finally { setBusy(false) }
  }

  async function generate(replace: boolean) {
    const sampled = await run(count)
    if (sampled) onGenerate({ items: sampled.items, recipe: recipeRef, replace })
  }

  return <aside className="recipe-sample" aria-label="预览与生成">
    <h4><Dices size={14} aria-hidden="true" /> 预览与生成</h4>
    <div className="recipe-detail-row">
      <label>条数 N <input type="number" min={1} max={MAX_DATASET_ITEMS} value={n} onChange={event => setN(event.target.value)} /></label>
      <label>种子 <input type="number" min={0} max={4294967295} value={seed} onChange={event => setSeed(event.target.value)} /></label>
      <button className="icon-button" type="button" title="随机种子" aria-label="随机种子" onClick={() => setSeed(String(Math.floor(Math.random() * 4294967295)))}><Dices size={14} /></button>
    </div>
    <div className="recipe-detail-row">
      <button className="secondary" type="button" disabled={busy || !valid} onClick={() => void run(Math.min(count, 20))}>预览 {Math.min(count || 20, 20)} 条</button>
      <button className="primary" type="button" disabled={busy || !valid} onClick={() => void generate(false)}>生成 {valid ? count : ''} 条：追加到列表</button>
      <button className="text-action" type="button" disabled={busy || !valid} onClick={() => { if (window.confirm('替换整个训练集列表？')) void generate(true) }}>替换列表</button>
    </div>
    {!saved && <p className="prompt-hint">配方未保存也能预览和生成；结果会记下配方名称，建议先保存方便以后对照。</p>}
    <p className="prompt-hint">同一配方 + 种子 + 条数总能得到同样的结果。预览不调用 NovelAI，不花费 Anlas。</p>
    {error && <p className="alert" role="alert">{error}</p>}
    {result && <SampleView recipe={recipe} result={result} style={style} />}
  </aside>
}

function SampleView({ recipe, result, style }: { recipe: Recipe; result: SampleResult; style: string }) {
  const { stats } = result
  return <div className="recipe-sample-view">
    <p className="subtle">已生成 {stats.produced} / {stats.requested} 条{stats.overflow ? `，${stats.overflow} 条超过 1000 字符被丢弃` : ''}
      {stats.stale_dependency ? `，${stats.stale_dependency} 条依赖已失效（建议调整抽取顺序）` : ''}。</p>
    {stats.warnings.length > 0 && <details className="recipe-warnings" open><summary>顺序提示（{stats.warnings.length}）</summary><ul>{stats.warnings.map(text => <li key={text}>{text}</li>)}</ul></details>}
    <details open><summary>条目（{result.items.length}）</summary>
      <ol className="recipe-preview-items">{result.items.slice(0, 50).map(item => <li key={item.id}>
        <code>{item.prompt}</code>
        {(item.style_edits.add.length > 0 || item.style_edits.remove.length > 0) && <div className="recipe-style-edit">
          画风：{item.style_edits.add.map(tag => <b key={`a${tag}`} className="add">+{tag}</b>)}{item.style_edits.remove.map(tag => <b key={`r${tag}`} className="remove">−{tag}</b>)}
          <span className="subtle"> → {previewStyle(style, item.style_edits) || '（空）'}</span>
        </div>}
        <div className="recipe-option-meta">{item.draws.filter(draw => draw.option.startsWith('-') || draw.partition.startsWith('-')).map((draw, index) => <span key={index}>{draw.label}</span>)}</div>
      </li>)}</ol>
    </details>
    <details><summary>占比统计（目标 vs 实际）</summary>
      {stats.partitions.map(part => {
        const total = part.options.reduce((sum, option) => sum + option.count, 0)
        return <table key={part.partition} className="recipe-table recipe-stats"><caption>{part.label || part.partition}
          {Object.entries(part.skips).map(([reason, value]) => <span key={reason} className="subtle"> 跳过（{SKIP_REASONS[reason] ?? reason}）{value}</span>)}</caption>
          <tbody>{part.options.map(option => {
            const actual = total ? option.count / total : 0
            const off = total > 0 && Math.abs(actual - option.target) > 0.05
            return <tr key={option.option} className={off ? 'off' : ''}><td>{option.label}</td><td>{(option.target * 100).toFixed(1)}%</td><td>{(actual * 100).toFixed(1)}%</td><td>{option.count}</td></tr>
          })}
          {Object.entries(part.values).map(([slot, values]) => <tr key={slot}><td colSpan={4} className="subtle">{slot}：{Object.entries(values).map(([value, c]) => `${recipe.slots?.find(s => s.id === slot)?.values.find(v => v.id === value)?.label || value} ${c}`).join('、')}</td></tr>)}
          </tbody></table>
      })}
      {Object.keys(stats.rules).length > 0 && <p className="subtle">规则命中：{Object.entries(stats.rules).map(([id, c]) => `${recipe.rules?.find(r => r.id === id)?.label || id} ${c}`).join('、')}</p>}
      {Object.keys(stats.style_removed).length > 0 && <p className="subtle">画风删除：{Object.entries(stats.style_removed).map(([tag, c]) => `${tag} ${c}`).join('、')}</p>}
      {Object.keys(stats.style_added).length > 0 && <p className="subtle">画风追加：{Object.entries(stats.style_added).map(([tag, c]) => `${tag} ${c}`).join('、')}</p>}
    </details>
  </div>
}

export function RecipeHint({ children }: { children: ReactNode }) {
  return <p className="prompt-hint">{children}</p>
}
