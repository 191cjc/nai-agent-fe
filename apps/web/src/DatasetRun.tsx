import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { observer } from 'mobx-react-lite'
import { Download, FileUp, Layers, Plus, RotateCcw, Shuffle, Trash2, Upload, UserRound, X } from 'lucide-react'
import { ApiFailure, errorText, MAX_EXPERIMENT_NAME, type GenerationView, type WorkspaceApi } from './api'
import { characterCategories, type CharacterMode } from './character-prompts'
import { CUSTOM_CATEGORY, MAX_DATASET_ITEMS, MAX_DATASET_PROMPT_LENGTH, RECIPE_CATEGORY, SHAPE_LABELS, datasetItemText, datasetItems, itemShape, markEdited, nextCustomId, type DatasetCategory, type DatasetEntry, type ItemShape } from './dataset-run'
import { previewStyle } from './recipe'
import { RecipeEditor, type RecipeDraftResult } from './RecipeEditor'
import { translatePrompt } from './prompt-zh'
import { supportsNativeCharacters } from './store'
import { defaultCharacterEntries, defaultDatasetEntries } from './dataset-defaults'
import { ANIMAGINE_QUALITY_PREFIX, NOOBAI_QUALITY_PREFIX, buildDatasetZip, downloadZip, experimentJobs, selectedJobs, type DatasetExportProgress } from './dataset-export'
import { CharacterRunSettings, characterSnapshotSummary, useCharacterSettings } from './CharacterDataset'
import { downloadText, formatPrompts, parsePrompts } from './prompt-io'
import type { GenerationStore } from './store'

const CUSTOM: DatasetCategory = { id: CUSTOM_CATEGORY, label: '自定义', description: '手动添加的提示词' }
const RECIPE: DatasetCategory = { id: RECIPE_CATEGORY, label: '随机配方', description: '由随机配方生成；下方灰字为抽到的分区与规则，可按它们在缩略图中筛选' }

// Body-shape and suggestive tags must never be applied to child subjects.
const CHILD_UNSAFE_STYLE = /\b(soft body|supple skin|soft curves|curvy|curvaceous|cleavage|breasts?|skin folds|skin compression|thick thighs|wide hips|sexy|seductive|sensual|erotic|nsfw|lewd|plump|voluptuous|navel|midriff|bare shoulders|thighs)\b/i

const CHILD_CATEGORIES: Record<string, string> = { boy: '男孩（年幼）', girl: '女孩（年幼）' }

const isChild = (entry: DatasetEntry) => entry.draws?.some(draw => draw.partition === '-meta' && draw.option === 'child') ?? false

function childSafetyError(entries: readonly DatasetEntry[], style: string): string {
  const chosen = Object.keys(CHILD_CATEGORIES).filter(category => entries.some(entry => entry.selected && entry.category === category))
  const match = chosen.length ? style.match(CHILD_UNSAFE_STYLE) : null
  if (match) {
    const names = chosen.map(category => `「${CHILD_CATEGORIES[category]}」`).join('、')
    return `已选${names}条目，但画风中含有身体描写类标签「${match[0]}」。这类标签绝不能用于年幼角色：请取消这些条目，或改用去掉身体描写的画风单独批跑。`
  }
  // Recipe items: check each child item's own resolved style (pool style plus its edits).
  for (const entry of entries) {
    if (!entry.selected || !isChild(entry)) continue
    const unsafe = previewStyle(style, entry.styleEdits).match(CHILD_UNSAFE_STYLE)
    if (unsafe) return `条目 ${entry.id} 是儿童条目，但它的画风中含有身体描写类标签「${unsafe[0]}」。这类标签绝不能用于年幼角色：请删除这些条目或修改画风。`
  }
  return ''
}

function validationError(entries: readonly DatasetEntry[], styles: readonly string[], traits?: string, nativeCharacters?: boolean): string {
  try {
    datasetItems(entries, styles, traits, nativeCharacters)
    return ''
  } catch (error) {
    return error instanceof Error ? error.message : '训练集提示词无效。'
  }
}

