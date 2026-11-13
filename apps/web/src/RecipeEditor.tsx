import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { ArrowDown, ArrowUp, ChevronDown, ChevronRight, Copy, Dices, Download, FileUp, Languages, ListChecks, MoreHorizontal, Plus, Redo2, Save, Search, Settings2, Shuffle, Trash2, Undo2, X } from 'lucide-react'
import { ApiFailure, errorText, type SearchResults, type WorkspaceApi } from './api'
import {
  DEFAULT_REGIONS, EFFECT_LABELS, LIST_EFFECTS, SKIP_REASONS, bulkAllowOptions, bulkCondition, bulkListEffect, bulkWeight,
  clone, deleteOption, deletePartition, describeCondition, describeEffects, emptyRecipe, findReferences, glossOption, glossTag,
  missingGlosses, moveOrCopy, newId, normalizeStyleTags, optionLabel, optionRef, previewStyle, splitStyleTags, splitTags, targetOptions,
  type BulkTarget, type Condition, type Effects, type ListEffect, type Partition, type Recipe, type RecipeOption, type RecipeSummary,
  type Rule, type SampleItem, type SampleResult,
} from './recipe'
import { MAX_DATASET_ITEMS } from './dataset-run'
import {
  bundleFileName, conflictingPartitions, exportPartitions, parsePartitionSource, planPartitionImport,
  type PartitionAction, type PartitionBundle,
} from './recipe-partitions'

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

  const missingCount = missingGlosses(recipe).length
  const tabs: Array<[Tab, string, string]> = [
    ['partitions', '分区与选项', '每个分区抽一个（或几个）选项，组合成一条提示词'],
    ['order', '顺序', '抽取顺序决定谁影响谁；输出顺序决定提示词怎么排'],
    ['rules', '规则', '全部抽完后，满足条件就增删 tag 或画风'],
    ['slots', '属性槽', '颜色等共享取值，填进 {color} 这样的占位'],
    ['regions', '部位与资源', '看不见的部位不写；手等资源有容量'],
    ['glossary', `翻译${missingCount ? `（缺 ${missingCount}）` : ''}`, '中文释义只用于显示'],
    ['json', '导入导出', '备份或分享配方 JSON'],
  ]

  return createPortal(<dialog ref={dialog} className="recipe-dialog" aria-labelledby="recipe-title" onCancel={event => { event.preventDefault(); close() }}>
    <div className="recipe-shell">
      <header className="recipe-header">
        <h2 id="recipe-title"><Shuffle size={16} aria-hidden="true" /> 随机训练集配方</h2>
        <label className="recipe-header-field"><span>配方</span>
          <select value={loadedAt ? currentId : ''} onChange={event => { if (event.target.value) void load(event.target.value) }}>
            {!loadedAt && <option value="">（未保存的草稿）</option>}
            {list?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select></label>
        <label className="recipe-header-field"><span>名称</span>
          <input value={name} maxLength={100} onChange={event => setName(event.target.value)} /></label>
        <span className={`recipe-save-state${dirty ? ' dirty' : ''}`}>{dirty ? '有未保存的修改' : '已保存'}</span>
        <span className="recipe-header-actions">
          <button className="icon-button" type="button" title="撤销" aria-label="撤销" disabled={!history.canUndo} onClick={history.undo}><Undo2 size={15} /></button>
          <button className="icon-button" type="button" title="重做" aria-label="重做" disabled={!history.canRedo} onClick={history.redo}><Redo2 size={15} /></button>
          <button className="secondary" type="button" disabled={busy} onClick={() => void save()}><Save size={14} aria-hidden="true" /> 保存</button>
          <details className="recipe-menu">
            <summary className="icon-button" title="更多" aria-label="更多操作"><MoreHorizontal size={16} /></summary>
            <div className="recipe-menu-list" onClick={event => (event.currentTarget.parentElement as HTMLDetailsElement).open = false}>
              <button type="button" disabled={busy} onClick={() => void save(true)}><Copy size={13} aria-hidden="true" /> 另存为新配方</button>
              <button type="button" onClick={() => void startFromTemplate(false)}><Plus size={13} aria-hidden="true" /> 从基础模板新建</button>
              <button type="button" onClick={() => void startFromTemplate(true)}><Plus size={13} aria-hidden="true" /> 新建空白配方</button>
              <button type="button" className="danger-text" disabled={!loadedAt} onClick={() => void remove()}><Trash2 size={13} aria-hidden="true" /> 删除这个配方</button>
            </div>
          </details>
          <button className="icon-button" type="button" title="关闭" aria-label="关闭" onClick={close}><X size={16} /></button>
        </span>
      </header>
      {(error || message) && <p className={error ? 'alert recipe-message' : 'subtle recipe-message'} role={error ? 'alert' : 'status'}>{error || message}</p>}
      <nav className="recipe-tabs" role="tablist">
        {tabs.map(([id, label, hint]) => <button key={id} type="button" role="tab" title={hint} aria-selected={tab === id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>)}
        <span className="recipe-tab-hint">{tabs.find(([id]) => id === tab)?.[2]}</span>
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
        <SamplePanel api={api} open={open} recipe={recipe} style={style} recipeRef={{ id: currentId, name: name.trim() || '未命名配方' }}
          saved={Boolean(loadedAt) && !dirty} onGenerate={result => { onGenerate(result); onClose() }} />
      </div>
    </div>
  </dialog>, document.body)
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
    // Computed outside the state updater: React may run updaters twice, and the anchor ref
    // must be read before it moves.
    const next = new Set(selected)
    const keys = rows.map(row => row.key)
    const from = anchor.current ? keys.indexOf(anchor.current) : -1
    if (shift && from >= 0) {
      const to = keys.indexOf(key)
      keys.slice(Math.min(from, to), Math.max(from, to) + 1).forEach(item => next.add(item))
    } else if (next.has(key)) next.delete(key)
    else next.add(key)
    anchor.current = key
    setSelected(next)
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
      <div className="recipe-list-title">分区 <small>按抽取顺序</small></div>
      {recipe.draw_order.map((id, index) => {
        const item = recipe.partitions.find(p => p.id === id)
        if (!item) return null
        return <button key={id} type="button" className={`recipe-partition-item${item.id === part?.id && !allPartitions ? ' active' : ''}`} onClick={() => { setActive(id); setAllPartitions(false) }}>
          <span className="recipe-partition-index">{index + 1}</span><span className="recipe-partition-name">{item.label || item.id}</span><small>{item.options.length}</small>
        </button>
      })}
      <div className="recipe-list-actions">
        <button type="button" className="text-action" onClick={addPartition}><Plus size={13} aria-hidden="true" /> 新建分区</button>
        <button type="button" className={`text-action${allPartitions ? ' active' : ''}`} onClick={() => setAllPartitions(true)}><ListChecks size={13} aria-hidden="true" /> 跨分区批量编辑</button>
      </div>
    </aside>
    <section className="recipe-partition-detail">
      {part && !allPartitions && <PartitionSettings history={history} part={part} onRemove={() => removePartition(part)} />}
      {allPartitions && <div className="recipe-section-head"><h3>全部选项</h3><p>勾选多个分区里的选项，一起批量修改。</p></div>}
      <div className="recipe-toolbar">
        <input type="search" value={filter} placeholder="按 tag 或中文名筛选选项" aria-label="筛选选项" onChange={event => setFilter(event.target.value)} />
        <span className="recipe-toolbar-actions">
          {!allPartitions && <button className="secondary small" type="button" onClick={addOption}><Plus size={13} aria-hidden="true" /> 新增选项</button>}
          {!allPartitions && part && !part.options.some(option => option.none) && <button className="text-action" type="button" title="抽到「无」时这一分区不写任何内容" onClick={addNone}><Plus size={13} aria-hidden="true" /> 添加「无」</button>}
          <button className="text-action" type="button" onClick={() => setSelected(new Set(rows.map(row => row.key)))}>全选（{rows.length}）</button>
          {selected.size > 0 && <button className="text-action" type="button" onClick={() => setSelected(new Set())}>取消选择</button>}
        </span>
      </div>
      {selected.size > 0 && <BulkPanel history={history} targets={targets} onDone={() => setSelected(new Set())} />}
      <div className="recipe-option-head" aria-hidden="true">
        <span /><span>英文 tag（进提示词和 caption）</span><span>中文名</span><span>占比</span><span>概率</span><span />
      </div>
      <ul className="recipe-options">
        {rows.map(row => <OptionRow key={row.key} history={history} part={row.part} option={row.option} showPartition={allPartitions}
          checked={selected.has(row.key)} onToggle={shift => toggle(row.key, shift)} />)}
        {!rows.length && <li className="recipe-empty">没有选项。</li>}
      </ul>
      <p className="recipe-footnote">勾选左侧方框可多选（按住 Shift 连选），然后在上方批量修改。点「规则」展开某个选项的条件和效果。</p>
    </section>
  </div>
}

const NONE = 'none'

function PartitionSettings({ history, part, onRemove }: { history: History; part: Partition; onRemove: () => void }) {
  const { recipe } = history
  const [open, setOpen] = useState(false)
  const update = (mutate: (p: Partition) => void) => history.change(draft => mutate(draft.partitions.find(item => item.id === part.id)!))
  const references = findReferences(recipe, part.id)
  const needs = (part.needs ?? []).map(id => recipe.regions?.find(region => region.id === id)?.label || id)
  const summary = [
    part.mode === 'fill' ? `重复抽，最多 ${part.max_draws ?? 2} 个` : '每条抽 1 个',
    part.quota ? '按配额精确分配' : '',
    needs.length ? `需要 ${needs.join('、')} 可见` : '',
    part.when ? `条件：${describeCondition(recipe, part.when)}` : '',
  ].filter(Boolean)
  return <div className="recipe-partition-settings">
    <div className="recipe-section-head">
      <input className="recipe-title-input" value={part.label ?? ''} maxLength={100} aria-label="分区名称" onChange={event => update(p => { p.label = event.target.value })} />
      <button className="text-action" type="button" aria-expanded={open} onClick={() => setOpen(value => !value)}><Settings2 size={13} aria-hidden="true" /> 分区设置 {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}</button>
      <button className="text-action" type="button" title="导出这个分区及其用到的取值槽、部位等，可导入到其他配方" onClick={() => exportPartitionFile(recipe, [part.id], '')}><Download size={13} aria-hidden="true" /> 导出分区</button>
      <button className="text-action danger-text" type="button" onClick={onRemove}><Trash2 size={13} aria-hidden="true" /> 删除分区</button>
    </div>
    <p className="recipe-summary">{summary.join(' · ')}{references.length ? ` · 被 ${references.length} 处引用` : ''}</p>
    {open && <div className="recipe-form">
      <Row label="抽取方式" hint="大多数分区每条只抽 1 个；手部动作、饰品这类可以抽多个。">
        <select value={part.mode ?? 'one'} onChange={event => update(p => { p.mode = event.target.value as 'one' | 'fill'; p.max_draws = p.mode === 'one' ? 1 : Math.max(2, p.max_draws ?? 2); if (p.mode === 'fill') p.quota = false })}>
          <option value="one">每条抽 1 个</option><option value="fill">重复抽多个</option></select>
        {part.mode === 'fill' && <label className="recipe-inline">最多 <input type="number" min={2} max={10} value={part.max_draws ?? 2} onChange={event => update(p => { p.max_draws = Math.min(10, Math.max(2, Number(event.target.value) || 2)) })} /> 个</label>}
      </Row>
      {part.mode === 'fill' && <p className="recipe-help">资源（如手）用完、抽到「无」或达到上限时停止。</p>}
      <Row label="配额" hint="在可选项及其占比相同的条目中分别分配；因不可见或条件不满足而跳过的条目不计入。小批量按整数取整。">
        <label className="recipe-check"><input type="checkbox" checked={Boolean(part.quota)} disabled={part.mode === 'fill'} onChange={event => update(p => { p.quota = event.target.checked })} /> 在符合条件的条目中按配额分配</label>
      </Row>
      <Row label="需要部位可见" hint="这些部位看不见时（例如上半身构图看不见脚），整个分区跳过。">
        <RegionChips recipe={recipe} value={part.needs ?? []} onChange={value => update(p => { p.needs = value })} />
      </Row>
      <Row label="分区条件" hint="不满足时整个分区跳过。">
        <ConditionList recipe={recipe} value={part.when ?? null} onChange={when => update(p => { p.when = when })} />
      </Row>
      {references.length > 0 && <Row label="谁引用了它" hint="删除分区时这些引用也会被删除。">
        <ul className="recipe-ref-list">{references.map((reference, index) => <li key={index}>{reference.where} 的{reference.text}
          <button className="text-action" type="button" onClick={() => history.change(draft => findReferences(draft, part.id)[index]?.remove(draft))}>删除引用</button></li>)}</ul>
      </Row>}
      <p className="recipe-id">分区 ID：{part.id}（引用都用 ID，改名不影响）</p>
    </div>}
  </div>
}

/** One labelled form row: fixed-width label column, controls, optional help below. */
function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <div className="recipe-row">
    <span className="recipe-row-label">{label}</span>
    <div className="recipe-row-body"><div className="recipe-row-controls">{children}</div>{hint && <p className="recipe-help">{hint}</p>}</div>
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
  const ruleCount = effects.length + (condition ? 1 : 0) + (option.needs?.length ? 1 : 0) + (option.weight_mods?.length ?? 0) + Object.keys(option.slots ?? {}).length

  function remove() {
    if (references.length && !window.confirm(`选项被 ${references.length} 处引用：\n${references.map(r => `· ${r.where} 的${r.text}`).join('\n')}\n删除选项并同时删除这些引用？`)) return
    history.change(draft => deleteOption(draft, part.id, option.id))
  }

  return <li className={`recipe-option${option.disabled ? ' muted' : ''}${option.none ? ' none' : ''}${expanded ? ' expanded' : ''}`}>
    <div className="recipe-option-grid">
      <input type="checkbox" checked={checked} aria-label={`选择 ${option.label || option.tags || option.id}`}
        onClick={event => { event.preventDefault(); onToggle(event.shiftKey) }} onChange={() => {}} />
      <div className="recipe-cell">
        {showPartition && <span className="recipe-badge">{part.label || part.id}</span>}
        {option.none
          ? <span className="recipe-none">无 <small>抽到时这一分区不写</small></span>
          : <input className="recipe-tags" value={option.tags ?? ''} placeholder="例如 upper body，可写 {color} skirt" spellCheck={false} aria-label="英文 tag"
            onChange={event => update(o => { o.tags = event.target.value })} />}
      </div>
      <input className="recipe-label" value={option.label ?? ''} placeholder={glosses.map(g => g.zh ?? g.tag).join('，') || '中文名'} maxLength={100} aria-label="中文名"
        onChange={event => update(o => { o.label = event.target.value })} />
      <input className="recipe-weight" type="number" min={0.001} step="any" value={option.weight} aria-label="占比（相对权重）" title="相对权重：同一分区里越大越常被抽到"
        onChange={event => { const value = Number(event.target.value); if (value > 0) update(o => { o.weight = value }) }} />
      <span className="recipe-share" title="同一分区内被抽到的大致概率">{(share * 100).toFixed(1)}%</span>
      <span className="recipe-row-buttons">
        <button className={`recipe-rule-toggle${ruleCount ? ' has' : ''}`} type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>
          规则{ruleCount ? ` ${ruleCount}` : ''} {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}</button>
        <button className="icon-button danger" type="button" title="删除选项" aria-label="删除选项" onClick={remove}><Trash2 size={13} /></button>
      </span>
    </div>
    {!expanded && <div className="recipe-option-meta">
      {!option.none && glosses.some(gloss => gloss.zh === null) && <span className="missing">未翻译：{glosses.filter(g => g.zh === null).map(g => g.tag).join('、')}</span>}
      {option.disabled && <b>已停用</b>}
      {option.needs?.length ? <span className="recipe-cond">需要 {option.needs.map(id => recipe.regions?.find(r => r.id === id)?.label || id).join('、')} 可见</span> : null}
      {condition && <span className="recipe-cond">只在 {condition} 时可抽</span>}
      {effects.map(text => <span key={text} className="recipe-effect">{text}</span>)}
      {option.slots && Object.entries(option.slots).map(([slotId, use]) => <span key={slotId} className="recipe-effect">{slotSummary(recipe, slotId, use)}</span>)}
      {references.length > 0 && <span className="recipe-ref-count">被 {references.length} 处引用</span>}
    </div>}
    {expanded && <OptionDetail history={history} part={part} option={option} update={update} />}
  </li>
}

