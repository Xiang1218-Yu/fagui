import { useEffect, useState } from 'react'
import { createSubscription, deleteSubscription, listSources, listSubscriptions, testEmail } from '../api'
import type { ImpactLevel, Source, Subscription } from '../types'
import { fmtTime, impactLabel } from '../labels'

const EMPTY: Partial<Subscription> = {
  name: '',
  subscriber: 'analyst',
  keyword: '',
  source_id: null,
  min_impact: 'low',
  channel: 'inapp',
  email: '',
  enabled: true,
}

export default function Subscriptions() {
  const [subs, setSubs] = useState<Subscription[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [form, setForm] = useState<Partial<Subscription>>({ ...EMPTY })
  const [msg, setMsg] = useState('')

  const load = () => listSubscriptions().then(setSubs).catch(() => {})
  useEffect(() => {
    load()
    listSources().then(setSources).catch(() => {})
  }, [])

  const sourceName = (id: number | null) =>
    id == null ? '全部来源' : sources.find((s) => s.id === id)?.name ?? `#${id}`

  const create = async () => {
    if (!form.name) return
    if (form.channel === 'email' && !form.email) {
      setMsg('邮件渠道需要填写收件邮箱')
      return
    }
    await createSubscription(form)
    setForm({ ...EMPTY })
    setMsg('')
    load()
  }

  const remove = async (id: number) => {
    await deleteSubscription(id)
    load()
  }

  const runEmailTest = async () => {
    if (!form.email) {
      setMsg('请先填写测试收件邮箱')
      return
    }
    try {
      const r = await testEmail(form.email)
      setMsg(`邮件测试：${r.status} — ${r.detail}`)
    } catch (e: any) {
      setMsg(`邮件测试失败：${e?.response?.data?.detail ?? e?.message}`)
    }
  }

  return (
    <div>
      <h2 className="page-title">订阅通知</h2>
      <p className="page-desc">
        按关键词、来源与最低影响等级订阅法规变更；站内渠道生成站内通知，邮件渠道通过 SMTP 真实投递并记录发送状态。
      </p>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>新建订阅</h3>
        <div className="form-grid">
          <div className="form-row">
            <label>订阅名称</label>
            <input value={form.name ?? ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-row">
            <label>订阅人</label>
            <input value={form.subscriber ?? ''} onChange={(e) => setForm({ ...form, subscriber: e.target.value })} />
          </div>
          <div className="form-row">
            <label>关键词（可空 = 全部）</label>
            <input value={form.keyword ?? ''} onChange={(e) => setForm({ ...form, keyword: e.target.value })} />
          </div>
          <div className="form-row">
            <label>来源</label>
            <select
              value={form.source_id ?? ''}
              onChange={(e) => setForm({ ...form, source_id: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">全部来源</option>
              {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>最低影响等级</label>
            <select value={form.min_impact} onChange={(e) => setForm({ ...form, min_impact: e.target.value as ImpactLevel })}>
              <option value="low">低及以上</option>
              <option value="medium">中及以上</option>
              <option value="high">仅高</option>
            </select>
          </div>
          <div className="form-row">
            <label>通知渠道</label>
            <select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })}>
              <option value="inapp">站内</option>
              <option value="email">邮件</option>
            </select>
          </div>
          {form.channel === 'email' && (
            <div className="form-row">
              <label>收件邮箱</label>
              <input
                value={form.email ?? ''}
                placeholder="compliance-team@example.com"
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
          )}
        </div>
        <div className="toolbar">
          <button className="btn btn-primary" onClick={create}>创建订阅</button>
          {form.channel === 'email' && (
            <button className="btn" onClick={runEmailTest}>发送测试邮件</button>
          )}
          {msg && <span className="muted">{msg}</span>}
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr><th>#</th><th>名称</th><th>订阅人</th><th>关键词</th><th>来源</th><th>最低影响</th><th>渠道</th><th>收件邮箱</th><th>创建</th><th></th></tr>
          </thead>
          <tbody>
            {subs.map((s) => (
              <tr key={s.id}>
                <td>{s.id}</td>
                <td>{s.name}</td>
                <td>{s.subscriber || '—'}</td>
                <td>{s.keyword || '（全部）'}</td>
                <td>{sourceName(s.source_id)}</td>
                <td>{impactLabel[s.min_impact]}</td>
                <td>{s.channel === 'email' ? '邮件' : '站内'}</td>
                <td className="mono">{s.email || '—'}</td>
                <td className="muted">{fmtTime(s.created_at)}</td>
                <td><button className="btn btn-sm btn-danger" onClick={() => remove(s.id)}>删除</button></td>
              </tr>
            ))}
            {subs.length === 0 && <tr><td colSpan={10} className="empty">暂无订阅。</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
