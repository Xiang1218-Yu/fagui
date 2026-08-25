import { useEffect, useState } from 'react'
import { listRegulations, listSources, regulationDocuments } from '../api'
import type { Document, Regulation, Source } from '../types'
import { fmtTime, impactBadge, impactLabel } from '../labels'

export default function Regulations() {
  const [regs, setRegs] = useState<Regulation[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [expanded, setExpanded] = useState<number | null>(null)
  const [docs, setDocs] = useState<Document[]>([])

  useEffect(() => {
    listRegulations().then(setRegs).catch(() => {})
    listSources().then(setSources).catch(() => {})
  }, [])

  const sourceName = (id: number) => sources.find((s) => s.id === id)?.name ?? `#${id}`

  const toggle = async (id: number) => {
    if (expanded === id) { setExpanded(null); return }
    setExpanded(id)
    setDocs(await regulationDocuments(id))
  }

  return (
    <div>
      <h2 className="page-title">法规归并</h2>
      <p className="page-desc">
        同一条法规被多个来源转载时，系统按标题归一化合并为一条法规；展开可见每个来源的原始文档与出处，便于向业务团队说明结论来源。
      </p>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr><th></th><th>#</th><th>法规标题</th><th>归并键</th><th>文号</th><th>创建时间</th></tr>
          </thead>
          <tbody>
            {regs.map((r) => (
              <>
                <tr key={r.id}>
                  <td><span className="link" onClick={() => toggle(r.id)}>{expanded === r.id ? '▼' : '▶'}</span></td>
                  <td>{r.id}</td>
                  <td>{r.title}</td>
                  <td className="mono muted">{r.dedup_key}</td>
                  <td>{r.identifier || '—'}</td>
                  <td className="muted">{fmtTime(r.created_at)}</td>
                </tr>
                {expanded === r.id && (
                  <tr>
                    <td colSpan={6} style={{ background: '#f8fafc' }}>
                      <div style={{ padding: '8px 4px' }}>
                        <b>来源文档（{docs.length}）</b>
                        <table style={{ marginTop: 8 }}>
                          <thead>
                            <tr><th>来源</th><th>标题</th><th>URL</th><th>影响等级</th><th>最近发现</th></tr>
                          </thead>
                          <tbody>
                            {docs.map((d) => (
                              <tr key={d.id}>
                                <td>{sourceName(d.source_id)}</td>
                                <td>{d.title}</td>
                                <td className="mono"><a className="link" href={d.url} target="_blank" rel="noreferrer">{d.url}</a></td>
                                <td><span className={'badge ' + impactBadge[d.impact_level]}>{impactLabel[d.impact_level]}</span></td>
                                <td className="muted">{fmtTime(d.last_seen_at)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {regs.length === 0 && <tr><td colSpan={6} className="empty">暂无归并后的法规。</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
