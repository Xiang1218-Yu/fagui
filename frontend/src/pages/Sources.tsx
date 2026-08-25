import { useEffect, useState } from 'react'
import {
  createSource,
  crawlSource,
  deleteSource,
  listSources,
  updateSource,
} from '../api'
import { useAuth } from '../auth'
import type { Source, SourceType } from '../types'
import { fmtTime, sourceTypeLabel } from '../labels'

const EMPTY: Partial<Source> = {
  name: '',
  url: '',
  source_type: 'regulator',
  allowed_hosts: '',
  frequency_minutes: 1440,
  enabled: true,
  respect_robots: true,
  fetch_attachments: true,
  follow_links: true,
  max_links: 20,
  link_selector: '',
  notes: '',
}

export default function Sources() {
  const { isAdmin } = useAuth()
  const [sources, setSources] = useState<Source[]>([])
  const [editing, setEditing] = useState<Partial<Source> | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const [msg, setMsg] = useState('')

  const load = () => listSources().then(setSources).catch(() => {})
  useEffect(() => { load() }, [])

  const save = async () => {
    if (!editing?.name || !editing?.url) {
      setMsg('名称与 URL 必填')
      return
    }
    if (editing.id) await updateSource(editing.id, editing)
    else await createSource(editing)
    setEditing(null)
    setMsg('')
    load()
  }

  const runNow = async (id: number) => {
    setBusy(id)
    setMsg('采集执行中…')
    try {
      const run = await crawlSource(id)
      setMsg(`来源 #${id} 采集完成：${run.message}（变更 ${run.changes_detected}）`)
    } catch (e: any) {
      setMsg(`采集失败：${e?.message ?? e}`)
    } finally {
      setBusy(null)
      load()
    }
  }

  const remove = async (id: number) => {
    if (!confirm('确认删除该来源及其历史数据？')) return
    await deleteSource(id)
    load()
  }

  return (
    <div>
      <h2 className="page-title">来源管理</h2>
      <p className="page-desc">
        维护允许采集的来源、抓取频率、host 白名单、正文链接采集与 robots 遵从策略。
        {isAdmin ? '（管理员可编辑）' : '（当前为分析师，只读；仅管理员可增删改与触发采集）'}
      </p>

      <div className="toolbar">
        {isAdmin && (
          <button className="btn btn-primary" onClick={() => setEditing({ ...EMPTY })}>
            + 新增来源
          </button>
        )}
        {msg && <span className="muted">{msg}</span>}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>URL</th>
              <th>白名单 host</th>
              <th>频率(分)</th>
              <th>正文链接</th>
              <th>robots</th>
              <th>状态</th>
              <th>上次采集</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td><span className="badge badge-blue">{sourceTypeLabel[s.source_type]}</span></td>
                <td className="mono" style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.url}</td>
                <td className="mono">{s.allowed_hosts || '—'}</td>
                <td>{s.frequency_minutes}</td>
                <td>{s.follow_links ? `跟进(≤${s.max_links})` : '关闭'}</td>
                <td>{s.respect_robots ? '遵从' : '忽略'}</td>
                <td>
                  <span className={'badge ' + (s.enabled ? 'badge-green' : 'badge-gray')}>
                    {s.enabled ? '启用' : '停用'}
                  </span>
                </td>
                <td className="muted">{fmtTime(s.last_run_at)}</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {isAdmin ? (
                    <>
                      <button className="btn btn-sm" disabled={busy === s.id} onClick={() => runNow(s.id)}>
                        {busy === s.id ? '采集中' : '立即采集'}
                      </button>{' '}
                      <button className="btn btn-sm" onClick={() => setEditing(s)}>编辑</button>{' '}
                      <button className="btn btn-sm btn-danger" onClick={() => remove(s.id)}>删除</button>
                    </>
                  ) : (
                    <span className="muted">只读</span>
                  )}
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr><td colSpan={10} className="empty">暂无来源{isAdmin ? '，点击“新增来源”开始。' : '。'}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="modal-overlay" onClick={() => setEditing(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editing.id ? '编辑来源' : '新增来源'}</h3>
            <div className="form-row">
              <label>名称</label>
              <input value={editing.name ?? ''} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
            </div>
            <div className="form-row">
              <label>URL（采集入口页）</label>
              <input value={editing.url ?? ''} onChange={(e) => setEditing({ ...editing, url: e.target.value })} />
            </div>
            <div className="form-grid">
              <div className="form-row">
                <label>类型</label>
                <select
                  value={editing.source_type}
                  onChange={(e) => setEditing({ ...editing, source_type: e.target.value as SourceType })}
                >
                  <option value="regulator">监管网站</option>
                  <option value="association">行业协会</option>
                  <option value="consultation">征求意见</option>
                </select>
              </div>
              <div className="form-row">
                <label>抓取频率（分钟）</label>
                <input
                  type="number"
                  value={editing.frequency_minutes ?? 1440}
                  onChange={(e) => setEditing({ ...editing, frequency_minutes: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="form-row">
              <label>允许的 host 白名单（逗号分隔，来源自身 host 自动加入）</label>
              <input
                value={editing.allowed_hosts ?? ''}
                placeholder="example.com,www.example.com"
                onChange={(e) => setEditing({ ...editing, allowed_hosts: e.target.value })}
              />
            </div>
            <div className="form-grid">
              <div className="form-row">
                <label>
                  <input
                    type="checkbox"
                    style={{ width: 'auto', marginRight: 8 }}
                    checked={!!editing.enabled}
                    onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })}
                  />
                  启用
                </label>
              </div>
              <div className="form-row">
                <label>
                  <input
                    type="checkbox"
                    style={{ width: 'auto', marginRight: 8 }}
                    checked={!!editing.respect_robots}
                    onChange={(e) => setEditing({ ...editing, respect_robots: e.target.checked })}
                  />
                  遵从 robots.txt
                </label>
              </div>
              <div className="form-row">
                <label>
                  <input
                    type="checkbox"
                    style={{ width: 'auto', marginRight: 8 }}
                    checked={!!editing.fetch_attachments}
                    onChange={(e) => setEditing({ ...editing, fetch_attachments: e.target.checked })}
                  />
                  抓取附件
                </label>
              </div>
              <div className="form-row">
                <label>
                  <input
                    type="checkbox"
                    style={{ width: 'auto', marginRight: 8 }}
                    checked={!!editing.follow_links}
                    onChange={(e) => setEditing({ ...editing, follow_links: e.target.checked })}
                  />
                  跟进正文链接
                </label>
              </div>
            </div>
            <div className="form-grid">
              <div className="form-row">
                <label>正文链接上限（每次采集）</label>
                <input
                  type="number"
                  value={editing.max_links ?? 20}
                  onChange={(e) => setEditing({ ...editing, max_links: Number(e.target.value) })}
                />
              </div>
              <div className="form-row">
                <label>正文链接 CSS 选择器（可选）</label>
                <input
                  value={editing.link_selector ?? ''}
                  placeholder="如 .news-list a"
                  onChange={(e) => setEditing({ ...editing, link_selector: e.target.value })}
                />
              </div>
            </div>
            <div className="form-row">
              <label>备注</label>
              <textarea value={editing.notes ?? ''} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} />
            </div>
            <div className="toolbar">
              <div className="spacer" />
              <button className="btn" onClick={() => setEditing(null)}>取消</button>
              <button className="btn btn-primary" onClick={save}>保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
