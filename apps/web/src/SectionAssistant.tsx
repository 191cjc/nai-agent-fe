import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { observer } from 'mobx-react-lite'
import { Search, Send, Sparkles, X } from 'lucide-react'
import { ApiFailure, errorText, type TagCandidate, type WorkspaceApi } from './api'
import type { GenerationStore } from './store'
import { SECTION_LABELS, promptTextTargetKey, type CharacterSectionKey, type PromptTextTarget, type SharedSectionKey, type SnapshotImportMode } from './prompt-sections'

const TABS = [['advice', 'AI 建议'], ['translation', 'AI 翻译'], ['search', '提示词搜索']] as const
type AssistantTab = typeof TABS[number][0]
interface TranslationSnapshot {
  source: string
  question: string
  explanation: string
}
export interface AssistantOpening {
  id: number
  target: PromptTextTarget
  label: string
  text: string
  revision: number
  opener: HTMLButtonElement
}
export type OpenSectionAssistant = (target: PromptTextTarget, label: string, opener: HTMLButtonElement) => void

const ADVICE_SCOPES = {
  style: '画风、媒介、绘制方式、线条、上色、阴影及所需的视觉表现',
  negative: '希望排除的内容、视觉缺陷和伪影，使用负面排除标签',
  shared: {
    scene: '公共场景的地点、环境、背景、时间、天气、场景物件和光照',
    other: '全局构图、取景、视角、氛围及其他公共细节',
  } satisfies Record<SharedSectionKey, string>,
  character: {
    character: '当前人物的身份、物种、外貌、头发、眼睛、面部和身体特征',
    upper_clothing: '当前人物的上半身服装、领口、袖子、材质、颜色和上半身配饰',
    lower_clothing: '当前人物的裤子、裙子、腿部服饰、袜子、鞋子和下半身配饰',
    action: '当前人物的姿势、动作、手势、身体朝向、表情、视线和互动',
    tags: '依据当前内容和用户意图，补充适用于当前人物的描述标签',
    special: '当前人物按需求指定的特殊特征、局部效果或特殊描述',
    other: '当前人物未归入其他分区的局部细节，依据当前内容和用户意图补充',
  } satisfies Record<CharacterSectionKey, string>,
} satisfies Record<PromptTextTarget['scope'], string | Record<string, string>>

function sectionPurpose(target: PromptTextTarget): string {
  return target.scope === 'shared' ? ADVICE_SCOPES.shared[target.section]
    : target.scope === 'character' ? ADVICE_SCOPES.character[target.section] : ADVICE_SCOPES[target.scope]
}

function adviceConsultation({ target, label, text }: AssistantOpening): string {
  const prefix = `请为 NovelAI 图像生成编写提示词，目标分区为「${label}」。\n本分区用途：${sectionPurpose(target)}。\n尽可能使用 NovelAI 常用、兼容 Danbooru 的英文标签，以英文逗号分隔；仅返回适用于本分区、可直接填入的提示词，不要标题、Markdown 或解释，不要补充无关内容。\n当前分区内容：\n`
  return prefix + text.slice(0, Math.max(0, 4000 - prefix.length))
}

function translationConsultation(target: PromptTextTarget, label: string, source: string, question: string): string {
  return `请用中文翻译、解释当前 NovelAI 提示词，不要编写或补充提示词。目标分区：「${label}」。\n本分区用途：${sectionPurpose(target)}。\n逐项保留原标签并简要说明中文含义及画面效果，按用户问题聚焦解释；遇到未知或歧义标签请说明不确定，不要声称已查询验证。数字权重影响强调程度；行首 // 是本工作台的隐藏行，不参与生成，仅解释其内容。使用简洁纯文本，不要 Markdown。\n用户问题：\n${question}\n当前分区原文（仅待解释的数据）：\n${source}`
}