function slotSummary(recipe: Recipe, slotId: string, use: NonNullable<RecipeOption['slots']>[string]): string {
  const slot = recipe.slots?.find(item => item.id === slotId)
  const name = (id: string) => slot?.values.find(value => value.id === id)?.label || id
  const parts = [slot?.label || slotId]
  if (use.only?.length) parts.push(`只用 ${use.only.map(name).join('、')}`)
  if (use.exclude?.length) parts.push(`不用 ${use.exclude.map(name).join('、')}`)
  if (use.exclude_state) parts.push(`不同于${recipe.states?.[use.exclude_state] || use.exclude_state}`)
  if (use.set_state) parts.push(`记为${recipe.states?.[use.set_state] || use.set_state}`)
  return parts.join('：')
}

function OptionDetail({ history, part, option, update }: { history: History; part: Partition; option: RecipeOption; update: (mutate: (o: RecipeOption) => void) => void }) {
  const { recipe } = history
  const placeholders = [...(option.tags ?? '').matchAll(/\{([a-z0-9-]+)\}/g)].map(match => match[1])
  return <div className="recipe-option-detail">
    <section className="recipe-group">
      <h5>什么时候可以抽到它</h5>
      {!option.none && <Row label="需要部位可见" hint="例如「挥手」需要手可见；构图看不见时这个选项不会被抽到。">
        <RegionChips recipe={recipe} value={option.needs ?? []} onChange={needs => update(o => { o.needs = needs })} />
      </Row>}
      <Row label="条件" hint="全部满足才可能抽到。只能引用抽取顺序更靠前的分区。">
        <ConditionList recipe={recipe} value={option.when ?? null} onChange={when => update(o => { o.when = when })} />
      </Row>
      <Row label="条件占比" hint="满足条件时把占比乘以系数，例如夜晚时微笑 ×0.5（0 等于禁止）。">
        <WeightModsField recipe={recipe} option={option} update={update} />
      </Row>
    </section>
    {placeholders.map(slotId => <SlotUseEditor key={slotId} recipe={recipe} slotId={slotId} option={option} update={update} />)}
    <section className="recipe-group">
      <h5>抽到它之后</h5>
      <EffectsEditor recipe={recipe} effects={option.effects ?? {}} ownPartition={part.id} allowStructural onChange={effects => update(o => { o.effects = effects })} />
    </section>
    <section className="recipe-group">
      <h5>其他</h5>
      <Row label="画幅" hint="抽到它时用的图片比例；不设则按构图自动判断。">
        <select value={option.size ?? ''} onChange={event => update(o => { o.size = (event.target.value || null) as RecipeOption['size'] })}>
          <option value="">自动</option><option value="portrait">竖图</option><option value="square">方图</option><option value="landscape">横图</option></select>
      </Row>
      <Row label="状态">
        <label className="recipe-check"><input type="checkbox" checked={Boolean(option.disabled)} onChange={event => update(o => { o.disabled = event.target.checked })} /> 停用（保留但不会被抽到）</label>
        <label className="recipe-check"><input type="checkbox" checked={Boolean(option.child)} onChange={event => update(o => {
          o.child = event.target.checked
          o.effects = { ...o.effects, set: { ...o.effects?.set, ...(event.target.checked ? { age: 'child' } : {}) } }
        })} /> 儿童选项</label>
      </Row>
      <p className="recipe-id">选项 ID：{option.id}</p>
    </section>
  </div>
}

