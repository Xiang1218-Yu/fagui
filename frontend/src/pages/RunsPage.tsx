import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Run, Source, fmtDate } from '../types'

const statusLabel: Record<Run['status'], string> = {
  running: '进行中',
  success: '成功',
  failed: '失败',
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [sourceId, setSourceId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const loadRuns = useCallback(async (sid: string, silent = false) => {
    if (!silent) setLoading(true)
    try {
      const query = sid ? `?source_id=${sid}&limit=50` : '?limit=50'
      const data = await api<Run[]>(`/runs${query}`)
      setRuns(data)
    } catch (e) {
      if (!silent) alert(e instanceof Error ? e.message : '加载运行记录失败')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    api<Source[]>('/sources')
      .then(setSources)
      .catch((e) => alert(e instanceof Error ? e.message : '加载来源列表失败'))
  }, [])

  useEffect(() => {
    loadRuns(sourceId)
    const timer = setInterval(() => loadRuns(sourceId, true), 10000)
    return () => clearInterval(timer)
  }, [sourceId, loadRuns])

  return (
    <div>
      <h1 className="page-title">采集运行</h1>
      <div className="toolbar">
        <label>按来源筛选：</label>
        <select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
          <option value="">全部来源</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <span className="muted">每 10 秒自动刷新</span>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <p className="muted" style={{ padding: 16 }}>加载中…</p>
        ) : runs.length === 0 ? (
          <p className="muted" style={{ padding: 16 }}>暂无运行记录。</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>来源</th>
                <th>状态</th>
                <th>开始时间</th>
                <th>结束时间</th>
                <th>抓取页数</th>
                <th>附件数</th>
                <th>检出变更数</th>
                <th>错误信息</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.source_name}</td>
                  <td><span className={`badge badge-${r.status}`}>{statusLabel[r.status] ?? r.status}</span></td>
                  <td>{fmtDate(r.started_at)}</td>
                  <td>{fmtDate(r.finished_at)}</td>
                  <td>{r.pages_fetched}</td>
                  <td>{r.attachments_fetched}</td>
                  <td>{r.changes_detected}</td>
                  <td>
                    {r.error ? (
                      <span
                        className="error-text"
                        title={r.error}
                        style={{ cursor: 'pointer', textDecoration: 'underline dotted' }}
                        onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                      >
                        {expandedId === r.id ? r.error : '查看错误'}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