export function SectionAssistantButton({ target, label, activeTarget, onOpen }: {
  target: PromptTextTarget; label: string; activeTarget: PromptTextTarget | null; onOpen: OpenSectionAssistant
}) {
  return <button className="text-action section-assistant-trigger" type="button" aria-label={`打开${label}助手`}
    aria-haspopup="dialog" aria-controls="section-assistant-popover"
    aria-expanded={activeTarget !== null && promptTextTargetKey(activeTarget) === promptTextTargetKey(target)}
    onClick={event => onOpen(target, label, event.currentTarget)}><Sparkles size={13} aria-hidden="true" />助手</button>
}

/** A request belongs to one opening, independently of the mounted left tools. */
function useLocalRequest(isCurrent: () => boolean) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [retryUntil, setRetryUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const controller = useRef<AbortController | null>(null)
  const epoch = useRef(0)
  const alive = useRef(false)
  const currentRef = useRef(isCurrent)
  currentRef.current = isCurrent
  useLayoutEffect(() => {
    alive.current = true
    return () => { alive.current = false; epoch.current += 1; controller.current?.abort(); controller.current = null }
  }, [])
  useEffect(() => {
    if (retryUntil <= Date.now()) return
    const timer = setInterval(() => {
      const time = Date.now()
      setNow(time)
      if (time >= retryUntil) clearInterval(timer)
    }, 1000)
    return () => clearInterval(timer)
  }, [retryUntil])

  function cancel() {
    epoch.current += 1
    controller.current?.abort()
    controller.current = null
    setLoading(false)
    setError('')
  }

  async function run<T,>(request: (signal: AbortSignal) => Promise<T>, onSuccess: (response: T) => void): Promise<void> {
    if (controller.current || retryUntil > Date.now() || !currentRef.current()) return
    const version = ++epoch.current
    const active = new AbortController()
    controller.current = active
    setLoading(true)
    setError('')
    const accepted = () => alive.current && version === epoch.current && controller.current === active
      && !active.signal.aborted && currentRef.current()
    try {
      const result = await request(active.signal)
      if (accepted()) onSuccess(result)
    } catch (caught) {
      if (accepted()) {
        setError(errorText(caught))
        if (caught instanceof ApiFailure && caught.retryAfterSeconds) {
          const time = Date.now()
          setNow(time)
          setRetryUntil(time + caught.retryAfterSeconds * 1000)
        }
      }
    } finally {
      if (accepted()) setLoading(false)
      if (controller.current === active) controller.current = null
    }
  }

  return { loading, error, retrySeconds: Math.max(0, Math.ceil((retryUntil - now) / 1000)), run, cancel }
}

function openerVisible(opener: HTMLElement): boolean {
  if (!opener.isConnected || opener.closest('[hidden], [inert]')) return false
  const rect = opener.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0 || getComputedStyle(opener).visibility !== 'visible') return false
  // A mobile keyboard can cover the anchor while the editor remains open.
  // Layout clipping, rather than the smaller visual viewport, defines hiding.
  for (let ancestor = opener.parentElement; ancestor; ancestor = ancestor.parentElement) {
    const style = getComputedStyle(ancestor)
    const bounds = ancestor.getBoundingClientRect()
    if (style.visibility === 'hidden' || style.display === 'none') return false
    if (/(auto|scroll|hidden|clip)/.test(style.overflowY) && (rect.bottom <= bounds.top || rect.top >= bounds.bottom)) return false
    if (/(auto|scroll|hidden|clip)/.test(style.overflowX) && (rect.right <= bounds.left || rect.left >= bounds.right)) return false
  }
  return true
}

