import { useLayoutEffect, useRef, useState } from 'react'
import { ArrowDownToLine } from 'lucide-react'
import { downloadPng, sanitizedPng } from './png-export'

export function ImageSaveButton({ url, filename, isCurrent }: {
  url: string
  filename: string
  isCurrent: () => boolean
}) {
  const pending = useRef<AbortController | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useLayoutEffect(() => {
    setSaving(false)
    setError('')
    return () => {
      pending.current?.abort()
      pending.current = null
    }
  }, [url, filename])

  async function save() {
    if (pending.current || !isCurrent()) return
    const controller = new AbortController()
    pending.current = controller
    setSaving(true)
    setError('')
    try {
      const blob = await sanitizedPng(url, controller.signal)
      // Check live store ownership as well as component cleanup, including logout start.
      if (!controller.signal.aborted && isCurrent()) downloadPng(blob, filename)
    } catch {
      if (!controller.signal.aborted && isCurrent()) setError('保存失败，请重试。')
    } finally {
      if (pending.current === controller) {
        pending.current = null
        if (!controller.signal.aborted) setSaving(false)
      }
    }
  }

  return <div className="image-save-action">
    {error && <span className="image-save-error" role="alert">{error}</span>}
    <button className="secondary image-save-button" type="button" disabled={saving} aria-busy={saving}
      title="保存图片（清除 NovelAI 元数据）" onClick={() => void save()}>
      <ArrowDownToLine size={15} aria-hidden="true" />{saving ? '保存中…' : '保存'}
    </button>
  </div>
}

export function ImageSeedButton({ seed, onUseSeed }: { seed: number; onUseSeed: (seed: number) => void }) {
  return <button className="image-seed-button" type="button" title="点击将种子填入生成设置"
    aria-label={`使用种子 ${seed}`} onClick={() => onUseSeed(seed)}>种子 {seed}</button>
}
