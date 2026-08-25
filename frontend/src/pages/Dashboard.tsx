import { useEffect, useState } from 'react'
import { getStats } from '../api'
import type { DashboardStats } from '../types'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    getStats().then(setStats).catch(() => {})
  }, [])

  const cards = [
    { label: '采集来源', value: stats?.sources, sub: `${stats?.active_sources ?? 0} 个启用` },
    { label: '跟踪法规文档', value: stats?.documents },
    { label: '归并后法规', value: stats?.regulations },
    { label: '待复核变更', value: stats?.pending_reviews },
    { label: '近 7 天变更', value: stats?.changes_last_7d },
    { label: '未读通知', value: stats?.unread_notifications },
  ]

  return (
    <div>
      <h2 className="page-title">总览</h2>
      <p className="page-desc">
        合规团队的法规变更闭环：来源白名单采集 → 快照留痕 → 变更识别 → 人工复核与影响研判 → 订阅通知。
      </p>
      <div className="stat-grid">
        {cards.map((c) => (
          <div className="stat" key={c.label}>
            <div className="num">{c.value ?? '—'}</div>
            <div className="label">{c.label}</div>
            {c.sub && <div className="label" style={{ fontSize: 12 }}>{c.sub}</div>}
          </div>
        ))}
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>工作闭环说明</h3>
        <ol style={{ lineHeight: 1.9, color: 'var(--muted)' }}>
          <li><b>来源管理</b>：管理员维护允许采集的来源、抓取频率、host 白名单与 robots 遵从策略。</li>
          <li><b>采集运行</b>：系统按频率或手动触发抓取公开页面及附件，保留可追溯快照。</li>
          <li><b>法规归并</b>：同一法规被多来源转载时，按标题归一化合并为一条法规。</li>
          <li><b>变更对比</b>：识别正文与附件的哈希变化，生成差异与摘要。</li>
          <li><b>复核 / 影响研判</b>：待确认变更进入人工复核队列，确认后记录影响等级与受影响业务。</li>
          <li><b>订阅通知</b>：按关键词、来源、影响等级订阅，命中变更即生成通知。</li>
        </ol>
      </div>
    </div>
  )
}
