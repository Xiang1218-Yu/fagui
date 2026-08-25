import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Source, fmtDate, useCurrentUser } from '../types'

interface FormState {
  name: string
  base_url: string
  allowed_paths: string
  frequency_minutes: number
  enabled: boolean
  respect_robots: boolean
  max_pages: number
}

const emptyForm: FormState = {
  name: '',
  base_url: '',
  allowed_paths: '',
  frequency_minutes: 60,
  enabled: true,
  respect_robots: true,
  max_pages: 20,
}

export default function SourcesPage() {
  const user = useCurrentUser()
  const isAdmin = user?.role === 'admin'
  const canRun = user?.role !== 'viewer'
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [runningId, setRunningId] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api<Source[]>('/sources')
      setSources(data)
    } catch (e) {
      alert(e instanceof Error ? e.message : '加载来源列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const startEdit = (s: Source) => {
    setEditingId(s.id)
    setForm({
      name: s.name,
      base_url: s.base_url,
      allowed_paths: s.allowed_paths.join(','),
      frequency_minutes: s.frequency_minutes,
      enabled: s.enabled,
      respect_robots: s.respect_robots,
      max_pages: s.max_pages,
    })
    setShowForm(true)
  }

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
    setShowForm(false)
  }

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.base_url.trim()) {
      alert('请填写名称与 base_url')
      return
    }
    setSubmitting(true)
    const payload = {
      name: form.name.trim(),
      base_url: form.base_url.trim(),
      allowed_paths: form.allowed_paths
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean),
      frequency_minutes: Number(form.frequency_minutes) || 60,
      enabled: form.enabled,
      respect_robots: form.respect_robots,
      max_pages: Number(form.max_pages) || 20,
    }
    try {
      if (editingId !== null) {
        await api<Source>(`/sources/${editingId}`, { method: 'PATCH', body: JSON.stringify(payload) })
      } else {
        await api<Source>('/sources', { method: 'POST', body: JSON.stringify(payload) })
      }
      resetForm()
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (s: Source) => {
    if (!window.confirm(`确定删除来源「${s.name}」吗？`)) return
    try {
      await api(`/sources/${s.id}`, { method: 'DELETE' })
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  const handleRun = async (s: Source) => {
    setRunningId(s.id)
    try {
      await api<{ run_id: number | null; status: string }>(`/sources/${s.id}/run`, { method: 'POST' })
      alert(`已触发采集：${s.name}`)
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '触发采集失败')
    } finally {
      setRunningId(null)
    }
  }

  const toggleEnabled = async (s: Source) => {
    try {
      await api<Source>(`/sources/${s.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled: !s.enabled }),
      })
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '更新失败')
    }
  }

  return (
    <div>
      <h1 className="page-title">来源管理</h1>
      <div className="toolbar">
        {isAdmin && (
          <button className="btn primary" onClick={() => { resetForm(); setShowForm(true) }}>
            新建来源
          </button>
        )}
      </div>

      {showForm && (
        <div className="card">
          <h2 className="section-title" style={{ marginTop: 0 }}>
            {editingId !== null ? '编辑来源' : '新建来源'}
          </h2>
          <div className="form-grid">
            <div className="form-item">
              <label>名称</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="form-item">
              <label>base_url</label>
              <input type="url" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
            </div>
            <div className="form-item">
              <label>允许路径（逗号分隔）</label>
              <input type="text" value={form.allowed_paths} onChange={(e) => setForm({ ...form, allowed_paths: e.target.value })} placeholder="/laws,/regulations" />
            </div>
            <div className="form-item">
              <label>采集频率（分钟）</label>
              <input type="number" min={1} value={form.frequency_minutes} onChange={(e) => setForm({ ...form, frequency_minutes: Number(e.target.value) })} />
            </div>
            <div className="form-item">
              <label>最大抓取页数</label>
              <input type="number" min={1} value={form.max_pages} onChange={(e) => setForm({ ...form, max_pages: Number(e.target.value) })} />
            </div>
            <div className="form-item checkbox-item">
              <input id="f-enabled" type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
              <label htmlFor="f-enabled">启用</label>
            </div>
            <div className="form-item checkbox-item">
              <input id="f-robots" type="checkbox" checked={form.respect_robots} onChange={(e) => setForm({ ...form, respect_robots: e.target.checked })} />
              <label htmlFor="f-robots">遵循 robots</label>
            </div>
          </div>
          <div className="btn-row">
            <button className="btn primary" disabled={submitting} onClick={handleSubmit}>
              {submitting ? '提交中…' : '保存'}
            </button>
            <button className="btn" onClick={resetForm}>取消</button>
          </div>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <p className="muted" style={{ padding: 16 }}>加载中…</p>
        ) : sources.length === 0 ? (
          <p className="muted" style={{ padding: 16 }}>暂无来源，请点击"新建来源"添加。</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>base_url</th>
                <th>允许路径</th>
                <th>频率(分钟)</th>
                <th>启用</th>
                <th>遵循robots</th>
                <th>最近运行时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td className="text-clip" title={s.base_url}>{s.base_url}</td>
                  <td className="text-clip" title={s.allowed_paths.join(', ')}>{s.allowed_paths.join(', ') || '—'}</td>
                  <td>{s.frequency_minutes}</td>
                  <td>
                    <label className="switch">
                      <input type="checkbox" checked={s.enabled} onChange={() => toggleEnabled(s)} />
                      <span className="muted">{s.enabled ? '开' : '关'}</span>
                    </label>
                  </td>
                  <td>{s.respect_robots ? '是' : '否'}</td>
                  <td>{fmtDate(s.last_run_at)}</td>
                  <td>
                    <div className="btn-row">
                      {canRun && (
                        <button className="btn small" disabled={runningId === s.id} onClick={() => handleRun(s)}>
                          {runningId === s.id ? '触发中…' : '立即采集'}
                        </button>
                      )}
                      {isAdmin && (
                        <>
                          <button className="btn small" onClick={() => startEdit(s)}>编辑</button>
                          <button className="btn small danger" onClick={() => handleDelete(s)}>删除</button>
                        </>
                      )}
                      {!canRun && !isAdmin && <span className="muted">—</span>}
                    </div>
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
