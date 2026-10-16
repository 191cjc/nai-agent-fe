import { observer } from 'mobx-react-lite'
import { ChevronDown, RefreshCw } from 'lucide-react'
import type { BalanceStore } from './balance-store'

export const AccountBalance = observer(({ store }: { store: BalanceStore }) => {
  const balance = store.balance
  const value = balance !== null ? balance.total.toLocaleString('zh-CN') : store.loading ? '查询中' : '暂不可用'
  const stale = balance !== null && !!store.error
  const label = `图像服务 Anlas 余额：${value}${stale ? '，刷新失败，显示上次结果' : ''}`
  const updated = balance === null ? null : new Date(balance.fetched_at * 1000)
  const validDate = updated !== null && Number.isFinite(updated.getTime())

  return <div className="account-balance">
    <details className="account-balance-details" onKeyDown={event => {
      if (event.key !== 'Escape' || !event.currentTarget.open) return
      event.preventDefault()
      event.currentTarget.open = false
      event.currentTarget.querySelector('summary')?.focus()
    }}>
      <summary className="account-balance-summary" aria-label={`${label}，查看余额详情`} title={label}>
        <span className="account-balance-label">生图 Anlas</span>
        <span className="account-balance-value">{value}</span>
        {stale && <span className="account-balance-stale">未更新</span>}
        <ChevronDown size={12} aria-hidden="true" />
      </summary>
      <div className="account-balance-panel">
        <strong>图像服务 Anlas 余额</strong>
        {balance !== null && <>
          <dl>
            <div><dt>总余额</dt><dd>{balance.total.toLocaleString('zh-CN')}</dd></div>
            <div><dt>固定额度</dt><dd>{balance.fixed.toLocaleString('zh-CN')}</dd></div>
            <div><dt>购买额度</dt><dd>{balance.purchased.toLocaleString('zh-CN')}</dd></div>
          </dl>
          <p>更新于 {validDate
            ? <time dateTime={updated.toISOString()}>{updated.toLocaleString('zh-CN')}</time>
            : `${balance.fetched_at}（Unix 秒）`}</p>
        </>}
        {store.loading && <p>正在刷新余额…</p>}
        {store.error && <p className="account-balance-error">{store.error}{balance !== null ? ' 当前显示上次查询结果。' : ''}</p>}
      </div>
    </details>
    <button className="icon-button account-balance-refresh" type="button" disabled={store.loading}
      title="刷新图像服务余额" aria-label={store.loading ? '正在刷新图像服务余额' : '刷新图像服务 Anlas 余额'}
      onClick={() => void store.refresh()}><RefreshCw size={15} aria-hidden="true" /></button>
  </div>
})
