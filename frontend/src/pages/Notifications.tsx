import { useEffect, useState } from 'react'
import { listNotifications, markAllRead, markNotificationRead } from '../api'
import type { Notification } from '../types'
import { fmtTime } from '../labels'

interface Props { onChange?: () => void }

export default function Notifications({ onChange }: Props) {
  const [items, setItems] = useState<Notification[]>([])
  const [unreadOnly, setUnreadOnly] = useState(false)

  const load = () => listNotifications(unreadOnly).then(setItems).catch(() => {})
  useEffect(() => { load() }, [unreadOnly])

  const readOne = async (id: number) => {
    await markNotificationRead(id)
    load()
    onChange?.()
  }
  const readAll = async () => {
    await markAllRead()
    load()
    onChange?.()
  }

  return (
    <div>
      <h2 className="page-title">通知</h2>
      <p className="page-desc">订阅命中的法规变更会在此汇总，点击可标记已读。</p>

      <div className="toolbar">
        <label>
          <input type="checkbox" style={{ width: 'auto', marginRight: 6 }} checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
          仅看未读
        </label>
        <div className="spacer" />
        <button className="btn" onClick={readAll}>全部已读</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {items.map((n) => (
          <div key={n.id} className={'notif-item' + (n.is_read ? '' : ' unread')}>
            {!n.is_read && <div className="dot" />}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{n.title}</div>
              <div className="muted" style={{ margin: '4px 0' }}>{n.body}</div>
              <div className="muted" style={{ fontSize: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className={'badge ' + (n.channel === 'email' ? 'badge-amber' : 'badge-blue')}>
                  {n.channel === 'email' ? '邮件' : '站内'}
                </span>
                <span className={'badge ' + (
                  n.delivery_status === 'sent' ? 'badge-green'
                    : n.delivery_status === 'failed' ? 'badge-red' : 'badge-gray'
                )}>
                  {n.delivery_status === 'sent' ? '已投递'
                    : n.delivery_status === 'failed' ? '投递失败'
                    : n.delivery_status === 'skipped' ? '未投递' : n.delivery_status}
                </span>
                {n.delivery_detail && <span>{n.delivery_detail}</span>}
                <span>· {fmtTime(n.created_at)}</span>
              </div>
            </div>
            {!n.is_read && <button className="btn btn-sm" onClick={() => readOne(n.id)}>标记已读</button>}
          </div>
        ))}
        {items.length === 0 && <div className="empty">暂无通知。</div>}
      </div>
    </div>
  )
}