function WeightModsField({ recipe, option, update }: { recipe: Recipe; option: RecipeOption; update: (mutate: (o: RecipeOption) => void) => void }) {
  const mods = option.weight_mods ?? []
  return <div className="recipe-stack">
    {mods.map((mod, index) => <div key={index} className="recipe-clause">
      <span>当 {describeCondition(recipe, mod.when)}</span>
      <label className="recipe-inline">占比 × <input type="number" min={0} step="any" value={mod.factor} onChange={event => update(o => { o.weight_mods![index].factor = Math.max(0, Number(event.target.value) || 0) })} /></label>
      <button className="icon-button" type="button" aria-label="删除" title="删除" onClick={() => update(o => { o.weight_mods = o.weight_mods!.filter((_, i) => i !== index) })}><X size={13} /></button>
    </div>)}
    <ConditionBuilder recipe={recipe} buttonLabel="添加" onAdd={when => update(o => { o.weight_mods = [...(o.weight_mods ?? []), { when, factor: 0.5 }] })} />
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
  return <section className="recipe-group">
    <h5>{slot.label || slot.id}（tag 里的 {`{${slot.id}}`}）</h5>
    <Row label="可用的值" hint="点一下切换：普通 → ✓ 只用这些 → × 不用。全部普通表示都可以用。">
      <div className="recipe-chips">{slot.values.map(value => {
        const state = use.exclude?.includes(value.id) ? 'exclude' : use.only?.includes(value.id) ? 'only' : ''
        return <button key={value.id} type="button" className={`recipe-chip ${state}`}
          onClick={() => set(u => {
            const only = new Set(u.only ?? [])
            const exclude = new Set(u.exclude ?? [])
            if (!state) { only.add(value.id) } else if (state === 'only') { only.delete(value.id); exclude.add(value.id) } else exclude.delete(value.id)
            u.only = only.size ? [...only] : null
            u.exclude = [...exclude]
          })}>{state === 'exclude' ? '× ' : state === 'only' ? '✓ ' : ''}{value.label || value.tag}</button>
      })}</div>
    </Row>
    <Row label="不能和…相同" hint="例如下装颜色不能和上衣颜色相同。">
      <select value={use.exclude_state ?? ''} onChange={event => set(u => { u.exclude_state = event.target.value || null })}>
        <option value="">不限制</option>{states.map(key => <option key={key} value={key}>{recipe.states?.[key] || key}</option>)}</select>
    </Row>
    <Row label="记住抽到的值" hint="写一个状态名（如 top-color），后面的选项可以用它比较。">
      <input value={use.set_state ?? ''} placeholder="不记录" list="recipe-states" onChange={event => set(u => { u.set_state = event.target.value.trim() || null })} />
    </Row>
  </section>
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

function RegionChips({ recipe, value, onChange, tone = 'only' }: { recipe: Recipe; value: string[]; onChange: (value: string[]) => void; tone?: 'only' | 'exclude' }) {
  const regions = recipe.regions ?? DEFAULT_REGIONS
  return <div className="recipe-chips">{regions.map(region => <button key={region.id} type="button" className={`recipe-chip ${value.includes(region.id) ? tone : ''}`}
    onClick={() => onChange(value.includes(region.id) ? value.filter(id => id !== region.id) : [...value, region.id])}>{region.label || region.id}</button>)}</div>
}

function ConditionList({ recipe, value, onChange }: { recipe: Recipe; value: Condition | null; onChange: (value: Condition | null) => void }) {
  const clauses = value === null ? [] : 'all' in value ? value.all : [value]
  const set = (next: Condition[]) => onChange(next.length === 0 ? null : next.length === 1 ? next[0] : { all: next })
  return <div className="recipe-stack">
    {clauses.map((clause, index) => <div key={index} className="recipe-clause">
      <span>{index > 0 && <b className="recipe-and">并且</b>}{describeCondition(recipe, clause)}</span>
      <button className="icon-button" type="button" aria-label="删除条件" title="删除条件" onClick={() => set(clauses.filter((_, i) => i !== index))}><X size={13} /></button>
    </div>)}
    {!clauses.length && <span className="recipe-muted">无条件</span>}
    <ConditionBuilder recipe={recipe} buttonLabel="添加条件" onAdd={clause => set([...clauses, clause])} />
  </div>
}

type ConditionKind = 'chosen' | 'not-chosen' | 'drawn' | 'not-drawn' | 'state' | 'not-state' | 'visible' | 'hidden' | 'tag' | 'not-tag' | 'any-chosen'

/** Collapsed "+ add" button that opens a one-line, sentence-style condition builder. */
function ConditionBuilder({ recipe, onAdd, buttonLabel }: { recipe: Recipe; onAdd: (condition: Condition) => void; buttonLabel: string }) {
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<ConditionKind>('chosen')
  const [partition, setPartition] = useState(recipe.draw_order[0] ?? '')
  const [options, setOptions] = useState<string[]>([])
  const [state, setState] = useState(stateKeys(recipe)[0] ?? '')
  const [values, setValues] = useState<string[]>([])
  const [region, setRegion] = useState((recipe.regions ?? DEFAULT_REGIONS)[0]?.id ?? '')
  const [tag, setTag] = useState('')
  const part = recipe.partitions.find(item => item.id === partition)
  const regions = recipe.regions ?? DEFAULT_REGIONS

  function build(): Condition | null {
    const chosen = options.map(option => ({ chosen: optionRef(partition, option) }) as Condition)
    const any = chosen.length === 1 ? chosen[0] : { any: chosen }
    switch (kind) {
      case 'chosen': return chosen.length ? any : null
      case 'any-chosen': return chosen.length ? { any: chosen } : null
      case 'not-chosen': return chosen.length ? { not: any } : null
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
  if (!open) return <button className="text-action recipe-add" type="button" onClick={() => setOpen(true)}><Plus size={13} aria-hidden="true" /> {buttonLabel}</button>
  const toggle = (list: string[], id: string) => list.includes(id) ? list.filter(item => item !== id) : [...list, id]
  return <div className="recipe-builder">
    <div className="recipe-builder-line">
      <select value={kind} aria-label="条件类型" onChange={event => setKind(event.target.value as ConditionKind)}>
        <optgroup label="看其他分区抽到了什么">
          <option value="chosen">某分区抽到了…</option><option value="not-chosen">某分区没抽到…</option>
          <option value="drawn">某分区有内容</option><option value="not-drawn">某分区没有内容</option>
        </optgroup>
        <optgroup label="看状态 / 部位 / tag">
          <option value="state">状态是…</option><option value="not-state">状态不是…</option>
          <option value="visible">部位可见</option><option value="hidden">部位看不见</option>
          <option value="tag">提示词里有 tag</option><option value="not-tag">提示词里没有 tag</option>
        </optgroup>
      </select>
      {['chosen', 'not-chosen', 'drawn', 'not-drawn'].includes(kind) && <select value={partition} aria-label="分区" onChange={event => { setPartition(event.target.value); setOptions([]) }}>
        {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>}
      {['state', 'not-state'].includes(kind) && <select value={state} aria-label="状态" onChange={event => { setState(event.target.value); setValues([]) }}>
        {stateKeys(recipe).map(key => <option key={key} value={key}>{recipe.states?.[key] || key}</option>)}</select>}
      {['visible', 'hidden'].includes(kind) && <select value={region} aria-label="部位" onChange={event => setRegion(event.target.value)}>
        {regions.map(item => <option key={item.id} value={item.id}>{item.label || item.id}</option>)}</select>}
      {['tag', 'not-tag'].includes(kind) && <input value={tag} placeholder="例如 smile" aria-label="tag" onChange={event => setTag(event.target.value)} />}
    </div>
    {['chosen', 'not-chosen'].includes(kind) && part && <div className="recipe-chips">
      <span className="recipe-muted">选一个或多个（任一满足）：</span>
      {part.options.map(option => <button key={option.id} type="button" className={`recipe-chip ${options.includes(option.id) ? 'only' : ''}`}
        onClick={() => setOptions(current => toggle(current, option.id))}>{option.none ? '无' : option.label || option.tags || option.id}</button>)}</div>}
    {['state', 'not-state'].includes(kind) && <div className="recipe-chips">
      <span className="recipe-muted">选一个或多个值：</span>
      {stateValues(recipe, state).map(value => <button key={value} type="button" className={`recipe-chip ${values.includes(value) ? 'only' : ''}`}
        onClick={() => setValues(current => toggle(current, value))}>{value}</button>)}</div>}
    <div className="recipe-builder-actions">
      {condition && <span className="recipe-muted">预览：{describeCondition(recipe, condition)}</span>}
      <button className="secondary small" type="button" disabled={!condition} onClick={() => { if (condition) { onAdd(condition); setOptions([]); setValues([]); setTag(''); setOpen(false) } }}>确定</button>
      <button className="text-action" type="button" onClick={() => setOpen(false)}>取消</button>
    </div>
  </div>
}

function EffectsEditor({ recipe, effects, ownPartition, allowStructural, onChange }: {
  recipe: Recipe; effects: Effects; ownPartition: string | null; allowStructural: boolean; onChange: (effects: Effects) => void
}) {
  const set = (mutate: (e: Effects) => void) => { const next = clone(effects); mutate(next); onChange(next) }
  const others = recipe.draw_order.filter(id => id !== ownPartition)
  const [allowPart, setAllowPart] = useState(others[0] ?? '')
  const allowTarget = recipe.partitions.find(part => part.id === allowPart)
  const partName = (id: string) => recipe.partitions.find(p => p.id === id)?.label || id
  const allowed = Object.entries(effects.allow_options ?? {})
  return <div className="recipe-effects">
    <h6>改提示词和画风</h6>
    <Row label="加内容 tag" hint="写进提示词，也会进 caption。例如不写鞋时补 barefoot。">
      <TagListField value={effects.content_add ?? []} onChange={value => set(e => { e.content_add = value })} /></Row>
    <Row label="删内容 tag" hint="从这一条的提示词里删掉某个 tag。">
      <TagListField value={effects.remove_tags ?? []} onChange={value => set(e => { e.remove_tags = value })} /></Row>
    <Row label="加画风 tag" hint="只加在这一条的画风里，不进 caption，支持 3::tag:: 和 {tag} 权重。">
      <TagListField value={effects.style_add ?? []} split={splitStyleTags} onChange={value => set(e => { e.style_add = value })} /></Row>
    <Row label="删画风 tag" hint="只从这一条的画风里删，例如夜晚删 sunlight。">
      <TagListField value={effects.style_remove ?? []} split={text => normalizeStyleTags([text], true)} onChange={value => set(e => { e.style_remove = value })} /></Row>
    <h6>影响其他分区</h6>
    {allowStructural && <Row label="隐藏部位" hint="被隐藏的部位上的分区和选项都会跳过，例如上半身隐藏下身和脚。">
      <RegionChips recipe={recipe} value={effects.hide ?? []} tone="exclude" onChange={value => set(e => { e.hide = value })} /></Row>}
    <Row label="移除分区" hint="这些分区不写（已经抽到的会被撤销），例如闭眼移除瞳色。">
      <div className="recipe-chips">{others.map(id => <button key={id} type="button" className={`recipe-chip ${effects.remove_partitions?.includes(id) ? 'exclude' : ''}`}
        onClick={() => set(e => { e.remove_partitions = e.remove_partitions?.includes(id) ? e.remove_partitions.filter(item => item !== id) : [...(e.remove_partitions ?? []), id] })}>
        {partName(id)}</button>)}</div></Row>
    <Row label="只允许" hint="让某个分区只能抽这几个选项，例如校服 → 下装只允许百褶裙。">
      <div className="recipe-stack">
        {allowed.map(([partId, ids]) => <div key={partId} className="recipe-clause"><span>{partName(partId)} 只允许：{ids.map(id => optionLabel(recipe, `${partId}.${id}`).split('.')[1]).join('、')}</span>
          <button className="icon-button" type="button" aria-label="删除" onClick={() => set(e => { const map = { ...(e.allow_options ?? {}) }; delete map[partId]; e.allow_options = map })}><X size={13} /></button></div>)}
        <div className="recipe-builder-line"><span className="recipe-muted">编辑分区</span>
          <select value={allowPart} aria-label="限定的分区" onChange={event => setAllowPart(event.target.value)}>
            {others.map(id => <option key={id} value={id}>{partName(id)}</option>)}</select></div>
        {allowTarget && <div className="recipe-chips">{allowTarget.options.map(option => {
          const listed = effects.allow_options?.[allowPart]?.includes(option.id)
          return <button key={option.id} type="button" className={`recipe-chip ${listed ? 'only' : ''}`} onClick={() => set(e => {
            const map = { ...(e.allow_options ?? {}) }
            const current = map[allowPart] ?? []
            const next = listed ? current.filter(id => id !== option.id) : [...current, option.id]
            if (next.length) map[allowPart] = next
            else delete map[allowPart]
            e.allow_options = map
          })}>{listed ? '✓ ' : ''}{option.none ? '无' : option.label || option.tags || option.id}</button>
        })}</div>}
      </div></Row>
    <Row label="移除选项" hint="让某几个具体选项不能被抽到。格式：分区ID.选项ID。">
      <TagListField value={effects.remove_options ?? []} placeholder="例如 hands.waving" onChange={value => set(e => { e.remove_options = value })} /></Row>
    {allowStructural && <>
      <h6>记录与占用</h6>
      <Row label="设置状态" hint="给后面的条件用，例如姿势=坐。">
        <KeyValueField value={effects.set ?? {}} keyPlaceholder="状态名，如 pose" valuePlaceholder="值，如 sitting" onChange={value => set(e => { e.set = value })} /></Row>
      <Row label="占用资源" hint="例如双手动作占用 hands 2，手用完后不再抽手部动作。">
        <KeyValueField value={Object.fromEntries(Object.entries(effects.consume ?? {}).map(([k, v]) => [k, String(v)]))}
          keyPlaceholder="资源" valuePlaceholder="数量" keys={Object.keys(recipe.resources ?? {})}
          onChange={value => set(e => { e.consume = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, Math.max(1, Number(v) || 1)])) })} /></Row>
    </>}
  </div>
}

function KeyValueField({ value, keyPlaceholder, valuePlaceholder, onChange, keys }: {
  value: Record<string, string>; keyPlaceholder: string; valuePlaceholder: string; onChange: (value: Record<string, string>) => void; keys?: string[]
}) {
  const [key, setKey] = useState('')
  const [val, setVal] = useState('')
  const valid = /^[a-z0-9][a-z0-9-]*$/
  return <div className="recipe-kv">
    {Object.entries(value).map(([k, v]) => <button key={k} type="button" className="recipe-chip only" title="点击删除"
      onClick={() => { const next = { ...value }; delete next[k]; onChange(next) }}>{k} = {v} ×</button>)}
    {keys ? <select value={key} onChange={event => setKey(event.target.value)} aria-label={keyPlaceholder}><option value="">{keyPlaceholder}</option>{keys.map(k => <option key={k}>{k}</option>)}</select>
      : <input value={key} placeholder={keyPlaceholder} list="recipe-states" onChange={event => setKey(event.target.value.trim())} />}
    <input value={val} placeholder={valuePlaceholder} onChange={event => setVal(event.target.value.trim())} />
    <button className="text-action" type="button" disabled={!valid.test(key) || !val || (!keys && !valid.test(val))}
      onClick={() => { onChange({ ...value, [key]: val }); setKey(''); setVal('') }}><Plus size={12} aria-hidden="true" /> 添加</button>
  </div>
}

function TagListField({ value, placeholder = '输入 tag，回车添加', split = splitTags, onChange }: {
  value: string[]; placeholder?: string; split?: (text: string) => string[]; onChange: (value: string[]) => void
}) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const add = () => {
    try {
      const tags = split(text).filter(tag => !value.includes(tag))
      if (tags.length) onChange([...value, ...tags])
      setText('')
      setError('')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'tag 格式无效。')
    }
  }
  return <div className="recipe-taglist">
    {value.map(tag => <button key={tag} type="button" className="recipe-chip only" title="点击删除" onClick={() => onChange(value.filter(item => item !== tag))}>{tag} ×</button>)}
    <input value={text} placeholder={placeholder} spellCheck={false} aria-invalid={!!error} onChange={event => { setText(event.target.value); setError('') }}
      onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); add() } }} onBlur={add} />
    {error && <span className="alert" role="alert">{error}</span>}
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
    <div className="recipe-bulk-head"><strong>批量修改已选的 {options.length} 个选项</strong>
      <div className="recipe-segment" role="group" aria-label="批量操作">
        {([['effect', '加 / 删效果'], ['allow', '只允许'], ['condition', '条件'], ['weight', '占比'], ['move', '移动 / 删除']] as const).map(([id, label]) =>
          <button key={id} type="button" className={kind === id ? 'active' : ''} onClick={() => setKind(id)}>{label}</button>)}
      </div>
      <button className="icon-button" type="button" aria-label="关闭批量编辑" title="取消选择" onClick={onDone}><X size={14} /></button>
    </div>
    <div className="recipe-bulk-body">
    {kind === 'effect' && <>
      <select value={effect} aria-label="效果" onChange={event => setEffect(event.target.value as ListEffect)}>
        {LIST_EFFECTS.map(key => <option key={key} value={key}>{EFFECT_LABELS[key]}</option>)}</select>
      {effect === 'hide' ? <select value={value} aria-label="部位" onChange={event => setValue(event.target.value)}><option value="">选择部位</option>
        {(recipe.regions ?? DEFAULT_REGIONS).map(region => <option key={region.id} value={region.id}>{region.label || region.id}</option>)}</select>
        : effect === 'remove_partitions' ? <select value={value} aria-label="分区" onChange={event => setValue(event.target.value)}><option value="">选择分区</option>
          {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
          : <input value={value} placeholder={effect === 'remove_options' ? '分区ID.选项ID' : 'tag'} spellCheck={false} onChange={event => setValue(event.target.value)} />}
      <button className="secondary small" type="button" disabled={!value.trim()} onClick={() => apply('add')}>给它们都加上</button>
      <button className="text-action" type="button" disabled={!value.trim()} onClick={() => apply('remove')}>从它们身上都删掉</button>
    </>}
    {kind === 'allow' && <>
      <select value={partition} aria-label="分区" onChange={event => { setPartition(event.target.value); setAllowed([]) }}>
        {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
      {part && <div className="recipe-chips">{part.options.map(option => <button key={option.id} type="button" className={`recipe-chip ${allowed.includes(option.id) ? 'only' : ''}`}
        onClick={() => setAllowed(current => current.includes(option.id) ? current.filter(id => id !== option.id) : [...current, option.id])}>{option.none ? '无' : option.label || option.tags}</button>)}</div>}
      <button className="secondary small" type="button" disabled={!allowed.length} onClick={() => apply('add')}>设置「只允许」</button>
      <button className="text-action" type="button" onClick={() => apply('remove')}>取消对这个分区的限制</button>
    </>}
    {kind === 'condition' && <ConditionBuilder recipe={recipe} buttonLabel="给它们都加一个条件" onAdd={clause => {
      history.change(draft => { const [c, s] = bulkCondition(targetOptions(draft, targets), clause, 'add'); setResult(`${c} 个选项已添加条件，${s} 个已存在`) })
    }} />}
    {kind === 'condition' && <ConditionBuilder recipe={recipe} buttonLabel="从它们身上删掉一个条件" onAdd={clause => {
      history.change(draft => { const [c, s] = bulkCondition(targetOptions(draft, targets), clause, 'remove'); setResult(`${c} 个选项已删除条件，${s} 个没有`) })
    }} />}
    {kind === 'weight' && <>
      <select value={weightMode} aria-label="方式" onChange={event => setWeightMode(event.target.value as typeof weightMode)}>
        <option value="set">占比都设为</option><option value="multiply">占比都乘以</option><option value="normalize">按比例缩放，总和为</option></select>
      <input type="number" min={0.001} step="any" value={weight} onChange={event => setWeight(event.target.value)} />
      <button className="secondary small" type="button" disabled={!(Number(weight) > 0)} onClick={() => history.change(draft => bulkWeight(targetOptions(draft, targets), weightMode, Number(weight)))}>应用</button>
    </>}
    {kind === 'move' && <>
      <select value={partition} aria-label="目标分区" onChange={event => setPartition(event.target.value)}>
        {recipe.draw_order.map(id => <option key={id} value={id}>{recipe.partitions.find(p => p.id === id)?.label || id}</option>)}</select>
      <span className="recipe-muted">目标分区</span>
      <button className="secondary small" type="button" onClick={() => { history.change(draft => setResult(`已移动 ${moveOrCopy(draft, targets, partition, false)} 个`)); onDone() }}>移动过去</button>
      <button className="text-action" type="button" onClick={() => history.change(draft => setResult(`已复制 ${moveOrCopy(draft, targets, partition, true)} 个`))}>复制过去</button>
      <span className="recipe-divider" />
      <button className="text-action" type="button" onClick={() => history.change(draft => targetOptions(draft, targets).forEach(o => { o.disabled = true }))}>停用</button>
      <button className="text-action" type="button" onClick={() => history.change(draft => targetOptions(draft, targets).forEach(o => { o.disabled = false }))}>启用</button>
      <button className="text-action danger-text" type="button" onClick={() => {
        const refs = targets.reduce((sum, t) => sum + findReferences(recipe, t.partition, t.option).length, 0)
        if (!window.confirm(`删除 ${targets.length} 个选项${refs ? `，同时删除 ${refs} 处引用` : ''}？（可撤销）`)) return
        history.change(draft => targets.forEach(t => deleteOption(draft, t.partition, t.option)))
        onDone()
      }}>删除</button>
    </>}
    </div>
    {result && <p className="recipe-muted">{result}</p>}
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
      <span className="recipe-partition-index">{index + 1}</span><span className="recipe-partition-name">{recipe.partitions.find(p => p.id === id)?.label || id}</span>
      <button className="icon-button" type="button" aria-label="上移" disabled={index === 0} onClick={() => move(index, index - 1)}><ArrowUp size={13} /></button>
      <button className="icon-button" type="button" aria-label="下移" disabled={index === order.length - 1} onClick={() => move(index, index + 1)}><ArrowDown size={13} /></button>
    </li>)}</ol></section>
}

