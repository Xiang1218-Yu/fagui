import { useEffect, useState } from 'react'
import { listRuns, listSources, runSnapshots } from '../api'
import type { CrawlRun, Snapshot, Source } from '../types'
import { fmtTime, runStatusBadge, runStatusLabel } from '../labels'

export default function Runs() {
  const [runs, setRuns] = useState<CrawlRun[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [filter, setFilter] = useState<number | undefined>(undefined)
  const [snaps, setSnaps] = useState<Snapshot[] | null>(null)
  const [snapRun, setSnapRun] = useState<number | null>(null)

  const load = () => listRuns(filter).then(setRuns).catch(() => {})
  useEffect(() => { listSources().then(setSources).catch(() => {}) }, [])
  useEffect(() => { load() }, [filter])
  useEffect(() => {
    const t = setInterval(load, 8000)
    return () => clearInterval(t)
  }, [filter])

  const sourceName = (id: number) => sources.find((s) => s.id === id)?.name ?? `#${id}`

  const openSnaps = async (runId: number) => {
    setSnapRun(runId)
    setSnaps(await runSnapshots(runId))
  }

  return (
    <div>
      <h2 className="page-title">采集运行</h2>
      <p className="page-desc">查看每次采集的执行结果、抓取页面/附件数量、检测到的变更与 robots 拦截情况。</p>

      <div className="toolbar">
        <select value={filter ?? ''} onChange={(e) => setFilter(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">全部来源</option>
          {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button className="btn" onClick={load}>刷新</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>运行 #</th><th>来源</th><th>触发</th><th>状态</th>
              <th>页面</th><th>附件</th><th>变更</th><th>robots拦截</th>
              <th>开始</th><th>结束</th><th>信息</th><th>快照</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{sourceName(r.source_id)}</td>
                <td>{r.trigger === 'manual' ? '手动' : '定时'}</td>
                <td><span className={'badge ' + runStatusBadge[r.status]}>{runStatusLabel[r.status]}</span></td>
                <td>{r.pages_fetched}</td>
                <td>{r.attachments_fetched}</td>
                <td>{r.changes_detected}</td>
                <td>{r.robots_blocked}</td>
                <td className="muted">{fmtTime(r.started_at)}</td>
                <td className="muted">{fmtTime(r.finished_at)}</td>
                <td className="muted" style={{ maxWidth: 240 }}>{r.message}</td>
                <td><span className="link" onClick={() => openSnaps(r.id)}>查看</span></td>
              </tr>
            ))}
            {runs.length === 0 && <tr><td colSpan={12} className="empty">暂无采集记录。</td></tr>}
          </tbody>
        </table>
      </div>

      {snapRun !== null && (
        <div className="modal-overlay" onClick={() => setSnapRun(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>运行 #{snapRun} 的快照（可追溯留痕）</h3>
            {snaps?.length ? snaps.map((s) => (
              <div key={s.id} className="card" style={{ marginBottom: 10 }}>
                <div>
                  <span className={'badge ' + (s.kind === 'page' ? 'badge-blue' : 'badge-amber')}>
                    {s.kind === 'page' ? '页面' : '附件'}
                  </span>{' '}
                  <span className="mono">{s.filename || s.url}</span>
                </div>
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  HTTP {s.http_status} · {s.content_type || '未知类型'} · hash {s.content_hash.slice(0, 12)} · {fmtTime(s.captured_at)}
                </div>
                <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', fontSize: 12, maxHeight: 140, overflow: 'auto' }}>
                  {s.text_excerpt || '（无文本摘要）'}
                </pre>
              </div>
            )) : <div className="empty">该运行没有快照。</div>}
            <div className="toolbar">
              <div className="spacer" />
              <button className="btn" onClick={() => setSnapRun(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
