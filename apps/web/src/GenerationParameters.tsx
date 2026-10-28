import type { GenerationView } from './api'
import { PromptSummary } from './PromptSummary'

export function GenerationParameters({ job }: { job: GenerationView }) {
  return <>
    <PromptSummary parameters={job.parameters} />
    {job.parameters.negative_prompt && <p>负向：{job.parameters.negative_prompt}</p>}
    <p>{job.parameters.model} · {job.parameters.width}×{job.parameters.height} · {job.parameters.sampler}</p>
    <p>{job.parameters.steps} 步 · CFG {job.parameters.cfg_scale} · 实际种子 {job.effective_seed} · {job.parameters.sample_count} 张 · {job.parameters.quality ? '高质量' : '标准质量'}</p>
    <details className="request-snapshot">
      <summary>工作台入参（含注释和分区）</summary>
      <pre className="request-snapshot-json" tabIndex={0} aria-label="工作台入参 JSON">{JSON.stringify(job.parameters, null, 2)}</pre>
    </details>
    <details className="request-snapshot">
      <summary>NovelAI 服务入参</summary>
      {job.provider_request == null
        ? <p>该记录的 NovelAI 服务入参不可用，可能是旧记录或尚未到达提交阶段。</p>
        : <pre className="request-snapshot-json" tabIndex={0} aria-label="NovelAI 服务入参 JSON">{JSON.stringify(job.provider_request, null, 2)}</pre>}
    </details>
    <p>任务 ID：{job.id}</p>
  </>
}