function OrderTab({ history }: { history: History }) {
  const { recipe } = history
  const prompt = recipe.prompt_order?.length ? recipe.prompt_order : recipe.draw_order
  return <div className="recipe-page">
    <div className="recipe-section-head"><h3>顺序</h3></div>
    <p className="recipe-help"><b>抽取顺序</b>决定谁影响谁：会隐藏部位、移除或限定别的分区的，要排在被影响的分区前面（例如景别在鞋子前、表情在瞳色前）。<b>输出顺序</b>只决定这些 tag 在提示词里怎么排。可以拖动，也可以用箭头。</p>
    <div className="recipe-orders">
      <OrderList title="抽取顺序" order={recipe.draw_order} recipe={recipe} onChange={order => history.change(draft => { draft.draw_order = order })} />
      <OrderList title="输出顺序" order={prompt} recipe={recipe} onChange={order => history.change(draft => { draft.prompt_order = order })} />
    </div>
    <button className="text-action" type="button" onClick={() => history.change(draft => { draft.prompt_order = [...draft.draw_order] })}>把输出顺序设为和抽取顺序一样</button>
  </div>
}

function RulesTab({ history }: { history: History }) {
  const { recipe } = history
  const rules = recipe.rules ?? []
  const [openId, setOpenId] = useState<string | null>(null)
  const update = (id: string, mutate: (rule: Rule) => void) => history.change(draft => mutate(draft.rules!.find(rule => rule.id === id)!))
  return <div className="recipe-page">
    <div className="recipe-section-head"><h3>规则</h3>
      <button className="secondary small" type="button" onClick={() => history.change(draft => {
        const id = newId('rule', (draft.rules ?? []).map(r => r.id))
        draft.rules = [...(draft.rules ?? []), { id, label: '新规则', when: { tag: 'smile' }, effects: {} }]
        setOpenId(id)
      })}><Plus size={13} aria-hidden="true" /> 新建规则</button></div>
    <p className="recipe-help">规则在所有分区都抽完后按顺序执行，所以可以看任何分区的结果。例如：「提示词里有 smile → 画风加 gentle smile」。</p>
    <ul className="recipe-rule-list">{rules.map((rule, index) => {
      const open = openId === rule.id
      const effects = describeEffects(recipe, rule.effects)
      return <li key={rule.id} className={`recipe-rule${rule.disabled ? ' muted' : ''}${open ? ' open' : ''}`}>
        <div className="recipe-rule-head">
          <button className="icon-button" type="button" aria-expanded={open} aria-label={open ? '收起' : '展开'} onClick={() => setOpenId(open ? null : rule.id)}>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</button>
          <div className="recipe-rule-text">
            <strong>{rule.label || '未命名规则'}{rule.disabled && <em> · 已停用</em>}</strong>
            <span><b>当</b> {describeCondition(recipe, rule.when) || '（无条件）'} <b>就</b> {effects.join('；') || '（还没设置效果）'}</span>
          </div>
          <label className="recipe-check"><input type="checkbox" checked={!rule.disabled} onChange={event => update(rule.id, r => { r.disabled = !event.target.checked })} /> 启用</label>
          <button className="icon-button" type="button" aria-label="上移" title="上移" disabled={index === 0} onClick={() => history.change(draft => { const r = draft.rules!; [r[index - 1], r[index]] = [r[index], r[index - 1]] })}><ArrowUp size={13} /></button>
          <button className="icon-button" type="button" aria-label="下移" title="下移" disabled={index === rules.length - 1} onClick={() => history.change(draft => { const r = draft.rules!; [r[index + 1], r[index]] = [r[index], r[index + 1]] })}><ArrowDown size={13} /></button>
          <button className="icon-button danger" type="button" aria-label="删除规则" title="删除规则" onClick={() => { if (window.confirm(`删除规则「${rule.label || rule.id}」？（可撤销）`)) history.change(draft => { draft.rules = draft.rules!.filter(r => r.id !== rule.id) }) }}><Trash2 size={13} /></button>
        </div>
        {open && <div className="recipe-rule-body">
          <Row label="名称"><input value={rule.label ?? ''} maxLength={100} onChange={event => update(rule.id, r => { r.label = event.target.value })} /></Row>
          <section className="recipe-group"><h5>当（全部满足）</h5>
            <ConditionList recipe={recipe} value={rule.when} onChange={when => update(rule.id, r => { r.when = when ?? { tag: 'never-matches' } })} /></section>
          <section className="recipe-group"><h5>就</h5>
            <EffectsEditor recipe={recipe} effects={rule.effects} ownPartition={null} allowStructural={false} onChange={effects => update(rule.id, r => { r.effects = effects })} /></section>
        </div>}
      </li>
    })}</ul>
    {!rules.length && <p className="recipe-empty">还没有规则。</p>}
  </div>
}

