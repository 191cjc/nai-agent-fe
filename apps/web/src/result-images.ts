import type { GenerationView } from './api'

/** Original image identities stay stable even when some slots have been purged. */
export function imagePurged(job: GenerationView, index: number): boolean {
  return job.purged_images?.includes(index) === true || job.purge_pending_images?.includes(index) === true
}

export function retainedImageIndexes(job: GenerationView): number[] {
  return job.status === 'succeeded' ? job.image_urls.flatMap((_path, index) => imagePurged(job, index) ? [] : [index]) : []
}

export function allImagesPurged(job: GenerationView): boolean {
  return job.status === 'succeeded' && job.image_count > 0
    && Array.from({ length: job.image_count }, (_value, index) => index).every(index => imagePurged(job, index))
}
