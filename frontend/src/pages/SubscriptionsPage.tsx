import { ChangeEvent, useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Notification, Source, Subscription, fmtDate, useCurrentUser } from '../types'

interface FormState {
  name: string
  channel: 'webhook' | 'email'
  target: string
  keywords: string
  source_ids: number[]
  enabled: boolean
}

const emptyForm: FormState = {
  name: '',
  channel: 'webhook',
  target: '',
  keywords: '',
  source_ids: [],
  enabled: true,
}

export default function SubscriptionsPage() {
  const user = useCurrentUser()
  const canEdit = user?.role !== 'viewer'
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const loadAll = useCallback(async () => {
    try {
      const [subs, notifs, srcs] = await Promise.all([
        api<Subscription[]>('/subscriptions'),
        api<Notification[]>('/notifications'),
        api<Source[]>('/sources'),
      ])
      setSubscriptions(subs)
      setNotifications(notifs)
      setSources(srcs)
    } catch (e) {
      alert(e instanceof Error ? e.message : '加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
    setShowForm(false)
  }

  const startEdit = (s: Subscription) => {
    setEditingId(s.id)
    setForm({
      name: s.name,
      channel: s.channel,
      target: s.target,
      keywords: s.keywords.join(','),
      source_ids: s.source_ids,
      enabled: s.enabled,
    })
    setShowForm(true)
  }

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.target.trim()) {
      alert('请填写名称与目标地址')
      return
    }
    setSubmitting(true)
    const payload = {
      name: form.name.trim(),
      channel: form.channel,
      target: form.target.trim(),
      keywords: form.keywords.split(',').map((k) => k.trim()).filter(Boolean),
      source_ids: form.source_ids,
      enabled: form.enabled,
    }
    try {
      if (editingId !== null) {
        await api<Subscription>(`/subscriptions/${editingId}`, { method: 'PATCH', body: JSON.stringify(payload) })
      } else {
        await api<Subscription>('/subscriptions', { method: 'POST', body: JSON.stringify(payload) })
      }
      resetForm()
      await loadAll()
    } catch (e) {
      alert(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (s: Subscription) => {
    if (!window.confirm(`确定删除订阅「${s.name}」吗？`)) return
    try {
      await api(`/subscriptions/${s.id}`, { method: 'DELETE' })
      await loadAll()
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  const toggleEnabled = async (s: Subscription) => {
    try {
      await api<Subscription>(`/subscriptions/${s.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled: !s.enabled }),
      })
      await loadAll()
    } catch (e) {
      alert(e instanceof Error ? e.message : '更新失败')
    }
  }

  const onSourceIdsChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const values = Array.from(e.target.selectedOptions, (o) => Number(o.value))
    setForm({ ...form, source_ids: values })
  }

  return (
    <div>
      <h1 className="page-title">订阅通知</h1>
      <div className="two-col">
        <div>
          {canEdit && (
            <div className="toolbar">
              <button className="btn primary" onClick={() => { resetForm(); setShowForm(true) }}>新建订阅</button>
            </div>
          )}

          {showForm && (
            <div className="card">
              <h2 className="section-title" style={{ marginTop: 0 }}>
                {editingId !== null ? '编辑订阅' : '新建订阅'}
              </h2>
              <div className="form-grid">
                <div className="form-item">
                  <label>名称</label>
                  <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="form-item">
                  <label>渠道</label>
                  <select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value as 'webhook' | 'email' })}>
                    <option value="webhook">webhook</option>
                    <option value="email">email</option>
                  </select>
                </div>
                <div className="form-item full">
                  <label>目标地址</label>
                  <input type="text" value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} placeholder={form.channel === 'email' ? 'user@example.com' : 'https://example.com/hook'} />
                </div>
                <div className="form-item full">
                  <label>关键词（逗号分隔）</label>
                  <input type="text" value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
                </div>
                <div className="form-item full">
                  <label>关联来源（按住 Ctrl/Cmd 多选）</label>
                  <select multiple value={form.source_ids.map(String)} onChange={onSourceIdsChange}>
                    {sources.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-item checkbox-item">
                  <input id="sub-enabled" type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
                  <label htmlFor="sub-enabled">启用</label>
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
            ) : subscriptions.length === 0 ? (
              <p className="muted" style={{ padding: 16 }}>暂无订阅。</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>渠道</th>
                    <th>目标地址</th>
                    <th>关键词</th>
                    <th>启用</th>
                    {canEdit && <th>操作</th>}
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((s) => (
                    <tr key={s.id}>
                      <td>{s.name}</td>
                      <td>{s.channel}</td>
                      <td className="text-clip" title={s.target}>{s.target}</td>
                      <td className="text-clip" title={s.keywords.join(', ')}>{s.keywords.join(', ') || '—'}</td>
                      <td>
                        <label className="switch">
                          <input type="checkbox" checked={s.enabled} onChange={() => toggleEnabled(s)} />
                          <span className="muted">{s.enabled ? '开' : '关'}</span>
                        </label>
                      </td>
                      {canEdit && (
                        <td>
                          <div className="btn-row">
                            <button className="btn small" onClick={() => startEdit(s)}>编辑</button>
                            <button className="btn small danger" onClick={() => handleDelete(s)}>删除</button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div>
          <h2 className="section-title" style={{ marginTop: 0 }}>通知记录</h2>
          <div className="card" style={{ padding: 0 }}>
            {loading ? (
              <p className="muted" style={{ padding: 16 }}>加载中…</p>
            ) : notifications.length === 0 ? (
              <p className="muted" style={{ padding: 16 }}>暂无通知记录。</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>订阅名</th>
                    <th>变更标题</th>
                    <th>渠道</th>
                    <th>状态</th>
                    <th>错误</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  {notifications.map((n) => (
                    <tr key={n.id}>
                      <td>{n.subscription_name}</td>
                      <td className="text-clip" title={n.change_title}>{n.change_title}</td>
                      <td>{n.channel}</td>
                      <td><span className={`badge badge-${n.status}`}>{n.status === 'sent' ? '已发送' : '失败'}</span></td>
                      <td className="error-text" title={n.error ?? ''}>{n.error ?? '—'}</td>
                      <td>{fmtDate(n.sent_at ?? n.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