function SlotsTab({ history }: { history: History }) {
  const { recipe } = history
  const setValue = (slotId: string, valueId: string, mutate: (value: NonNullable<Recipe['slots']>[number]['values'][number]) => void) =>
    history.change(draft => mutate(draft.slots!.find(s => s.id === slotId)!.values.find(v => v.id === valueId)!))
  return <div className="recipe-page">
    <div className="recipe-section-head"><h3>属性槽</h3>
      <button className="secondary small" type="button" onClick={() => {
        const id = window.prompt('槽的英文名（小写，用在 tag 里写成 {名字}，之后不能改）', 'color')?.trim()
        if (!id || !/^[a-z0-9][a-z0-9-]*$/.test(id) || recipe.slots?.some(s => s.id === id)) return
        history.change(draft => { draft.slots = [...(draft.slots ?? []), { id, label: id, values: [{ id: 'v-white', tag: 'white', label: '白色', weight: 1 }] }] })
      }}><Plus size={13} aria-hidden="true" /> 新建属性槽</button></div>
    <p className="recipe-help">一组可共用的取值，例如颜色。在选项的 tag 里写 <code>{'{color} china dress'}</code>，抽中时会从下面的颜色里按占比挑一个填进去，得到 <code>red china dress</code>。每个选项还可以在「规则」里限制能用哪些颜色。</p>
    {(recipe.slots ?? []).map(slot => {
      const total = slot.values.reduce((sum, value) => sum + value.weight, 0)
      return <section key={slot.id} className="recipe-card">
        <div className="recipe-section-head">
          <input className="recipe-title-input" value={slot.label ?? ''} aria-label="槽名称" onChange={event => history.change(draft => { draft.slots!.find(s => s.id === slot.id)!.label = event.target.value })} />
          <span className="recipe-muted">在 tag 里写 <code>{`{${slot.id}}`}</code></span>
          <button className="text-action danger-text" type="button" onClick={() => { if (window.confirm(`删除属性槽「${slot.label || slot.id}」？`)) history.change(draft => { draft.slots = draft.slots!.filter(s => s.id !== slot.id) }) }}><Trash2 size={13} aria-hidden="true" /> 删除</button>
        </div>
        <table className="recipe-table"><thead><tr><th>英文（填进 tag）</th><th>中文</th><th className="recipe-col-num">占比</th><th className="recipe-col-num">概率</th><th /></tr></thead><tbody>
          {slot.values.map(value => <tr key={value.id}>
            <td><input value={value.tag} spellCheck={false} onChange={event => setValue(slot.id, value.id, v => { v.tag = event.target.value })} /></td>
            <td><input value={value.label ?? ''} placeholder={glossTag(recipe, value.tag) ?? ''} onChange={event => setValue(slot.id, value.id, v => { v.label = event.target.value })} /></td>
            <td className="recipe-col-num"><input type="number" min={0.001} step="any" value={value.weight} onChange={event => { const w = Number(event.target.value); if (w > 0) setValue(slot.id, value.id, v => { v.weight = w }) }} /></td>
            <td className="recipe-col-num recipe-muted">{total ? (value.weight / total * 100).toFixed(1) : 0}%</td>
            <td className="recipe-col-action"><button className="icon-button danger" type="button" aria-label="删除取值" disabled={slot.values.length <= 1}
              onClick={() => history.change(draft => { const s = draft.slots!.find(item => item.id === slot.id)!; s.values = s.values.filter(v => v.id !== value.id) })}><Trash2 size={13} /></button></td>
          </tr>)}
        </tbody></table>
        <button className="text-action recipe-add" type="button" onClick={() => history.change(draft => { const s = draft.slots!.find(item => item.id === slot.id)!; s.values.push({ id: newId('value', s.values.map(v => v.id)), tag: '', label: '', weight: 1 }) })}>
          <Plus size={13} aria-hidden="true" /> 新增取值</button>
      </section>
    })}
    {!recipe.slots?.length && <p className="recipe-empty">还没有属性槽。</p>}
  </div>
}

