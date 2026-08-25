import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Assessment, ChangeItem, ImpactLevel, fmtDate } from '../types'
import { changeTypeLabel } from './ChangesPage'

export const impactLevelLabel: Record<ImpactLevel, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

interface EditState {
  business_area: string
  impact_level: ImpactLevel
  analysis: string
  recommendation: string
  created_by: string
}

export default function ImpactPage() {
  const [changes, setChanges] = useState<ChangeItem[]>([])
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [selectedChangeId, setSelectedChangeId] = useState<string>('')
  const [form, setForm] = useState<EditState>({
    business_area: '',
    impact_level: 'medium',
    analysis: '',
    recommendation: '',
    created_by: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<EditState | null>(null)
  const [loading, setLoading] = useState(true)

  const loadAssessments = useCallback(async () => {
    try {
      const data = await api<Assessment[]>('/assessments')
      setAssessments(data)
    } catch (e) {
      alert(e instanceof Error ? e.message : '加载研判列表失败')
    }
  }, [])

  useEffect(() => {
    Promise.all([
      api<ChangeItem[]>('/changes'),
      api<Assessment[]>('/assessments'),
    ])
      .then(([c, a]) => {
        setChanges(c)
        setAssessments(a)
      })
      .catch((e) => alert(e instanceof Error ? e.message : '加载数据失败'))
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async () => {
    if (!selectedChangeId) {
      alert('请先选择一个变更')
      return
    }
    if (!form.business_area.trim() || !form.analysis.trim() || !form.created_by.trim()) {
      alert('请填写业务线、分析与填写人')
      return
    }
    setSubmitting(true)
    try {
      await api<Assessment>('/assessments', {
        method: 'POST',
        body: JSON.stringify({
          change_id: Number(selectedChangeId),
          business_area: form.business_area.trim(),
          impact_level: form.impact_level,
          analysis: form.analysis,
          recommendation: form.recommendation.trim() || null,
          created_by: form.created_by.trim(),
        }),
      })
      setForm({ business_area: '', impact_level: 'medium', analysis: '', recommendation: '', created_by: form.created_by })
      await loadAssessments()
      alert('研判已提交')
    } catch (e) {
      alert(e instanceof Error ? e.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const startEdit = (a: Assessment) => {
    setEditingId(a.id)
    setEditForm({
      business_area: a.business_area,
      impact_level: a.impact_level,
      analysis: a.analysis,
      recommendation: a.recommendation ?? '',
      created_by: a.created_by,
    })
  }

  const handleSaveEdit = async () => {
    if (editingId === null || !editForm) return
    try {
      await api<Assessment>(`/assessments/${editingId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          business_area: editForm.business_area,
          impact_level: editForm.impact_level,
          analysis: editForm.analysis,
          recommendation: editForm.recommendation.trim() || null,
          created_by: editForm.created_by,
        }),
      })
      setEditingId(null)
      setEditForm(null)
      await loadAssessments()
    } catch (e) {
      alert(e instanceof Error ? e.message : '保存失败')
    }
  }

  return (
    <div>
      <h1 className="page-title">影响研判</h1>

      <div className="card">
        <h2 className="section-title" style={{ marginTop: 0 }}>新建研判</h2>
        <div className="form-grid">
          <div className="form-item full">
            <label>选择变更</label>
            <select value={selectedChangeId} onChange={(e) => setSelectedChangeId(e.target.value)}>
              <option value="">请选择变更…</option>
              {changes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.regulation_title} - {changeTypeLabel[c.change_type] ?? c.change_type} - {fmtDate(c.detected_at)}
                </option>
              ))}
            </select>
          </div>
          <div className="form-item">
            <label>业务线</label>
            <input type="text" value={form.business_area} onChange={(e) => setForm({ ...form, business_area: e.target.value })} />
          </div>
          <div className="form-item">
            <label>影响等级</label>
            <select value={form.impact_level} onChange={(e) => setForm({ ...form, impact_level: e.target.value as ImpactLevel })}>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </div>
          <div className="form-item">
            <label>填写人</label>
            <input type="text" value={form.created_by} onChange={(e) => setForm({ ...form, created_by: e.target.value })} />
          </div>
          <div className="form-item full">
            <label>分析</label>
            <textarea value={form.analysis} onChange={(e) => setForm({ ...form, analysis: e.target.value })} />
          </div>
          <div className="form-item full">
            <label>建议</label>
            <textarea value={form.recommendation} onChange={(e) => setForm({ ...form, recommendation: e.target.value })} />
          </div>
        </div>
        <button className="btn primary" disabled={submitting} onClick={handleSubmit}>
          {submitting ? '提交中…' : '提交研判'}
        </button>
      </div>

      <h2 className="section-title">已有研判</h2>
      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <p className="muted" style={{ padding: 16 }}>加载中…</p>
        ) : assessments.length === 0 ? (
          <p className="muted" style={{ padding: 16 }}>暂无研判记录。</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>法规标题</th>
                <th>业务线</th>
                <th>影响等级</th>
                <th>分析摘要</th>
                <th>填写人</th>
                <th>时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((a) =>
                editingId === a.id && editForm ? (
                  <tr key={a.id}>
                    <td>{a.regulation_title}</td>
                    <td>
                      <input type="text" value={editForm.business_area} onChange={(e) => setEditForm({ ...editForm, business_area: e.target.value })} style={{ width: '100%' }} />
                    </td>
                    <td>
                      <select value={editForm.impact_level} onChange={(e) => setEditForm({ ...editForm, impact_level: e.target.value as ImpactLevel })}>
                        <option value="high">高</option>
                        <option value="medium">中</option>
                        <option value="low">低</option>
                      </select>
                    </td>
                    <td>
                      <textarea value={editForm.analysis} onChange={(e) => setEditForm({ ...editForm, analysis: e.target.value })} style={{ width: '100%', minHeight: 60 }} />
                      <textarea value={editForm.recommendation} placeholder="建议（可空）" onChange={(e) => setEditForm({ ...editForm, recommendation: e.target.value })} style={{ width: '100%', minHeight: 40, marginTop: 4 }} />
                    </td>
                    <td>
                      <input type="text" value={editForm.created_by} onChange={(e) => setEditForm({ ...editForm, created_by: e.target.value })} style={{ width: '100%' }} />
                    </td>
                    <td>{fmtDate(a.created_at)}</td>
                    <td>
                      <div className="btn-row">
                        <button className="btn small primary" onClick={handleSaveEdit}>保存</button>
                        <button className="btn small" onClick={() => { setEditingId(null); setEditForm(null) }}>取消</button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={a.id}>
                    <td>{a.regulation_title}</td>
                    <td>{a.business_area}</td>
                    <td><span className={`badge badge-${a.impact_level}`}>{impactLevelLabel[a.impact_level]}</span></td>
                    <td className="text-clip" title={a.analysis}>{a.analysis}</td>
                    <td>{a.created_by}</td>
                    <td>{fmtDate(a.created_at)}</td>
                    <td>
                      <button className="btn small" onClick={() => startEdit(a)}>编辑</button>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
