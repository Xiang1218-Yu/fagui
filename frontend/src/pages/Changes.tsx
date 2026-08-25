import { useEffect, useMemo, useState } from 'react'
import { changeSnapshots, listChanges, listDocuments } from '../api'
import type { ChangeEvent, Document, Snapshot } from '../types'
import { changeTypeBadge, changeTypeLabel, fmtTime } from '../labels'

function DiffView({ diff }: { diff: string }) {
  if (!diff) return <div className="muted">无逐行差异（首次采集或二进制附件）。</div>
  return (
    <div className="diff card" style={{ maxHeight: 360, overflow: 'auto' }}>
      {diff.split('\n').map((line, i) => {
        let cls = 'ctx'
        if (line.startsWith('+') && !line.startsWith('+++')) cls = 'add'
        else if (line.startsWith('-') && !line.startsWith('---')) cls = 'del'
        return <span key={i} className={cls}>{line || ' '}</span>
      })}
    </div>
  )
}

export default function Changes() {
  const [changes, setChanges] = useState<ChangeEvent[]>([])
  const [docs, setDocs] = useState<Document[]>([])
  const [typeFilter, setTypeFilter] = useState('')
  const [detail, setDetail] = useState<{
    change: ChangeEvent
    data: { old: Snapshot | null; new: Snapshot | null; old_text: string; new_text: string; diff_text: string }
  } | null>(null)

  const load = () =>
    listChanges(typeFilter ? { change_type: typeFilter } : undefined).then(setChanges).catch(() => {})
  useEffect(() => { listDocuments().then(setDocs).catch(() => {}) }, [])
  useEffect(() => { load() }, [typeFilter])

  const docMap = useMemo(() => {
    const m: Record<number, Document> = {}
    docs.forEach((d) => (m[d.id] = d))
    return m
  }, [docs])

  const open = async (c: ChangeEvent) => {
    const data = await changeSnapshots(c.id)
    setDetail({ change: c, data })
  }

  return (
    <div>
      <h2 className="page-title">变更对比</h2>
      <p className="page-desc">系统识别正文与附件的变化，逐条列出变更类型、相似度与差异，并支持新旧快照并排对比。</p>

      <div className="toolbar">
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">全部类型</option>
          <option value="new">新增法规</option>
          <option value="body_changed">正文变化</option>
          <option value="attachment_changed">附件变化</option>
        </select>
        <button className="btn" onClick={load}>刷新</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>#</th><th>法规文档</th><th>变更类型</th><th>相似度</th><th>摘要</th><th>时间</th><th></th>
            </tr>
          </thead>
          <tbody>
            {changes.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td style={{ maxWidth: 240 }}>{docMap[c.document_id]?.title ?? `文档#${c.document_id}`}</td>
                <td><span className={'badge ' + changeTypeBadge[c.change_type]}>{changeTypeLabel[c.change_type]}</span></td>
                <td>{c.change_type === 'new' ? '—' : `${(c.similarity * 100).toFixed(0)}%`}</td>
                <td className="muted" style={{ maxWidth: 340 }}>{c.summary}</td>
                <td className="muted">{fmtTime(c.created_at)}</td>
                <td><span className="link" onClick={() => open(c)}>对比</span></td>
              </tr>
            ))}
            {changes.length === 0 && <tr><td colSpan={7} className="empty">暂无变更记录。</td></tr>}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal" style={{ width: 900 }} onClick={(e) => e.stopPropagation()}>
            <h3>变更 #{detail.change.id} · {changeTypeLabel[detail.change.change_type]}</h3>
            <p className="muted">{detail.change.summary}</p>
            <h4>逐行差异</h4>
            <DiffView diff={detail.data.diff_text} />
            <h4>快照并排对比</h4>
            <div className="snapshot-cols">
              <div>
                <div className="muted" style={{ marginBottom: 6 }}>
                  旧快照 {detail.data.old ? `#${detail.data.old.id} · ${fmtTime(detail.data.old.captured_at)}` : '（无）'}
                </div>
                <pre>{detail.data.old_text || '（无历史版本）'}</pre>
              </div>
              <div>
                <div className="muted" style={{ marginBottom: 6 }}>
                  新快照 {detail.data.new ? `#${detail.data.new.id} · ${fmtTime(detail.data.new.captured_at)}` : ''}
                </div>
                <pre>{detail.data.new_text || '（无）'}</pre>
              </div>
            </div>
            <div className="toolbar">
              <div className="spacer" />
              <button className="btn" onClick={() => setDetail(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