function RegionsTab({ history }: { history: History }) {
  const { recipe } = history
  const regions = recipe.regions ?? DEFAULT_REGIONS
  const [bindTag, setBindTag] = useState('')
  const [bindRegion, setBindRegion] = useState('eyes')
  return <div className="recipe-page">
    <div className="recipe-section-head"><h3>部位</h3>
      <button className="secondary small" type="button" onClick={() => {
        const label = window.prompt('新部位名称，例如 尾巴', '')
        if (!label) return
        history.change(draft => { draft.regions = [...(draft.regions ?? clone(DEFAULT_REGIONS)), { id: newId('region', (draft.regions ?? []).map(r => r.id)), label, parent: 'person' }] })
      }}><Plus size={13} aria-hidden="true" /> 新增部位</button></div>
    <p className="recipe-help">选项可以「隐藏部位」，需要这个部位的分区和选项就会跳过。隐藏上级时下级一起隐藏，例如隐藏「人物」等于全部隐藏。</p>
    <table className="recipe-table"><thead><tr><th>名称</th><th>属于</th><th className="recipe-col-id">ID</th><th /></tr></thead><tbody>
      {regions.map(region => <tr key={region.id}>
        <td><input value={region.label ?? ''} onChange={event => history.change(draft => { (draft.regions ??= clone(DEFAULT_REGIONS)).find(r => r.id === region.id)!.label = event.target.value })} /></td>
        <td><select value={region.parent ?? ''} onChange={event => history.change(draft => { (draft.regions ??= clone(DEFAULT_REGIONS)).find(r => r.id === region.id)!.parent = event.target.value || null })}>
          <option value="">（顶层）</option>{regions.filter(r => r.id !== region.id).map(r => <option key={r.id} value={r.id}>{r.label || r.id}</option>)}</select></td>
        <td className="recipe-col-id recipe-id">{region.id}</td>
        <td className="recipe-col-action"><button className="icon-button danger" type="button" aria-label="删除部位" onClick={() => history.change(draft => { draft.regions = (draft.regions ?? clone(DEFAULT_REGIONS)).filter(r => r.id !== region.id) })}><Trash2 size={13} /></button></td>
      </tr>)}
    </tbody></table>

    <div className="recipe-section-head"><h3>画风 tag 绑定部位</h3></div>
    <p className="recipe-help">部位看不见时，从这一条的画风里自动删掉这些 tag，例如背面或远景时删掉 detailed eyes。</p>
    <table className="recipe-table"><thead><tr><th>画风 tag</th><th>需要部位</th><th /></tr></thead><tbody>
      {(recipe.style_tags ?? []).map((binding, index) => <tr key={index}>
        <td><code>{binding.tag}</code></td>
        <td><select value={binding.needs} onChange={event => history.change(draft => { draft.style_tags![index].needs = event.target.value })}>
          {regions.map(r => <option key={r.id} value={r.id}>{r.label || r.id}</option>)}</select></td>
        <td className="recipe-col-action"><button className="icon-button danger" type="button" aria-label="删除" onClick={() => history.change(draft => { draft.style_tags = draft.style_tags!.filter((_, i) => i !== index) })}><Trash2 size={13} /></button></td>
      </tr>)}
      <tr><td><input value={bindTag} placeholder="例如 detailed eyes" onChange={event => setBindTag(event.target.value)} /></td>
        <td><select value={bindRegion} onChange={event => setBindRegion(event.target.value)}>{regions.map(r => <option key={r.id} value={r.id}>{r.label || r.id}</option>)}</select></td>
        <td className="recipe-col-action"><button className="secondary small" type="button" disabled={!bindTag.trim()} onClick={() => {
          history.change(draft => { draft.style_tags = [...(draft.style_tags ?? []), { tag: bindTag.trim(), needs: bindRegion }] }); setBindTag('')
        }}>添加</button></td></tr>
    </tbody></table>

    <div className="recipe-section-head"><h3>资源</h3></div>
    <p className="recipe-help">有容量的东西，例如 hands = 2：双手动作占 2，单手动作占 1，占满后不再抽手部动作。</p>
    <KeyValueField value={Object.fromEntries(Object.entries(recipe.resources ?? {}).map(([k, v]) => [k, String(v)]))} keyPlaceholder="资源名，如 hands" valuePlaceholder="容量"
      onChange={value => history.change(draft => { draft.resources = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, Math.max(1, Math.min(100, Number(v) || 1))])) })} />

    <div className="recipe-section-head"><h3>状态的中文名</h3></div>
    <p className="recipe-help">只影响显示，例如把 pose 显示成「姿势」。</p>
    <KeyValueField value={recipe.states ?? {}} keyPlaceholder="状态" valuePlaceholder="中文名，如 姿势"
      onChange={value => history.change(draft => { draft.states = value })} keys={stateKeys(recipe)} />
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

  return <div className="recipe-page">
    <div className="recipe-section-head"><h3>翻译</h3></div>
    <p className="recipe-help">中文只用于显示，不会发给模型，也不进 caption。会先看选项自己的中文名，再看这里的词典，最后看内置词典。</p>
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
    <div className="recipe-section-head"><h3>未翻译（{missing.length}）</h3></div>
    {!missing.length && <p className="recipe-empty">全部都有中文了。</p>}
    <ul className="recipe-missing">{missing.map(tag => <MissingRow key={tag} tag={tag} onSave={zh => setGloss(tag, zh)} onSearch={() => void search(tag, tag)} />)}</ul>
    <div className="recipe-section-head"><h3>配方词典（{Object.keys(recipe.glossary ?? {}).length}）</h3></div>
    <ul className="recipe-missing">{Object.entries(recipe.glossary ?? {}).map(([tag, zh]) => <li key={tag}><code>{tag}</code> {zh}
      <button className="text-action" type="button" onClick={() => history.change(draft => { const g = { ...(draft.glossary ?? {}) }; delete g[tag]; draft.glossary = g })}>删除</button></li>)}</ul>
  </div>
}

function MissingRow({ tag, onSave, onSearch }: { tag: string; onSave: (zh: string) => void; onSearch: () => void }) {
  const [text, setText] = useState('')
  return <li><code>{tag}</code>
    <input value={text} placeholder="输入中文" maxLength={100} onChange={event => setText(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && text.trim()) onSave(text.trim()) }} />
    <button className="text-action" type="button" disabled={!text.trim()} onClick={() => onSave(text.trim())}>保存</button>
    <button className="text-action" type="button" onClick={onSearch}><Search size={12} aria-hidden="true" /> 查找</button>
  </li>
}

