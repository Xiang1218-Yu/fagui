import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { ChangeItem, fmtDate } from '../types'

export const changeTypeLabel: Record<ChangeItem['change_type'], string> = {
  new: '新增法规',
  content_updated: '正文更新',
  attachment_updated: '附件更新',
}

export const changeStatusLabel: Record<ChangeItem['status'], string> = {
  pending_review: '待复核',
  confirmed: '已确认',
  dismissed: '已驳回',
}

export default function ChangesPage() {
  const [changes, setChanges] = useState<ChangeItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api<ChangeItem[]>('/changes')
      .then(setChanges)
      .catch((e) => alert(e instanceof Error ? e.message : '加载变更列表失败'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h1 className="page-title">变更对比</h1>
      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <p className="muted" style={{ padding: 16 }}>加载中…</p>
        ) : changes.length === 0 ? (
          <p className="muted" style={{ padding: 16 }}>暂无检出的变更。</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>法规标题</th>
                <th>来源</th>
                <th>变更类型</th>
                <th>状态</th>
                <th>检出时间</th>
                <th>差异摘要</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((c) => (
                <tr key={c.id} className="clickable" onClick={() => navigate(`/changes/${c.id}`)}>
                  <td>{c.regulation_title}</td>
                  <td>{c.source_name}</td>
                  <td><span className={`badge badge-${c.change_type}`}>{changeTypeLabel[c.change_type] ?? c.change_type}</span></td>
                  <td><span className={`badge badge-${c.status}`}>{changeStatusLabel[c.status] ?? c.status}</span></td>
                  <td>{fmtDate(c.detected_at)}</td>
                  <td className="text-clip" title={c.diff_summary}>{c.diff_summary || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
