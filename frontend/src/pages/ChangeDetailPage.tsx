import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Assessment, ChangeDetail, fmtDate } from '../types'
import { changeStatusLabel, changeTypeLabel } from './ChangesPage'
import { impactLevelLabel } from './ImpactPage'

export default function ChangeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [detail, setDetail] = useState<ChangeDetail | null>(null)
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      api<ChangeDetail>(`/changes/${id}`),
      api<Assessment[]>(`/assessments?change_id=${id}`).catch(() => [] as Assessment[]),
    ])
      .then(([d, a]) => {
        setDetail(d)
        setAssessments(a)
      })
      .catch((e) => alert(e instanceof Error ? e.message : '加载变更详情失败'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p className="muted">加载中…</p>
  if (!detail) return <p className="muted">未找到该变更。<Link to="/changes">返回列表</Link></p>

  const diffLines = detail.unified_diff ? detail.unified_diff.split('\n') : []

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{detail.regulation_title}</h1>
        <Link to="/changes" className="muted">← 返回变更列表</Link>
      </div>

      <div className="card">
        <div className="btn-row" style={{ alignItems: 'center' }}>
          <span className={`badge badge-${detail.change_type}`}>{changeTypeLabel[detail.change_type]}</span>
          <span className={`badge badge-${detail.status}`}>{changeStatusLabel[detail.status]}</span>
          <span className="muted">来源：{detail.source_name}</span>
          <span className="muted">检出时间:{fmtDate(detail.detected_at)}</span>
          <a href={detail.document_url} target="_blank" rel="noreferrer">原文链接</a>
        </div>
        <p style={{ marginBottom: 0 }}>{detail.diff_summary || '暂无差异摘要'}</p>
        {detail.review ? (
          <p className="muted" style={{ marginTop: 10, marginBottom: 0 }}>
            复核信息：{detail.review.reviewer} 于 {fmtDate(detail.review.decided_at)}{' '}
            {detail.review.decision === 'confirmed' ? '确认' : '驳回'}
            {detail.review.comment ? `，备注：${detail.review.comment}` : ''}
          </p>
        ) : (
          <p className="muted" style={{ marginTop: 10, marginBottom: 0 }}>尚未复核</p>
        )}
      </div>

      <h2 className="section-title">正文对比</h2>
      <div className="text-compare">
        <div>
          <div className="pane-title">变更前</div>
          <div className="pane">{detail.old_text ?? '（无旧文本，可能为新增法规）'}</div>
        </div>
        <div>
          <div className="pane-title">变更后</div>
          <div className="pane">{detail.new_text ?? '（无新文本）'}</div>
        </div>
      </div>

      <h2 className="section-title">Unified Diff</h2>
      {diffLines.length > 0 ? (
        <div className="diff-box">
          {diffLines.map((line, i) => {
            let cls = 'diff-line'
            if (line.startsWith('+') && !line.startsWith('+++')) cls += ' diff-add'
            else if (line.startsWith('-') && !line.startsWith('---')) cls += ' diff-del'
            else if (line.startsWith('@@') || line.startsWith('+++') || line.startsWith('---')) cls += ' diff-meta'
            return <span key={i} className={cls}>{line || ' '}</span>
          })}
        </div>
      ) : (
        <p className="muted">暂无 diff 内容。</p>
      )}

      <h2 className="section-title">附件列表</h2>
      {detail.attachments.length === 0 ? (
        <p className="muted">无附件。</p>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>URL</th>
                <th>内容哈希</th>
              </tr>
            </thead>
            <tbody>
              {detail.attachments.map((a) => (
                <tr key={a.id}>
                  <td>{a.filename}</td>
                  <td className="text-clip"><a href={a.url} target="_blank" rel="noreferrer">{a.url}</a></td>
                  <td className="text-clip" title={a.content_hash}>{a.content_hash}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="section-title">影响研判</h2>
      {assessments.length === 0 ? (
        <p className="muted">该变更暂无影响研判，可前往<Link to="/impact">影响研判</Link>页面填写。</p>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>业务线</th>
                <th>影响等级</th>
                <th>分析</th>
                <th>建议</th>
                <th>填写人</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((a) => (
                <tr key={a.id}>
                  <td>{a.business_area}</td>
                  <td><span className={`badge badge-${a.impact_level}`}>{impactLevelLabel[a.impact_level]}</span></td>
                  <td className="text-clip" title={a.analysis}>{a.analysis}</td>
                  <td className="text-clip" title={a.recommendation ?? ''}>{a.recommendation ?? '—'}</td>
                  <td>{a.created_by}</td>
                  <td>{fmtDate(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