function JsonTab({ history, name, setName }: { history: History; name: string; setName: (name: string) => void }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const file = useRef<HTMLInputElement>(null)

  function exportJson() {
    downloadJson({ name, recipe: history.recipe }, `${name || 'recipe'}.recipe.json`)
  }

  function importJson(raw: string) {
    try {
      const parsed = JSON.parse(raw) as { name?: string; recipe?: Recipe } | Recipe
      if ('format' in parsed && parsed.format === 'nai-recipe-partitions') throw new Error('这是分区文件，请用下面的「导入分区」。')
      const recipe = 'recipe' in parsed && parsed.recipe ? parsed.recipe : parsed as Recipe
      if (!Array.isArray(recipe.partitions) || !Array.isArray(recipe.draw_order)) throw new Error('不是配方 JSON：缺少 partitions 或 draw_order。')
      history.change(draft => { Object.keys(draft).forEach(key => delete (draft as unknown as Record<string, unknown>)[key]); Object.assign(draft, recipe) })
      if ('name' in parsed && typeof parsed.name === 'string') setName(parsed.name)
      setError('')
      setText('')
    } catch (failure) { setError(failure instanceof Error ? failure.message : '无法解析 JSON。') }
  }

  return <div className="recipe-page">
    <div className="recipe-section-head"><h3>导入导出</h3></div>
    <p className="recipe-help">导出 JSON 可以备份或分享给别的账号。导入会替换当前配方（可撤销），保存时服务器会完整检查。</p>
    <div className="recipe-toolbar">
      <button className="secondary" type="button" onClick={exportJson}><Download size={13} aria-hidden="true" /> 导出 JSON</button>
      <input ref={file} type="file" accept=".json,application/json" hidden onChange={async event => { const f = event.target.files?.[0]; if (f) importJson(await f.text()); event.target.value = '' }} />
      <button className="secondary" type="button" onClick={() => file.current?.click()}><FileUp size={13} aria-hidden="true" /> 从文件导入</button>
    </div>
    <textarea rows={12} value={text} spellCheck={false} placeholder="或粘贴配方 JSON" onChange={event => setText(event.target.value)} />
    <button className="text-action" type="button" disabled={!text.trim()} onClick={() => importJson(text)}>导入粘贴的 JSON（替换当前配方）</button>
    {error && <p className="alert" role="alert">{error}</p>}
    <PartitionTransfer history={history} name={name} />
  </div>
}

function downloadJson(data: unknown, fileName: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = Object.assign(document.createElement('a'), { href: url, download: fileName })
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function exportPartitionFile(recipe: Recipe, ids: readonly string[], name: string) {
  const bundle = exportPartitions(recipe, ids)
  downloadJson(bundle, bundleFileName(name, bundle))
}

const ACTION_LABELS: Record<PartitionAction, string> = { add: '添加', replace: '替换现有分区', copy: '作为副本添加', skip: '跳过' }

/** Partition-level export and import: only the chosen partitions are added or replaced. */
function PartitionTransfer({ history, name }: { history: History; name: string }) {
  const { recipe } = history
  const [selected, setSelected] = useState<string[]>([])
  const [source, setSource] = useState<PartitionBundle | null>(null)
  const [actions, setActions] = useState<Record<string, PartitionAction | ''>>({})
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const file = useRef<HTMLInputElement>(null)
  const ordered = [...new Set([...recipe.draw_order, ...recipe.partitions.map(part => part.id)])]
    .map(id => recipe.partitions.find(part => part.id === id)).filter((part): part is Partition => Boolean(part))
  const live = selected.filter(id => recipe.partitions.some(part => part.id === id))
  const conflicts = source ? conflictingPartitions(recipe, source) : new Set<string>()
  const undecided = source ? source.partitions.filter(part => actions[part.id] === '' || actions[part.id] === undefined) : []
  const plan = useMemo(() => source && !undecided.length ? planPartitionImport(recipe, source, actions as Record<string, PartitionAction>) : null,
    [recipe, source, actions, undecided.length])
  const count = source ? source.partitions.filter(part => actions[part.id] && actions[part.id] !== 'skip').length : 0

  function load(raw: string) {
    try {
      const bundle = parsePartitionSource(raw)
      const clash = conflictingPartitions(recipe, bundle)
      setActions(Object.fromEntries(bundle.partitions.map(part => [part.id, clash.has(part.id) ? '' : 'add'])))
      setSource(bundle)
      setError('')
      setMessage('')
    } catch (failure) { setError(failure instanceof Error ? failure.message : '无法解析 JSON。') }
  }

  function apply() {
    if (!source || !plan || !count) return
    const chosen = actions as Record<string, PartitionAction>
    history.change(draft => {
      const next = planPartitionImport(draft, source, chosen).recipe
      Object.keys(draft).forEach(key => delete (draft as unknown as Record<string, unknown>)[key])
      Object.assign(draft, next)
    })
    setMessage(`已导入 ${count} 个分区${plan.notes.length ? `，并处理了 ${plan.notes.length} 处引用` : ''}（可撤销）。保存时服务器会完整检查。`)
    setSource(null)
    setText('')
  }

  return <section className="recipe-partition-transfer">
    <div className="recipe-section-head"><h3>分区导入导出</h3></div>
    <p className="recipe-help">只导出或导入选中的分区，不影响配方中的其他分区。导出文件会带上这些分区用到的取值槽、部位、资源、状态名和中文释义；导入时只补充当前配方缺少的这些定义，不会覆盖已有的。</p>
    <ul className="recipe-ref-list">{ordered.map(part => <li key={part.id}><label className="recipe-check">
      <input type="checkbox" checked={live.includes(part.id)} onChange={event => setSelected(current => event.target.checked ? [...current, part.id] : current.filter(id => id !== part.id))} />
      {part.label || part.id} <span className="recipe-help">（{part.id}，{part.options.length} 个选项）</span></label></li>)}</ul>
    <div className="recipe-toolbar">
      <button className="text-action" type="button" onClick={() => setSelected(live.length === ordered.length ? [] : ordered.map(part => part.id))}>{live.length === ordered.length ? '全不选' : '全选'}</button>
      <button className="secondary" type="button" disabled={!live.length} onClick={() => exportPartitionFile(recipe, live, name)}><Download size={13} aria-hidden="true" /> 导出所选 {live.length} 个分区</button>
      <input ref={file} type="file" accept=".json,application/json" hidden onChange={async event => { const f = event.target.files?.[0]; if (f) load(await f.text()); event.target.value = '' }} />
      <button className="secondary" type="button" onClick={() => file.current?.click()}><FileUp size={13} aria-hidden="true" /> 从文件导入分区</button>
    </div>
    <textarea rows={6} value={text} spellCheck={false} placeholder="或粘贴分区 JSON；也可以粘贴整个配方 JSON，再挑选其中的分区" onChange={event => setText(event.target.value)} />
    <button className="text-action" type="button" disabled={!text.trim()} onClick={() => load(text)}>读取粘贴的 JSON</button>
    {error && <p className="alert" role="alert">{error}</p>}
    {message && <p className="recipe-help" role="status">{message}</p>}
    {source && <div className="recipe-form">
      <p className="recipe-help">文件中有 {source.partitions.length} 个分区。新分区加到抽取顺序末尾；替换的分区保留原来的位置。{conflicts.size ? `其中 ${conflicts.size} 个与当前配方的分区 id 相同，请逐个选择处理方式。` : ''}</p>
      <ul className="recipe-ref-list">{source.partitions.map(part => {
        const clash = conflicts.has(part.id)
        const current = recipe.partitions.find(item => item.id === part.id)
        return <li key={part.id}>
          <strong>{part.label || part.id}</strong> <span className="recipe-help">（{part.id}，{part.options.length} 个选项{clash ? `；当前配方已有「${current?.label || part.id}」，${current?.options.length ?? 0} 个选项` : ''}）</span>
          <select value={actions[part.id] ?? ''} aria-label={`导入分区 ${part.id} 的方式`} onChange={event => setActions(value => ({ ...value, [part.id]: event.target.value as PartitionAction | '' }))}>
            {clash && <option value="" disabled>请选择</option>}
            {(clash ? ['replace', 'copy', 'skip'] as const : ['add', 'skip'] as const).map(action => <option key={action} value={action}>{ACTION_LABELS[action]}</option>)}
          </select>
        </li>
      })}</ul>
      {undecided.length > 0 && <p className="recipe-help">还有 {undecided.length} 个同 id 分区未选择处理方式。</p>}
      {plan && plan.notes.length > 0 && <>
        <p className="recipe-help">导入时将自动处理以下 {plan.notes.length} 处：</p>
        <ul className="recipe-ref-list">{plan.notes.map((note, index) => <li key={index}>{note}</li>)}</ul>
      </>}
      <div className="recipe-toolbar">
        <button className="secondary" type="button" disabled={!plan || !count} onClick={apply}>导入 {count} 个分区</button>
        <button className="text-action" type="button" onClick={() => { setSource(null); setActions({}) }}>取消</button>
      </div>
    </div>}
  </section>
}

// ------------------------------------------------------------------ sampling

function SamplePanel({ api, open, recipe, style, recipeRef, saved, onGenerate }: {
  api: WorkspaceApi; open: boolean; recipe: Recipe; style: string; recipeRef: { id: string; name: string }; saved: boolean; onGenerate: (result: RecipeDraftResult) => void
}) {
  const [n, setN] = useState('100')
  const [seed, setSeed] = useState(() => String(Math.floor(Math.random() * 4294967295)))
  const [sampled, setSampled] = useState<{ key: string; result: SampleResult } | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const cached = useRef<{ key: string; result: SampleResult } | null>(null)
  const pending = useRef<{ key: string; controller: AbortController } | null>(null)
  const adding = useRef(false)
  const mounted = useRef(false)
  const count = Number(n)
  const seedValue = Number(seed)
  const seedValid = seed.trim() !== '' && Number.isInteger(seedValue) && seedValue >= 0 && seedValue <= 4294967295
  const valid = Number.isInteger(count) && count >= 1 && count <= MAX_DATASET_ITEMS && seedValid
  const key = JSON.stringify({ recipe, count, seed: seedValue, recipeRef, open })
  const latestKey = useRef(key)
  latestKey.current = key
  const result = sampled?.key === key ? sampled.result : null
  const busy = busyKey === key
  const error = failure?.key === key ? failure.message : ''

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => () => {
    if (pending.current?.key === key) {
      pending.current.controller.abort()
      pending.current = null
      if (mounted.current) setBusyKey(current => current === key ? null : current)
    }
    if (cached.current?.key === key) cached.current = null
  }, [key])

  async function run(): Promise<SampleResult | null> {
    if (!mounted.current || !open || !valid || pending.current?.key === key) return null
    if (cached.current?.key === key) return cached.current.result
    pending.current?.controller.abort()
    const request = { key, controller: new AbortController() }
    pending.current = request
    setFailure(null)
    setBusyKey(key)
    try {
      // Quotas depend on the complete batch size. Preview the same batch that
      // will be appended, then keep it so generating never silently resamples.
      const next = await api.sampleRecipe(recipe, count, seedValue, request.controller.signal)
      if (!mounted.current || pending.current !== request || latestKey.current !== key) return null
      cached.current = { key, result: next }
      setSampled(cached.current)
      return next
    } catch (failure) {
      if (mounted.current && pending.current === request && latestKey.current === key && !request.controller.signal.aborted) {
        setFailure({ key, message: errorText(failure) })
      }
      return null
    } finally {
      if (pending.current === request) {
        pending.current = null
        if (mounted.current) setBusyKey(null)
      }
    }
  }

  async function generate(replace: boolean) {
    if (adding.current) return
    adding.current = true
    try {
      const next = await run()
      if (next && mounted.current && latestKey.current === key) onGenerate({ items: next.items, recipe: recipeRef, replace })
    } finally { adding.current = false }
  }

  return <aside className="recipe-sample" aria-label="预览与生成">
    <h3><Dices size={15} aria-hidden="true" /> 预览与生成</h3>
    <div className="recipe-sample-form">
      <label><span>生成条数</span><input type="number" min={1} max={MAX_DATASET_ITEMS} value={n} onChange={event => setN(event.target.value)} /></label>
    </div>
    <details className="recipe-advanced">
      <summary>高级参数</summary>
      <label><span>抽取种子（只决定抽到哪些训练词，不影响图片；每张图的种子由服务器另行随机）</span><span className="recipe-seed"><input type="number" min={0} max={4294967295} value={seed} onChange={event => setSeed(event.target.value)} />
        <button className="icon-button" type="button" title="换一个种子" aria-label="换一个抽取种子" onClick={() => setSeed(String(Math.floor(Math.random() * 4294967295)))}><Dices size={14} /></button></span></label>
      <p className="recipe-help">同一配方、种子和条数，每次抽到的训练词都一样；填回原来的种子可以复现同一批。</p>
    </details>
    {!seedValid && <p className="alert" role="alert">高级参数中的抽取种子需要是 0–4294967295 的整数。</p>}
    <p className="recipe-help">预览按完整条数抽取，展示前 20 条；加入列表使用这批相同的结果。预览不会调用 NovelAI，不花 Anlas。</p>
    <div className="recipe-sample-actions">
      <button className="secondary" type="button" disabled={busy || !valid} onClick={() => void run()}>先预览 {Math.min(count || 20, 20)} 条</button>
      <button className="primary" type="button" disabled={busy || !valid} onClick={() => void generate(false)}>生成 {valid ? count : ''} 条，加到列表</button>
      <button className="text-action" type="button" disabled={busy || !valid} onClick={() => { if (window.confirm('清空训练集列表，换成这次生成的条目？')) void generate(true) }}>生成并替换整个列表</button>
    </div>
    {!saved && <p className="recipe-help warn">配方还没保存。没关系，也能预览和生成；保存后以后更好对照。</p>}
    {error && <p className="alert" role="alert">{error}</p>}
    {result ? <SampleView recipe={recipe} result={result} style={style} /> : <p className="recipe-empty">点「先预览」看看会生成什么。</p>}
  </aside>
}