/** Category/item picker shared by the style and character libraries. */
export function PromptLibrary({ entries, setEntries, categories, defaults, placeholder, name, allowCharacters, showShape = false }: {
  entries: DatasetEntry[]
  setEntries: Dispatch<SetStateAction<DatasetEntry[]>>
  categories: readonly DatasetCategory[]
  defaults: () => DatasetEntry[]
  placeholder: string
  /** Library name for the export title and file name, e.g. 画风训练集. */
  name: string
  /** Style libraries accept multi-person 「人物：」 lines; character libraries do not. */
  allowCharacters: boolean
  /** Show each item's automatic canvas shape (竖图 / 方图 / 横图) beside its translation. */
  showShape?: boolean
}) {
  const [custom, setCustom] = useState('')
  const [importing, setImporting] = useState(false)
  const [importText, setImportText] = useState('')
  const [importMessage, setImportMessage] = useState('')
  const [importError, setImportError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const selectedEntries = entries.filter(entry => entry.selected)

  function update(id: string, change: Partial<DatasetEntry>) {
    setEntries(current => current.map(entry => entry.id === id ? { ...entry, ...change } : entry))
  }

  function selectCategory(category: string, value: boolean) {
    setEntries(current => current.map(entry => entry.category === category ? { ...entry, selected: value } : entry))
  }

  function addCustom() {
    const prompt = custom.trim()
    if (!prompt) return
    setEntries(current => [...current, { id: nextCustomId(current), category: CUSTOM_CATEGORY, prompt, selected: true }])
    setCustom('')
  }

  function importPrompts(replace: boolean) {
    setImportMessage('')
    try {
      const { entries: parsed, multi } = parsePrompts(importText, replace ? [] : entries, categories.map(category => category.id), allowCharacters)
      if (replace && !window.confirm(`用导入的 ${parsed.length} 条替换整个列表？当前列表（含内置条目和编辑内容）将被清空，可用「恢复默认」找回内置库。`)) return
      setEntries(current => replace ? parsed : [...current, ...parsePrompts(importText, current, categories.map(category => category.id), allowCharacters).entries])
      setImportError('')
      setImportText('')
      setImporting(false)
      setImportMessage(`已${replace ? '替换为' : '追加'} ${parsed.length} 条提示词${multi ? `（其中多人条目 ${multi} 条）` : ''}，均已勾选。`)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : '导入失败。')
    }
  }

  async function readFile(files: FileList | null) {
    const file = files?.[0]
    if (fileInput.current) fileInput.current.value = ''
    if (!file) return
    if (file.size > 2 * 1024 * 1024) { setImportError('文件超过 2 MB，请拆分后再导入。'); return }
    setImportText(await file.text())
    setImportError('')
  }

  function exportPrompts() {
    const date = new Date().toISOString().slice(0, 10).replaceAll('-', '')
    downloadText(formatPrompts(selectedEntries, `${name}提示词（${selectedEntries.length} 条已选）`), `${name}提示词-${date}.txt`)
    setImportMessage(`已导出 ${selectedEntries.length} 条已选提示词。`)
  }

  return <>
    <fieldset className="dataset-categories">
      <legend>按分类选择</legend>
      {[...categories, RECIPE, CUSTOM].map(category => {
        const members = entries.filter(entry => entry.category === category.id)
        if (!members.length) return null
        const count = members.filter(entry => entry.selected).length
        return <details className="dataset-category" key={category.id}>
          <summary>
            <input type="checkbox" checked={count === members.length} aria-label={`选择全部「${category.label}」`}
              ref={input => { if (input) input.indeterminate = count > 0 && count < members.length }}
              onClick={event => event.stopPropagation()} onChange={event => selectCategory(category.id, event.target.checked)} />
            <strong>{category.label}</strong><span>{count} / {members.length}</span>
            <span className="prompt-hint">{category.description}</span>
          </summary>
          <ul className="dataset-items">{members.map(entry => <li key={entry.id} className={entry.selected ? '' : 'muted'}>
            <input type="checkbox" checked={entry.selected} aria-label={`选择提示词 ${entry.id}`}
              onChange={event => update(entry.id, { selected: event.target.checked })} />
            <div className="dataset-item-fields">
              <input type="text" value={entry.prompt} maxLength={MAX_DATASET_PROMPT_LENGTH} spellCheck={false} aria-label={`编辑提示词 ${entry.id}`}
                title={entry.characters?.length ? '共享场景：人数、构图、动作与背景' : undefined}
                onChange={event => setEntries(current => current.map(item => item.id === entry.id ? markEdited(item, event.target.value) : item))} />
              <span className="dataset-item-zh">{showShape && <b>{SHAPE_LABELS[entry.shape ?? itemShape(entry.prompt, entry.characters)]}</b>}{translatePrompt(entry.prompt)}</span>
              {entry.draws && <DrawSummary entry={entry} />}
              {entry.characters?.map((character, person) => <label key={person} className="dataset-item-person"><span>人物 {person + 1}</span>
                <input type="text" value={character} maxLength={MAX_DATASET_PROMPT_LENGTH} spellCheck={false} aria-label={`编辑提示词 ${entry.id} 的人物 ${person + 1}`}
                  onChange={event => update(entry.id, { characters: entry.characters?.map((value, index) => index === person ? event.target.value : value) })} />
                <span className="dataset-item-zh">{translatePrompt(character)}</span></label>)}
            </div>
            <button className="icon-button" type="button" title="移除这条提示词" aria-label={`移除提示词 ${entry.id}`}
              onClick={() => setEntries(current => current.filter(item => item.id !== entry.id))}><Trash2 size={14} /></button>
          </li>)}</ul>
        </details>
      })}
    </fieldset>
    <div className="dataset-custom">
      <input type="text" value={custom} maxLength={MAX_DATASET_PROMPT_LENGTH} spellCheck={false} placeholder={placeholder}
        aria-label="自定义提示词" onChange={event => setCustom(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); addCustom() } }} />
      <button className="secondary" type="button" disabled={!custom.trim()} onClick={addCustom}><Plus size={14} aria-hidden="true" /> 添加</button>
      <button className="text-action" type="button" onClick={() => { if (window.confirm('恢复为内置提示词库？自定义和编辑内容将丢失。')) setEntries(defaults()) }}>
        <RotateCcw size={14} aria-hidden="true" /> 恢复默认</button>
      <button className="text-action" type="button" aria-expanded={importing} onClick={() => { setImporting(value => !value); setImportError('') }}>
        <Upload size={14} aria-hidden="true" /> 批量导入</button>
      <button className="text-action" type="button" disabled={!selectedEntries.length} onClick={exportPrompts}
        title="把已勾选的提示词导出为文本文件，可编辑后再导入"><Download size={14} aria-hidden="true" /> 导出已选</button>
    </div>
    {importing && <div className="dataset-import">
      <label className="field"><span>每行一条提示词{allowCharacters ? '；多人条目在场景行下面逐行写「人物：…」' : ''}；# 开头的行忽略，「# 分类：id」可指定分类</span>
        <textarea value={importText} rows={8} spellCheck={false} aria-label="批量导入的提示词"
          placeholder={allowCharacters
            ? '1girl, solo, portrait, smile, long hair, black hair, brown eyes, white shirt\n2girls, upper body, friends, classroom\n人物：girl, long hair, black hair, brown eyes, navy blue blazer\n人物：girl, short hair, blonde hair, blue eyes, white cardigan'
            : 'portrait, smile, looking at viewer\nfull body, running, park'}
          onChange={event => { setImportText(event.target.value); setImportError('') }} /></label>
      <div className="dataset-custom">
        <input ref={fileInput} type="file" accept=".txt,text/plain" hidden onChange={event => void readFile(event.target.files)} />
        <button className="secondary" type="button" onClick={() => fileInput.current?.click()}><FileUp size={14} aria-hidden="true" /> 从文件读取</button>
        <button className="secondary" type="button" disabled={!importText.trim()} onClick={() => importPrompts(false)}><Plus size={14} aria-hidden="true" /> 追加到列表</button>
        <button className="text-action" type="button" disabled={!importText.trim()} onClick={() => importPrompts(true)}>替换整个列表</button>
        <button className="text-action" type="button" onClick={() => { setImporting(false); setImportError('') }}><X size={14} aria-hidden="true" /> 取消</button>
      </div>
      {importError && <p className="alert" role="alert">{importError}</p>}
    </div>}
    {importMessage && <p className="subtle" role="status">{importMessage}</p>}
  </>
}

