import { makeAutoObservable, runInAction } from 'mobx'
import { errorText, type AccountBalance, WorkspaceApi } from './api'

const POLL_INTERVAL_MS = 30_000
// Leave the server's five-second account cache before observing activity again.
const ACTIVITY_DELAY_MS = 5_500

/** Read-only account observation, independent of generation acceptance and errors. */
export class BalanceStore {
  balance: AccountBalance | null = null
  loading = false
  error = ''
  private observing = false
  private epoch = 0
  private controller: AbortController | null = null
  private pollTimer: ReturnType<typeof setTimeout> | null = null
  private activityTimer: ReturnType<typeof setTimeout> | null = null
  private activityPending = false

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  private isVisible(): boolean {
    return typeof document === 'undefined' || document.visibilityState !== 'hidden'
  }

  enterWorkspace(): void {
    if (this.observing) return
    this.observing = true
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', this.onVisibilityChange)
    if (this.isVisible()) void this.refresh()
    this.schedulePoll()
  }

  private onVisibilityChange(): void {
    this.clearTimers()
    if (!this.observing || !this.isVisible()) return
    void this.refresh()
    this.schedulePoll()
    this.scheduleActivity()
  }

  private schedulePoll(): void {
    if (!this.observing || !this.isVisible() || this.pollTimer !== null) return
    this.pollTimer = setTimeout(() => {
      this.pollTimer = null
      if (!this.observing || !this.isVisible()) return
      void this.refresh()
      this.schedulePoll()
    }, POLL_INTERVAL_MS)
  }

  noteActivity(): void {
    if (!this.observing) return
    this.activityPending = true
    this.scheduleActivity()
  }

  private scheduleActivity(): void {
    if (!this.observing || !this.isVisible() || this.loading || !this.activityPending || this.activityTimer !== null) return
    // Subsequent progress signals share this timer rather than postpone it.
    this.activityTimer = setTimeout(() => {
      this.activityTimer = null
      if (!this.observing || !this.isVisible()) return
      // An older in-flight read cannot consume this intent. Its completion
      // schedules a fresh delay, including if that read fails.
      if (this.loading) return
      this.activityPending = false
      void this.refresh()
    }, ACTIVITY_DELAY_MS)
  }

  async refresh(): Promise<void> {
    if (!this.observing || this.loading) return
    const epoch = this.epoch
    const controller = new AbortController()
    this.controller = controller
    this.loading = true
    // A manual/periodic read can complete with a snapshot older than an
    // activity signal. Preserve that intent beyond this read and cache window.
    if (this.activityTimer !== null) clearTimeout(this.activityTimer)
    this.activityTimer = null
    try {
      const balance = await this.api.balance(controller.signal)
      if (epoch !== this.epoch || !this.observing) return
      runInAction(() => { this.balance = balance; this.error = '' })
    } catch (error) {
      if (epoch === this.epoch && this.observing) runInAction(() => { this.error = errorText(error) })
    } finally {
      if (epoch === this.epoch && this.observing) runInAction(() => {
        this.controller = null
        this.loading = false
        this.scheduleActivity()
      })
    }
  }

  private clearTimers(): void {
    if (this.pollTimer !== null) clearTimeout(this.pollTimer)
    if (this.activityTimer !== null) clearTimeout(this.activityTimer)
    this.pollTimer = null
    this.activityTimer = null
  }

  reset(): void {
    this.epoch += 1
    this.observing = false
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', this.onVisibilityChange)
    this.controller?.abort()
    this.controller = null
    this.clearTimers()
    this.activityPending = false
    this.balance = null
    this.loading = false
    this.error = ''
  }
}