function SampleView({ recipe, result, style }: { recipe: Recipe; result: SampleResult; style: string }) {
  const { stats } = result
  const [view, setView] = useState<'items' | 'stats'>('items')
  const slotValue = (slotId: string, valueId: string) => recipe.slots?.find(s => s.id === slotId)?.values.find(v => v.id === valueId)?.label || valueId
  return <div className="recipe-sample-view">
    <div className="recipe-segment" role="tablist">
      <button type="button" className={view === 'items' ? 'active' : ''} onClick={() => setView('items')}>条目（{stats.produced}/{stats.requested}）</button>
      <button type="button" className={view === 'stats' ? 'active' : ''} onClick={() => setView('stats')}>占比统计</button>
    </div>
    {(stats.overflow > 0 || stats.stale_dependency > 0 || stats.warnings.length > 0) && <div className="recipe-notice">
      {stats.overflow > 0 && <p>{stats.overflow} 条提示词为空或超过 1000 字符，已丢弃。</p>}
      {stats.stale_dependency > 0 && <p>{stats.stale_dependency} 条有失效的依赖，建议调整抽取顺序。</p>}
      {stats.warnings.map(text => <p key={text}>{text}</p>)}
    </div>}
    {view === 'items' && <>
      <p className="recipe-help">已生成 {stats.produced} / {stats.requested} 条，下面展示前 {Math.min(20, result.items.length)} 条；加入列表会加入全部 {result.items.length} 条。</p>
      <ol className="recipe-preview-items">{result.items.slice(0, 20).map((item, index) => {
      const notes = item.draws.filter(draw => draw.partition === '-rule' || draw.option === '-removed' || draw.option === '-skip' || draw.partition === '-meta')
      const edits = item.style_edits
      return <li key={item.id}>
        <span className="recipe-preview-index">{index + 1}</span>
        <div>
          <p className="recipe-preview-prompt">{item.prompt}</p>
          {(edits.add.length > 0 || edits.remove.length > 0) && <p className="recipe-style-edit">画风 {edits.add.map(tag => <b key={`a${tag}`} className="add">+ {tag}</b>)}{edits.remove.map(tag => <b key={`r${tag}`} className="remove">− {tag}</b>)}
            {style.trim() && <span className="recipe-muted" title={previewStyle(style, edits)}>实际发送的画风：{previewStyle(style, edits) || '（空）'}</span>}</p>}
          {notes.length > 0 && <p className="recipe-preview-notes">{notes.map((draw, i) => <span key={i}>{draw.label}</span>)}</p>}
        </div>
      </li>
    })}</ol></>}
    {view === 'stats' && <div className="recipe-stats-list">
      <p className="recipe-help">「目标」是按占比算出的期望，「实际」按该分区实际抽取次数计算，不计入因不可见或条件不满足而跳过的条目；偏差超过 5 个百分点时标黄。</p>
      {stats.partitions.map(part => {
        const total = part.options.reduce((sum, option) => sum + option.count, 0)
        const skips = Object.entries(part.skips)
        return <details key={part.partition} className="recipe-stat">
          <summary><span>{part.label || part.partition}</span><small>{total} 次{skips.length ? ` · 跳过 ${skips.reduce((sum, [, v]) => sum + v, 0)}` : ''}</small></summary>
          {skips.length > 0 && <p className="recipe-muted">跳过原因：{skips.map(([reason, value]) => `${SKIP_REASONS[reason] ?? reason} ${value}`).join('、')}</p>}
          {part.quota_misses > 0 && <p className="warn">有 {part.quota_misses} 条未满足分配的配额，请检查条件或后续移除规则。</p>}
          <table className="recipe-table"><thead><tr><th>选项</th><th className="recipe-col-num">目标</th><th className="recipe-col-num">实际</th><th className="recipe-col-num">次数</th></tr></thead>
            <tbody>{part.options.map(option => {
              const actual = total ? option.count / total : 0
              const off = total > 0 && Math.abs(actual - option.target) > 0.05
              return <tr key={option.option} className={off ? 'off' : ''}><td>{option.label}</td><td className="recipe-col-num">{(option.target * 100).toFixed(1)}%</td><td className="recipe-col-num">{(actual * 100).toFixed(1)}%</td><td className="recipe-col-num">{option.count}</td></tr>
            })}</tbody></table>
          {Object.entries(part.values).map(([slot, values]) => <p key={slot} className="recipe-muted">{recipe.slots?.find(s => s.id === slot)?.label || slot}：{Object.entries(values).map(([value, c]) => `${slotValue(slot, value)} ${c}`).join('、')}</p>)}
        </details>
      })}
      {Object.keys(stats.rules).length > 0 && <p className="recipe-muted">规则命中：{Object.entries(stats.rules).map(([id, c]) => `${recipe.rules?.find(r => r.id === id)?.label || id} ${c}`).join('、')}</p>}
      {Object.keys(stats.style_removed).length > 0 && <p className="recipe-muted">画风删除：{Object.entries(stats.style_removed).map(([tag, c]) => `${tag} ${c}`).join('、')}</p>}
      {Object.keys(stats.style_added).length > 0 && <p className="recipe-muted">画风追加：{Object.entries(stats.style_added).map(([tag, c]) => `${tag} ${c}`).join('、')}</p>}
    </div>}
  </div>
}

export function RecipeHint({ children }: { children: ReactNode }) {
  return <p className="prompt-hint">{children}</p>
}