export const SectionAssistantPopover = observer(({ api, generation, opening, onClose }: {
  api: WorkspaceApi; generation: GenerationStore; opening: AssistantOpening; onClose: () => void
}) => {
  const [tab, setTab] = useState<AssistantTab>('advice')
  const [input, setInput] = useState(() => adviceConsultation(opening))
  const [suggestion, setSuggestion] = useState('')
  const [hasSuggestion, setHasSuggestion] = useState(false)
  const [translationQuestion, setTranslationQuestion] = useState('请用中文简要解释这些提示词的含义和画面效果。')
  const [translationSnapshot, setTranslationSnapshot] = useState<TranslationSnapshot | null>(null)
  const [translationError, setTranslationError] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<TagCandidate[]>([])
  const [searched, setSearched] = useState(false)
  const [applyError, setApplyError] = useState('')
  const [applied, setApplied] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryRef = useRef<HTMLInputElement>(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  const id = useId()
  const target = opening.target
  const label = target.scope === 'character'
    ? `人物 ${generation.draft.character_prompts.findIndex(person => person.id === target.characterId) + 1} · ${SECTION_LABELS[target.section]}` : opening.label
  const currentSource = generation.promptTextAt(target)
  const translationInputError = !currentSource?.trim() ? '当前分区没有提示词，请先填写内容。'
    : !translationQuestion.trim() ? '请填写想了解的问题。'
      : translationQuestion.length > 500 ? '问题不能超过 500 个字符。'
        : translationConsultation(target, label, currentSource, translationQuestion).length > 4000 ? '原文和问题合计过长，请缩短问题后重试；不会截断原文。' : ''
  const translationStale = translationSnapshot !== null && translationSnapshot.source !== currentSource
  const isCurrent = () => opening.revision === generation.assistantDraftRevision
    && generation.promptTextAt(opening.target) !== undefined && openerVisible(opening.opener)
  const advice = useLocalRequest(isCurrent)
  const translation = useLocalRequest(isCurrent)
  const search = useLocalRequest(isCurrent)

  useLayoutEffect(() => {
    const panel = panelRef.current
    if (!panel) return
    let frame = 0
    function position() {
      if (!panel || !openerVisible(opening.opener)) { closeRef.current(); return }
      const viewport = window.visualViewport
      const margin = 8
      const gap = 8
      const left = (viewport?.offsetLeft ?? 0) + margin
      const top = (viewport?.offsetTop ?? 0) + margin
      const width = Math.max(1, (viewport?.width ?? window.innerWidth) - margin * 2)
      const height = Math.max(1, (viewport?.height ?? window.innerHeight) - margin * 2)
      panel.style.width = `${Math.min(420, width)}px`
      panel.style.maxHeight = `${Math.min(580, height)}px`
      const anchor = opening.opener.getBoundingClientRect()
      const box = panel.getBoundingClientRect()
      const below = top + height - anchor.bottom - gap
      const above = anchor.top - gap - top
      const desiredTop = below >= box.height || below >= above ? anchor.bottom + gap : anchor.top - box.height - gap
      panel.style.left = `${Math.max(left, Math.min(anchor.right - box.width, left + width - box.width))}px`
      panel.style.top = `${Math.max(top, Math.min(desiredTop, top + height - box.height))}px`
      panel.style.visibility = 'visible'
    }
    function schedulePosition() {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(position)
    }
    function outside(event: PointerEvent) {
      if (event.target instanceof Node && !panel?.contains(event.target) && !opening.opener.contains(event.target)) closeRef.current()
    }
    function focusOutside(event: FocusEvent) {
      if (event.target instanceof Node && !panel?.contains(event.target) && !opening.opener.contains(event.target)) closeRef.current()
    }
    function escape(event: globalThis.KeyboardEvent) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      closeRef.current()
    }
    position()
    inputRef.current?.focus({ preventScroll: true })
    window.addEventListener('resize', schedulePosition)
    window.addEventListener('scroll', schedulePosition, true)
    window.visualViewport?.addEventListener('resize', schedulePosition)
    window.visualViewport?.addEventListener('scroll', schedulePosition)
    document.addEventListener('pointerdown', outside, true)
    document.addEventListener('focusin', focusOutside)
    document.addEventListener('keydown', escape, true)
    const resize = new ResizeObserver(schedulePosition)
    resize.observe(panel)
    resize.observe(opening.opener)
    const mutations = new MutationObserver(schedulePosition)
    for (let ancestor: HTMLElement | null = opening.opener; ancestor; ancestor = ancestor.parentElement) {
      mutations.observe(ancestor, { attributes: true, attributeFilter: ['hidden', 'inert', 'style', 'class'] })
    }
    mutations.observe(document.body, { childList: true, subtree: true })
    return () => {
      cancelAnimationFrame(frame)
      resize.disconnect()
      mutations.disconnect()
      window.removeEventListener('resize', schedulePosition)
      window.removeEventListener('scroll', schedulePosition, true)
      window.visualViewport?.removeEventListener('resize', schedulePosition)
      window.visualViewport?.removeEventListener('scroll', schedulePosition)
      document.removeEventListener('pointerdown', outside, true)
      document.removeEventListener('focusin', focusOutside)
      document.removeEventListener('keydown', escape, true)
      if (panel.contains(document.activeElement) || document.activeElement === document.body) {
        const fallback = document.getElementById('prompt-drawer-toggle')
        const destination = openerVisible(opening.opener) ? opening.opener : fallback
        if (destination?.isConnected && !destination.closest('[hidden], [inert]')) destination.focus({ preventScroll: true })
      }
    }
  }, [opening])

  function selectTab(next: AssistantTab, focusTab = false) {
    setTab(next)
    if (focusTab) panelRef.current?.querySelector<HTMLButtonElement>(`[data-assistant-tab="${next}"]`)?.focus()
  }

  function tabKeys(event: KeyboardEvent<HTMLDivElement>) {
    const current = TABS.findIndex(([name]) => name === tab)
    const next = event.key === 'ArrowRight' ? (current + 1) % TABS.length
      : event.key === 'ArrowLeft' ? (current + TABS.length - 1) % TABS.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? TABS.length - 1 : null
    if (next === null) return
    event.preventDefault()
    event.stopPropagation()
    selectTab(TABS[next][0], true)
  }

  async function requestAdvice() {
    if (!input.trim() || input.length > 4000 || advice.loading || advice.retrySeconds) return
    setHasSuggestion(false)
    setSuggestion('')
    setApplied('')
    await advice.run(signal => api.advice(input, signal), response => {
      if (typeof response.suggestion !== 'string' || !response.suggestion.trim() || response.suggestion.length > 3000) {
        setApplyError('建议结果无效，请重新获取；草稿未修改。')
        return
      }
      setSuggestion(response.suggestion)
      setHasSuggestion(true)
      setApplyError('')
    })
  }

  async function requestSearch() {
    if (!query.trim() || query.trim().length > 100 || search.loading || search.retrySeconds) return
    setSearched(false)
    setResults([])
    await search.run(signal => api.search(query.trim(), signal), response => {
      setResults(response.results)
      setSearched(true)
    })
  }

  async function requestTranslation() {
    if (translation.loading || translation.retrySeconds) return
    if (!isCurrent()) { closeRef.current(); return }
    const source = generation.promptTextAt(target)
    const question = translationQuestion
    if (!source?.trim() || !question.trim() || question.length > 500) return
    const consultation = translationConsultation(target, label, source, question)
    if (consultation.length > 4000) return
    setTranslationSnapshot({ source, question, explanation: '' })
    setTranslationError('')
    await translation.run(signal => api.advice(consultation, signal), response => {
      if (typeof response.suggestion !== 'string' || !response.suggestion.trim() || response.suggestion.length > 3000) {
        setTranslationError('翻译结果无效，请重新获取。')
        return
      }
      setTranslationSnapshot({ source, question, explanation: response.suggestion })
    })
  }

  function apply(text: string, mode: SnapshotImportMode) {
    setApplyError('')
    setApplied('')
    if (!isCurrent()) { closeRef.current(); return }
    try {
      generation.applyPromptText(opening.target, text, mode, opening.revision)
      setApplied(`已${mode === 'append' ? '追加到' : '覆盖'}${label}`)
    } catch (caught) { setApplyError(caught instanceof Error ? caught.message : '无法填入当前分区，草稿未修改。') }
  }

  return createPortal(<div ref={panelRef} id="section-assistant-popover" className="section-assistant-popover"
    role="dialog" aria-modal="false" aria-labelledby={`${id}-title`} style={{ visibility: 'hidden' }}
    onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onClose() }
      // Portal events bubble through the editor's generation form.
      if (event.key === 'Enter') event.stopPropagation()
    }}>
    <header className="section-assistant-heading"><h2 id={`${id}-title`}>{label}<span>分区助手</span></h2>
      <button className="icon-button" type="button" aria-label="关闭分区助手" onClick={onClose}><X size={17} aria-hidden="true" /></button></header>
    <div className="section-assistant-tabs" role="tablist" aria-label="分区助手工具" onKeyDown={tabKeys}>
      {TABS.map(([name, label]) => <button key={name} type="button" role="tab" data-assistant-tab={name} id={`${id}-tab-${name}`}
        aria-selected={tab === name} aria-controls={`${id}-panel-${name}`} tabIndex={tab === name ? 0 : -1}
        onClick={() => selectTab(name)}>{label}</button>)}
    </div>
    <div className="section-assistant-scroll">
      <div role="tabpanel" id={`${id}-panel-advice`} aria-labelledby={`${id}-tab-advice`} hidden={tab !== 'advice'}>
        <label className="field"><span>咨询内容</span><textarea ref={inputRef} value={input} rows={4} maxLength={4000}
          onChange={event => { advice.cancel(); setInput(event.target.value) }}
          onKeyDown={event => { if (event.key === 'Enter' && !event.nativeEvent.isComposing && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void requestAdvice() } }} /></label>
        <p className="prompt-hint">仅发送上方内容，可修改后咨询。Ctrl / ⌘ + Enter 获取建议。</p>
        <div className="section-assistant-submit"><button className="primary" type="button" disabled={advice.loading || advice.retrySeconds > 0 || !input.trim()}
          onClick={() => void requestAdvice()}><Send size={14} aria-hidden="true" />{advice.loading ? '正在获取...' : '获取建议'}</button></div>
        {advice.error && <p role="alert" className="alert">{advice.error}</p>}
        {advice.retrySeconds > 0 && <p className="subtle" role="status">{advice.retrySeconds} 秒后可重试</p>}
        {advice.loading && <p className="subtle" role="status">正在获取当前分区的建议...</p>}
        {hasSuggestion && <div className="section-assistant-suggestion"><label className="field"><span>建议提示词 · 可编辑</span>
          <textarea value={suggestion} rows={4} maxLength={3000} onChange={event => setSuggestion(event.target.value)} /></label>
          <div className="section-assistant-apply"><button type="button" className="secondary" disabled={!suggestion.trim()} onClick={() => apply(suggestion, 'append')}>追加</button>
            <button type="button" className="secondary" disabled={!suggestion.trim()} onClick={() => apply(suggestion, 'replace')}>覆盖</button></div></div>}
      </div>
      <div role="tabpanel" id={`${id}-panel-translation`} aria-labelledby={`${id}-tab-translation`} hidden={tab !== 'translation'}>
        <label className="field"><span>当前分区提示词 · 只读</span><textarea value={currentSource ?? ''} rows={4} readOnly /></label>
        <label className="field section-translation-question"><span>想了解什么</span><textarea value={translationQuestion} rows={2} maxLength={500}
          onChange={event => { translation.cancel(); setTranslationQuestion(event.target.value); setTranslationSnapshot(null); setTranslationError('') }}
          onKeyDown={event => { if (event.key === 'Enter' && !event.nativeEvent.isComposing && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void requestTranslation() } }} /></label>
        <p className="prompt-hint">可询问单个标签、权重或词义；仅解释上方原文，不修改提示词。Ctrl / ⌘ + Enter 获取翻译。</p>
        {translationInputError && <p className="prompt-hint">{translationInputError}</p>}
        <div className="section-assistant-submit"><button className="primary" type="button" disabled={translation.loading || translation.retrySeconds > 0 || !!translationInputError}
          onClick={() => void requestTranslation()}><Send size={14} aria-hidden="true" />{translation.loading ? '正在翻译...' : '获取翻译'}</button></div>
        {(translation.error || translationError) && <p role="alert" className="alert">{translation.error || translationError}</p>}
        {translation.retrySeconds > 0 && <p className="subtle" role="status">{translation.retrySeconds} 秒后可重试</p>}
        {translation.loading && <p className="subtle" role="status">正在解释本次请求的分区原文...</p>}
        {translationStale && <p className="alert" role="status">当前分区已更改，本次翻译对应先前内容。请重新获取翻译。</p>}
        {translationSnapshot?.explanation && !translationStale && <section className="section-assistant-suggestion section-translation-result" aria-labelledby={`${id}-translation-title`}>
          <h3 id={`${id}-translation-title`}>中文解释</h3>
          <p className="prompt-hint">本次问题：{translationSnapshot.question}</p>
          <p className="section-translation-explanation">{translationSnapshot.explanation}</p>
        </section>}
      </div>
      <div role="tabpanel" id={`${id}-panel-search`} aria-labelledby={`${id}-tab-search`} hidden={tab !== 'search'}>
        <div className="search-form"><label className="sr-only" htmlFor={`${id}-query`}>搜索当前分区提示词</label>
          <input ref={queryRef} id={`${id}-query`} value={query} maxLength={100} placeholder="搜索中文或英文提示词"
            onChange={event => { search.cancel(); setQuery(event.target.value); setResults([]); setSearched(false) }}
            onKeyDown={event => { if (event.key === 'Enter' && !event.nativeEvent.isComposing) { event.preventDefault(); void requestSearch() } }} />
          <button className="primary icon-button" type="button" aria-label="搜索当前分区提示词" disabled={search.loading || search.retrySeconds > 0 || !query.trim()}
            onClick={() => void requestSearch()}><Search size={17} aria-hidden="true" /></button></div>
        <div className="source-line">来源：<a href="https://huggingface.co/spaces/SAkizuki/DanbooruSearch" target="_blank" rel="noopener noreferrer">DanbooruSearch</a></div>
        {search.error && <p role="alert" className="alert">{search.error}</p>}
        {search.retrySeconds > 0 && <p className="subtle" role="status">{search.retrySeconds} 秒后可重试</p>}
        {search.loading && <p className="subtle" role="status">正在搜索...</p>}
        {searched && !results.length && <p className="subtle" role="status">没有匹配的提示词</p>}
        <div className="tag-results">{results.map((candidate, index) => <article className="tag-item" key={`${candidate.tag}-${index}`}>
          <div className="tag-head"><strong>{candidate.tag}</strong>{candidate.is_nsfw === true && <span className="nsfw">NSFW</span>}</div>
          {candidate.cn_name && <div className="tag-cn">{candidate.cn_name}</div>}
          {(candidate.category || candidate.count != null || candidate.score != null) && <div className="tag-meta">
            {candidate.category && <span>{candidate.category}</span>}
            {candidate.count != null && <span>{candidate.count.toLocaleString()} 次使用</span>}
            {candidate.score != null && <span>评分 {candidate.score.toFixed(2)}</span>}
          </div>}
          {candidate.summary && <p className="tag-summary">{candidate.summary}</p>}
          <div className="tag-actions"><button className="text-action" type="button" aria-label={`将 ${candidate.tag} 追加到${label}`} onClick={() => apply(candidate.tag, 'append')}>追加</button>
            <button className="text-action" type="button" aria-label={`用 ${candidate.tag} 覆盖${label}`} onClick={() => apply(candidate.tag, 'replace')}>覆盖</button></div>
        </article>)}</div>
      </div>
    </div>
    {tab !== 'translation' && (applyError || applied) && <footer className="section-assistant-feedback">{applyError ? <p className="alert" role="alert">{applyError}</p>
      : <p className="prompt-hint" role="status">{applied}</p>}</footer>}
  </div>, document.body)
})
