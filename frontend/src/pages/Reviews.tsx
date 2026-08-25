import { useEffect, useState } from 'react'
import { assignReview, changeSnapshots, decideReview, listReviews } from '../api'
import type { ImpactLevel, ReviewItem, ReviewStatus } from '../types'
import {
  changeTypeLabel,
  fmtTime,
  impactBadge,
  impactLabel,
  reviewStatusBadge,
  reviewStatusLabel,
} from '../labels'

interface Props { onChange?: () => void }

export default function Reviews({ onChange }: Props) {
  const [items, setItems] = useState<ReviewItem[]>([])
  const [filter, setFilter] = useState<string>('pending')
  const [active, setActive] = useState<ReviewItem | null>(null)
  const [diff, setDiff] = useState('')
  const [form, setForm] = useState({
    status: 'confirmed' as ReviewStatus,
    impact_level: 'medium' as ImpactLevel,
    decision_note: '',
    impact_note: '',
    affected_business: '',
    reviewed_by: 'analyst',
  })

  const load = () => listReviews(filter || undefined).then(setItems).catch(() => {})
  useEffect(() => { load() }, [filter])

  const open = async (r: ReviewItem) => {
    setActive(r)
    setForm({
      status: 'confirmed',
      impact_level: r.impact_level === 'unassessed' ? 'medium' : r.impact_level,
      decision_note: r.decision_note,
      impact_note: r.impact_note,
      affected_business: r.affected_business,
      reviewed_by: r.reviewed_by || 'analyst',
    })
    setDiff('')
    if (r.change) {
      const d = await changeSnapshots(r.change.id)
      setDiff(d.diff_text)
    }
  }

  const submit = async () => {
    if (!active) return
    await decideReview(active.id, form)
    setActive(null)
    load()
    onChange?.()
  }

  const assign = async (r: ReviewItem) => {
    const who = prompt('指派给（用户名）', r.assignee || 'analyst')
    if (who == null) return
    await assignReview(r.id, who)
    load()
  }

  return (
    <div>
      <h2 className="page-title">复核队列 / 影响研判</h2>
      <p className="page-desc">
        待确认变更进入人工复核队列；分析师确认或忽略，并记录影响等级、受影响业务与研判结论，形成可追溯的处置闭环。
      </p>

      <div className="toolbar">
        {['pending', 'confirmed', 'dismissed', ''].map((s) => (
          <button
            key={s || 'all'}
            className={'btn' + (filter === s ? ' btn-primary' : '')}
            onClick={() => setFilter(s)}
          >
            {s ? reviewStatusLabel[s as ReviewStatus] : '全部'}
          </button>
        ))}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>#</th><th>变更</th><th>类型</th><th>状态</th><th>影响</th>
              <th>受影响业务</th><th>负责人</th><th>时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td className="muted" style={{ maxWidth: 300 }}>{r.change?.summary ?? `变更#${r.change_id}`}</td>
                <td>{r.change ? changeTypeLabel[r.change.change_type] : '—'}</td>
                <td><span className={'badge ' + reviewStatusBadge[r.status]}>{reviewStatusLabel[r.status]}</span></td>
                <td><span className={'badge ' + impactBadge[r.impact_level]}>{impactLabel[r.impact_level]}</span></td>
                <td className="muted">{r.affected_business || '—'}</td>
                <td>{r.assignee || <span className="link" onClick={() => assign(r)}>指派</span>}</td>
                <td className="muted">{fmtTime(r.reviewed_at || r.created_at)}</td>
                <td>
                  {r.status === 'pending'
                    ? <span className="link" onClick={() => open(r)}>研判</span>
                    : <span className="link" onClick={() => open(r)}>查看</span>}
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={9} className="empty">队列为空。</td></tr>}
          </tbody>
        </table>
      </div>

      {active && (
        <div className="modal-overlay" onClick={() => setActive(null)}>
          <div className="modal" style={{ width: 760 }} onClick={(e) => e.stopPropagation()}>
            <h3>影响研判 · 变更 #{active.change_id}</h3>
            <p className="muted">{active.change?.summary}</p>
            {diff && (
              <div className="diff card" style={{ maxHeight: 220, overflow: 'auto' }}>
                {diff.split('\n').map((l, i) => {
                  let cls = 'ctx'
                  if (l.startsWith('+') && !l.startsWith('+++')) cls = 'add'
                  else if (l.startsWith('-') && !l.startsWith('---')) cls = 'del'
                  return <span key={i} className={cls}>{l || ' '}</span>
                })}
              </div>
            )}
            <div className="form-grid">
              <div className="form-row">
                <label>复核结论</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as ReviewStatus })}>
                  <option value="confirmed">确认（需处理）</option>
                  <option value="dismissed">忽略（无需处理）</option>
                </select>
              </div>
              <div className="form-row">
                <label>影响等级</label>
                <select value={form.impact_level} onChange={(e) => setForm({ ...form, impact_level: e.target.value as ImpactLevel })}>
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <label>受影响业务</label>
              <input value={form.affected_business} onChange={(e) => setForm({ ...form, affected_business: e.target.value })} placeholder="如：信贷审批、KYC 流程" />
            </div>
            <div className="form-row">
              <label>影响研判结论</label>
              <textarea value={form.impact_note} onChange={(e) => setForm({ ...form, impact_note: e.target.value })} placeholder="说明本次变更对业务的具体影响与处置建议" />
            </div>
            <div className="form-row">
              <label>复核备注</label>
              <textarea value={form.decision_note} onChange={(e) => setForm({ ...form, decision_note: e.target.value })} />
            </div>
            <div className="form-row">
              <label>复核人</label>
              <input value={form.reviewed_by} onChange={(e) => setForm({ ...form, reviewed_by: e.target.value })} />
            </div>
            <div className="toolbar">
              <div className="spacer" />
              <button className="btn" onClick={() => setActive(null)}>取消</button>
              <button className="btn btn-primary" onClick={submit}>提交研判</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
