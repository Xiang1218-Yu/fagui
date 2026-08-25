import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { ChangeItem, fmtDate, useCurrentUser } from '../types'
import { changeStatusLabel, changeTypeLabel } from './ChangesPage'

type View = 'pending' | 'reviewed'

interface ReviewTarget {
  change: ChangeItem
  decision: 'confirmed' | 'dismissed'
}

export default function ReviewPage() {
  const user = useCurrentUser()
  const canReview = user?.role !== 'viewer'
  const [view, setView] = useState<View>('pending')
  const [pending, setPending] = useState<ChangeItem[]>([])
  const [reviewed, setReviewed] = useState<ChangeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [target, setTarget] = useState<ReviewTarget | null>(null)
  const [reviewer, setReviewer] = useState('')
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async (v: View) => {
    setLoading(true)
    try {
      if (v === 'pending') {
        const data = await api<ChangeItem[]>('/changes?status=pending_review')
        setPending(data)
      } else {
        const [confirmed, dismissed] = await Promise.all([
          api<ChangeItem[]>('/changes?status=confirmed'),
          api<ChangeItem[]>('/changes?status=dismissed'),
        ])
        setReviewed(
          [...confirmed, ...dismissed].sort(
            (a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
          ),
        )
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : '加载复核队列失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(view)
  }, [view, load])

  const openModal = (change: ChangeItem, decision: 'confirmed' | 'dismissed') => {
    setTarget({ change, decision })
    setReviewer('')
    setComment('')
  }

  const handleSubmitReview = async () => {
    if (!target) return
    if (!reviewer.trim()) {
      alert('请填写复核人姓名')
      return
    }
    setSubmitting(true)
    try {
      await api<ChangeItem>(`/changes/${target.change.id}/review`, {
        method: 'POST',
        body: JSON.stringify({
          reviewer: reviewer.trim(),
          decision: target.decision,
          comment: comment.trim() || undefined,
        }),
      })
      setPending((prev) => prev.filter((c) => c.id !== target.change.id))
      setTarget(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : '提交复核失败')
    } finally {
      setSubmitting(false)
    }
  }

  const list = view === 'pending' ? pending : reviewed

  return (
    <div>
      <h1 className="page-title">复核队列</h1>
      <div className="page-tabs">
        <button className={view === 'pending' ? 'active' : ''} onClick={() => setView('pending')}>
          待复核
        </button>
        <button className={view === 'reviewed' ? 'active' : ''} onClick={() => setView('reviewed')}>
          全部已复核
        </button>
      </div>

      {loading ? (
        <p className="muted">加载中…</p>
      ) : list.length === 0 ? (
        <p className="muted">{view === 'pending' ? '复核队列为空，暂无待复核变更。' : '暂无已复核记录。'}</p>
      ) : (
        <div className="review-cards">
          {list.map((c) => (
            <div key={c.id} className="review-card">
              <div className="review-card-head">
                <span className="review-card-title">{c.regulation_title}</span>
                <span className={`badge badge-${c.change_type}`}>{changeTypeLabel[c.change_type]}</span>
                <span className={`badge badge-${c.status}`}>{changeStatusLabel[c.status]}</span>
                <span className="muted">来源：{c.source_name}</span>
                <span className="muted">检出：{fmtDate(c.detected_at)}</span>
              </div>
              <p className="muted" style={{ margin: '0 0 12px' }}>{c.diff_summary || '暂无差异摘要'}</p>
              <div className="btn-row">
                <Link to={`/changes/${c.id}`}>
                  <button className="btn small">查看详情</button>
                </Link>
                {view === 'pending' && canReview && (
                  <>
                    <button className="btn small primary" onClick={() => openModal(c, 'confirmed')}>确认</button>
                    <button className="btn small danger" onClick={() => openModal(c, 'dismissed')}>驳回</button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {target && (
        <div className="modal-mask" onClick={() => !submitting && setTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>
              {target.decision === 'confirmed' ? '确认变更' : '驳回变更'}：{target.change.regulation_title}
            </h3>
            <div className="form-item" style={{ marginBottom: 12 }}>
              <label>复核人姓名</label>
              <input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
            </div>
            <div className="form-item">
              <label>备注（可空）</label>
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
            </div>
            <div className="modal-actions">
              <button className="btn" disabled={submitting} onClick={() => setTarget(null)}>取消</button>
              <button className="btn primary" disabled={submitting} onClick={handleSubmitReview}>
                {submitting ? '提交中…' : '提交'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