type DatasetMode = 'style' | 'character'

export const DatasetRunConfig = observer(({ generation, api, hidden }: { generation: GenerationStore; api: WorkspaceApi; hidden: boolean }) => {
  const [mode, setMode] = useState<DatasetMode>('style')
  const [runName, setRunName] = useState('')
  const [entries, setEntries] = useState<DatasetEntry[]>(defaultDatasetEntries)
  const [characterEntriesByMode, setCharacterEntriesByMode] = useState<Record<CharacterMode, DatasetEntry[]>>(() => ({
    gpt: defaultCharacterEntries('gpt'), precise: defaultCharacterEntries('precise'),
  }))
  const [autoShape, setAutoShape] = useState(true)
  const [recipeOpen, setRecipeOpen] = useState(false)
  const [recipeMessage, setRecipeMessage] = useState('')
  const character = useCharacterSettings()
  const characterMode = character.settings.mode
  const characterEntries = characterEntriesByMode[characterMode]
  const setCharacterEntries: Dispatch<SetStateAction<DatasetEntry[]>> = update => setCharacterEntriesByMode(current => ({
    ...current, [characterMode]: typeof update === 'function' ? update(current[characterMode]) : update,
  }))
  const runs = generation.runs
  const snapshot = runs.kind === 'dataset' ? runs.snapshot : null
  const style = generation.draft.style_prompt
  const active = mode === 'style' ? entries : characterEntries
  const selected = active.filter(entry => entry.selected)
  const gptMode = mode === 'character' && character.settings.mode === 'gpt'
  const shapes = autoShape
  const shapeCounts = shapes ? selected.reduce<Record<ItemShape, number>>((counts, entry) => {
    counts[entry.shape ?? itemShape(entry.prompt, entry.characters)] += 1
    return counts
  }, { portrait: 0, square: 0, landscape: 0 }) : null
  const sampleText = gptMode ? character.settings.gptSamples : generation.draft.sample_count
  const samples = /^\d+$/.test(sampleText) ? Number(sampleText) : null
  const error = !selected.length ? '' : mode === 'style'
    ? childSafetyError(entries, style) || validationError(entries, [style], '', supportsNativeCharacters(generation.draft.model))
    : validationError(characterEntries, character.styles, character.settings.traits) || character.error(generation.draft.model)
  const locked = generation.operationLocked || generation.activeId !== null || generation.busy || generation.submitUncertain

  function start() {
    if (locked || error || !selected.length) return
    const started = mode === 'style'
      ? generation.startDatasetRun(entries, { name: runName, autoShape: shapes })
      : generation.startDatasetRun(characterEntries, {
        styles: character.styles, character: character.settings, gptModel: character.gpt?.gpt_image_model ?? undefined,
        gptConcurrencyMax: character.gpt?.gpt_concurrency_max ?? undefined, name: runName, autoShape: shapes,
      })
    // A queued run keeps its name; clear the field so the next set gets its own.
    void started.then(() => { if (!runs.createError && !runs.pendingId && !generation.error) setRunName('') })
  }

  const frozenCharacter = snapshot?.character && 'references' in snapshot.character ? snapshot.character : null

  function acceptRecipe(result: RecipeDraftResult) {
    setEntries(current => {
      const base = result.replace ? [] : current
      const taken = new Set(base.map(entry => entry.id))
      const added: DatasetEntry[] = result.items.map(item => {
        let id = item.id
        for (let suffix = 2; taken.has(id); suffix += 1) id = `${item.id}-${suffix}`
        taken.add(id)
        return {
          id, category: RECIPE_CATEGORY, prompt: item.prompt, selected: true, draws: item.draws,
          styleEdits: item.style_edits, recipe: result.recipe, shape: item.shape ?? null,
        }
      })
      return [...base, ...added]
    })
    setRecipeMessage(`已从配方「${result.recipe.name}」${result.replace ? '替换为' : '追加'} ${result.items.length} 条。`)
  }

  return <section id="dataset-run-config" className="style-experiment-config dataset-run-config" aria-labelledby="dataset-run-config-title" hidden={hidden}
    onKeyDown={event => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
    <h3 id="dataset-run-config-title"><Layers size={15} aria-hidden="true" /> 训练集批跑</h3>
    {!snapshot && <div className="history-mode dataset-mode" role="group" aria-label="训练集类型">
      <button type="button" className={mode === 'style' ? 'active' : ''} aria-pressed={mode === 'style'} onClick={() => setMode('style')}><Layers size={14} aria-hidden="true" /> 画风训练集</button>
      <button type="button" className={mode === 'character' ? 'active' : ''} aria-pressed={mode === 'character'} onClick={() => setMode('character')}><UserRound size={14} aria-hidden="true" /> 角色训练集</button>
    </div>}
    {mode === 'style'
      ? <p className="prompt-hint">用当前「画风」固定风格，逐条运行下面的内容提示词，生成用于训练画风 LoRA 的图片。提示词只描述内容，不含画风与质量词；导出时作为 caption。用「随机配方」按分区和占比生成条目：看不见的部位不写（半身不写鞋）、冲突自动排除、规则可按条目增删画风 tag（只发给模型，不进 caption）。也可以手动添加或批量导入。每条下方的中文只用于阅读，不会发送。</p>
      : <p className="prompt-hint">用参考图和固定的角色特征，逐条运行景别、表情、姿势、场景等内容提示词，生成用于训练角色 LoRA 的图片。导出的 caption 包含每张图使用的画风和内容提示词，不含角色特征（让画法不会被学成角色的一部分）。</p>}
    <p className="prompt-hint">公共分区和人物卡片不参与批跑。{gptMode
      ? 'GPT 的尺寸、质量和每条张数使用下方独立设置，自动比例开启时按条目调整尺寸；NovelAI 参数不参与。'
      : '负面提示词、模型、尺寸（关闭自动比例时）、步数、CFG、采样器和每条张数取自当前生成设置。'}</p>
    {snapshot ? <div className="experiment-note" role="status">
      <p>这里展示本次训练集批跑固定的配置与 {snapshot.items?.length ?? 0} 条提示词。编辑草稿不会改变服务器批跑。</p>
      <p>画风：{snapshot.styles?.length ? snapshot.styles.join(' ｜ ') : snapshot.parameters.style_prompt}</p>
      {frozenCharacter && <p>{characterSnapshotSummary(frozenCharacter)}</p>}
    </div> : mode === 'style' ? <>
      <div className="dataset-style-preview"><span>将应用的画风</span>
        <p>{style.trim() ? style : '（未填写画风）'}</p></div>
      <div className="dataset-recipe-bar">
        <button className="primary" type="button" onClick={() => setRecipeOpen(true)}><Shuffle size={14} aria-hidden="true" /> 随机配方…</button>
        <span className="prompt-hint">按分区随机组合内容（景别、外貌、服装、动作、场景……），带占比、冲突规则和每条画风增删，生成结果追加到下方列表。</span>
      </div>
      {recipeMessage && <p className="subtle" role="status">{recipeMessage}</p>}
      <RecipeEditor api={api} open={recipeOpen} onClose={() => setRecipeOpen(false)} style={style} onGenerate={acceptRecipe} />
      <PromptLibrary entries={entries} setEntries={setEntries} categories={[]} defaults={defaultDatasetEntries}
        placeholder="添加自定义内容提示词，例如 1girl, solo, sitting, library" name="画风训练集" allowCharacters showShape={shapes} />
    </> : <>
      <CharacterRunSettings api={api} state={character} model={generation.draft.model} draftStyle={style} />
      <p className="prompt-hint">{characterMode === 'gpt'
        ? 'GPT 默认条目覆盖肖像、正侧背面、站立、半身和坐姿等日常姿态，并穿插俯视、仰视和侧面。'
        : 'Precise 默认条目保留基础角色视图，并增加瑜伽、战斗姿态、四肢着地、坐位前屈和碰脚尖等复杂动作，搭配不同视角。'} 当前方式的条目编辑、勾选和自定义内容会单独保留；切换方式不会覆盖另一套。</p>
      <PromptLibrary key={characterMode} entries={characterEntries} setEntries={setCharacterEntries} categories={characterCategories(characterMode)} defaults={() => defaultCharacterEntries(characterMode)}
        placeholder="添加自定义内容提示词（不写性别、人数和外貌），例如 sitting, library, reading" name="角色训练集" allowCharacters={false} showShape={shapes} />
    </>}
    {!snapshot && <label className="dataset-shape-toggle">
      <input type="checkbox" checked={shapes} onChange={event => setAutoShape(event.target.checked)} />
      <span>按构图自动选比例：躺姿、四肢着地、爬行、平板支撑、侧平板、下犬式、坐位前屈，以及远景、风景和多人全身优先用横图，其他全身、七分身用竖图，其余用方图（{gptMode ? 'GPT 1024×1536 / 1024×1024 / 1536×1024' : '832×1216 / 1024×1024 / 1216×832'}）。关闭后整套使用{gptMode ? '下方 GPT 设置' : '生成设置'}的尺寸。</span>
    </label>}
    {!snapshot && error && <p className="alert" role="alert">{error}</p>}
    {!snapshot && <div className="experiment-preview" aria-live="polite" aria-atomic="true">
      <p><strong>{selected.length} 条</strong>{samples !== null && samples >= 1 && samples <= 8 && <> × 每条 {samples} 张 = <strong>{selected.length * samples} 张图像</strong></>}
        {selected.length > MAX_DATASET_ITEMS && `（上限 ${MAX_DATASET_ITEMS} 条）`}
        {shapeCounts && <>：竖图 {shapeCounts.portrait}、方图 {shapeCounts.square}、横图 {shapeCounts.landscape}</>}</p>
      <p className="prompt-hint">{mode === 'style'
        ? '每条提示词是一次付费生成。画风 LoRA 一般 30–150 张精选图即可。'
        : gptMode ? '每条提示词是一次 GPT 付费生成，请人工筛选角色一致、动作正确的图片，并核对 caption。'
          : '每条提示词是一次 NovelAI 付费生成，Precise Reference 会额外消耗 Anlas。请人工筛选角色一致、肢体正确的图片，并核对 caption。'}</p>
    </div>}
    {!snapshot && <p className="prompt-hint">{gptMode
      ? 'GPT 生图接口不接收种子，调整 NovelAI 的种子不会改变 GPT 请求，也无法靠种子保证复现。'
      : mode === 'style'
        ? '每条由服务器各自随机一个种子，生成设置里的种子不参与；种子随条目保存，续跑时保持不变。'
        : '每条使用不同种子：生成设置中的种子作为基础种子（留空则服务器随机一次），第 N 条使用基础种子 + N − 1。'}</p>}
    <p className="prompt-hint">批跑在服务器依次执行，单条失败后继续下一条，不会自动重试。刷新、关闭页面或退出登录不会停止；只有“停止”会阻止后续条目。已有任务在运行时会加入队列：NovelAI 与 GPT 各自按加入顺序逐个执行，互不等待；最多 10 个未完成任务。</p>
    <p className="prompt-hint">可从历史记录的「实验与训练集」中查看和导出已保存的图片。</p>
    {!snapshot && generation.error && !generation.submitUncertain && <p className="alert" role="alert">{generation.error}</p>}
    {!snapshot && <label className="dataset-run-name">训练集名称（可选）
      <input value={runName} maxLength={MAX_EXPERIMENT_NAME} placeholder={mode === 'style' ? '例如：水彩画风 第 1 版' : '例如：希望 角色 v2'}
        onChange={event => setRunName(event.target.value)} />
      <span className="prompt-hint">会显示在「已保存的画风实验与训练集」里，并用作导出 zip 的文件名；之后可以改名。</span>
    </label>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={locked || Boolean(error) || !selected.length || selected.length > MAX_DATASET_ITEMS} onClick={start}>
        <Layers size={15} aria-hidden="true" /> {runs.running ? '加入队列' : '开始批跑'}
      </button>
    </div>
  </section>
})

/** Compact draw summary under a recipe entry. */
function DrawSummary({ entry }: { entry: DatasetEntry }) {
  const edits = entry.styleEdits
  const flags = entry.draws?.filter(draw => draw.partition.startsWith('-') || draw.option.startsWith('-')) ?? []
  const edited = entry.draws?.some(draw => draw.partition === '-meta' && draw.option === 'edited')
  return <span className="dataset-item-draws">
    {flags.map((draw, index) => <i key={index}>{draw.label}</i>)}
    {edits && edits.add.map(tag => <b key={`a${tag}`} className="add">画风+{tag}</b>)}
    {edits && edits.remove.map(tag => <b key={`r${tag}`} className="remove">画风−{tag}</b>)}
    {edited && edits && (edits.add.length > 0 || edits.remove.length > 0) && <em>提示词已修改，画风增删可能已不适用</em>}
  </span>
}

export type DatasetExportSource =
  | { kind: 'experiment'; id: string }
  | { kind: 'experiments'; ids: readonly string[] }
  | { kind: 'selection'; ids: readonly string[] }

/** Reads every group of each chosen training set in order (metadata only). */
async function sourceJobs(api: WorkspaceApi, source: DatasetExportSource, signal: AbortSignal): Promise<GenerationView[]> {
  if (source.kind === 'selection') return selectedJobs(api, source.ids, signal)
  const ids = source.kind === 'experiment' ? [source.id] : source.ids
  const jobs: GenerationView[] = []
  for (const id of ids) jobs.push(...await experimentJobs(api, id, signal))
  return jobs
}

/** File-system-safe zip name from a training-set name; falls back to a dated default. */
function zipName(name: string | undefined): string {
  const date = new Date().toISOString().slice(0, 10)
  // eslint-disable-next-line no-control-regex
  const safe = (name ?? '').replace(/[\u0000-\u001f\u007f\\/:*?"<>|]+/g, '_').replace(/\s+/g, ' ').trim().replace(/^\.+/, '').slice(0, 80)
  return safe ? `${safe}-${date}.zip` : `lora-dataset-${date}.zip`
}

export function DatasetExportPanel({ api, source, fileName, onClose }: { api: WorkspaceApi; source: DatasetExportSource; fileName?: string; onClose: () => void }) {
  const [trigger, setTrigger] = useState('')
  const [prefix, setPrefix] = useState('')
  // On by default: character LoRA captions must name each image's drawing style.
  const [characterStyle, setCharacterStyle] = useState(true)
  // Experiment exports load their groups first so the user can drop off-model items.
  const [jobs, setJobs] = useState<GenerationView[] | null>(null)
  const [excluded, setExcluded] = useState<ReadonlySet<string>>(new Set())
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<DatasetExportProgress | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function loadGroups() {
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setRunning(true)
    setError('')
    try {
      if (source.kind !== 'experiment') return
      const loaded = await experimentJobs(api, source.id, current.signal)
      if (controller.current === current) setJobs(loaded)
    } catch (exception) {
      if (!current.signal.aborted) setError(exception instanceof ApiFailure ? errorText(exception) : '读取记录失败，请重试。')
    } finally {
      if (controller.current === current) {
        controller.current = null
        setRunning(false)
      }
    }
  }

  async function run() {
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setRunning(true)
    setError('')
    setMessage('')
    setProgress(null)
    try {
      // Always re-read: groups may have finished or been reviewed since the checklist loaded.
      const all = await sourceJobs(api, source, current.signal)
      const chosen = all.filter(job => !excluded.has(job.id))
      const result = await buildDatasetZip(api, chosen, trigger, prefix, current.signal, setProgress, characterStyle)
      if (current.signal.aborted) return
      const discardedText = result.discarded ? `，已弃置 ${result.discarded} 张未导出` : ''
      if (!result.blob) setError(`没有可导出的图片（跳过 ${result.skipped} 张：失败、已过期或不可用${discardedText}）。`)
      else {
        downloadZip(result.blob, zipName(fileName))
        setMessage(`已导出 ${result.written} 张图片和对应 caption${result.skipped ? `，跳过 ${result.skipped} 张（失败、已过期或不可用）` : ''}${discardedText}。`)
      }
    } catch (exception) {
      if (!current.signal.aborted) setError(exception instanceof ApiFailure ? errorText(exception) : exception instanceof Error ? exception.message : '导出失败，请重试。')
      else setMessage('已取消导出。')
    } finally {
      if (controller.current === current) {
        controller.current = null
        setRunning(false)
      }
    }
  }

  return <div className="dataset-export" role="group" aria-label="导出训练集">
    <label className="field"><span>触发词（可选，加在每个 caption 开头）</span>
      <input type="text" value={trigger} maxLength={100} spellCheck={false} disabled={running} placeholder="例如 mystyle"
        onChange={event => setTrigger(event.target.value)} /></label>
    <label className="field"><span>质量词前缀（可选，加在触发词之后、内容标签之前；生成时也写同样的词）</span>
      <input type="text" value={prefix} maxLength={300} spellCheck={false} disabled={running} placeholder="例如 masterpiece, best quality, newest, absurdres, highres"
        onChange={event => setPrefix(event.target.value)} /></label>
    <label className="history-select"><input type="checkbox" checked={characterStyle} disabled={running}
      onChange={event => setCharacterStyle(event.target.checked)} /> 角色训练集：caption 写入每张图使用的画风（推荐，默认开启；画风训练集不受影响）</label>
    <div className="experiment-config-actions">
      <button className="text-action" type="button" disabled={running} onClick={() => setPrefix(NOOBAI_QUALITY_PREFIX)}>NoobAI-XL 预设</button>
      <button className="text-action" type="button" disabled={running} onClick={() => setPrefix(ANIMAGINE_QUALITY_PREFIX)}>Animagine XL 4.0 预设</button>
      {prefix && <button className="text-action" type="button" disabled={running} onClick={() => setPrefix('')}>清空前缀</button>}
    </div>
    <p className="prompt-hint">caption 示例：{[trigger.trim(), prefix.trim(), '1girl, solo, portrait, smile…'].filter(Boolean).join(', ')}。只放质量词：皮肤光泽、眼睛细节等希望成为画风的一部分的质感，不要写进 caption。</p>
    <p className="prompt-hint">zip 内为 0001.png + 0001.txt 成对文件。图片去除元数据与隐写信息；画风训练集的 caption 不含画风；角色训练集默认写入每张图的画风（去掉画师和负权重标签），始终不含角色特征。已弃置的图片不会导出。导出只读取已保存图片，不会生成。</p>
    {source.kind === 'experiment' && (jobs === null
      ? <button className="text-action" type="button" disabled={running} onClick={() => void loadGroups()}>筛选条目（可选：取消不像角色或不满意的条目）</button>
      : <details className="dataset-category" open><summary><strong>导出条目</strong><span>{jobs.length - excluded.size} / {jobs.length}</span>
          <span className="prompt-hint">可先在「浏览图片」中查看第 N 条，再在这里取消</span></summary>
        <ul className="dataset-items">{jobs.map(job => {
          const context = job.parameters.experiment
          return <li key={job.id} className={excluded.has(job.id) ? 'muted' : ''}>
            <input type="checkbox" checked={!excluded.has(job.id)} disabled={running} aria-label={`导出第 ${context?.ordinal ?? '?'} 条`}
              onChange={event => setExcluded(current => {
                const next = new Set(current)
                if (event.target.checked) next.delete(job.id)
                else next.add(job.id)
                return next
              })} />
            <span>第 {context?.ordinal ?? '?'} 条 · {job.status === 'succeeded' ? `${job.image_urls.length} 张` : '无可用图片'} · {context?.item ? datasetItemText(context.item) : ''}</span>
            <span />
          </li>
        })}</ul></details>)}
    {source.kind === 'experiments' && <p className="prompt-hint">将把所选 {source.ids.length} 个训练集合并导出到一个 zip，编号连续。</p>}
    {progress && <p role="status" aria-live="polite">已处理 {progress.processedJobs} / {progress.totalJobs} 条记录 · 已写入 {progress.written} 张 · 跳过 {progress.skipped} 张 · 已弃置 {progress.discarded} 张</p>}
    {message && <p className="experiment-note" role="status">{message}</p>}
    {error && <p className="alert" role="alert">{error}</p>}
    <div className="experiment-config-actions">
      {running
        ? <button className="secondary" type="button" onClick={() => controller.current?.abort()}><X size={14} aria-hidden="true" /> 取消导出</button>
        : <button className="primary" type="button" onClick={() => void run()}><Download size={14} aria-hidden="true" /> 导出 zip</button>}
      <button className="text-action" type="button" disabled={running} onClick={onClose}>关闭</button>
    </div>
  </div>
}
