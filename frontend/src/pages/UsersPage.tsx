import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Role, User, fmtDate, roleLabel } from '../types'

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('viewer')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api<User[]>('/auth/users')
      setUsers(data)
    } catch (e) {
      alert(e instanceof Error ? e.message : '加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleCreate = async () => {
    if (!username.trim() || !password) {
      alert('请填写用户名与密码')
      return
    }
    setSubmitting(true)
    try {
      await api<User>('/auth/users', {
        method: 'POST',
        body: JSON.stringify({ username: username.trim(), password, role }),
      })
      setUsername('')
      setPassword('')
      setRole('viewer')
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '创建用户失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">用户管理</h1>

      <div className="card">
        <h2 className="section-title" style={{ marginTop: 0 }}>新建用户</h2>
        <div className="form-grid">
          <div className="form-item">
            <label>用户名</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="form-item">
            <label>密码</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <div className="form-item">
            <label>角色</label>
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="admin">管理员</option>
              <option value="analyst">分析师</option>
              <option value="viewer">只读</option>
            </select>
          </div>
        </div>
        <div className="btn-row">
          <button className="btn primary" disabled={submitting} onClick={handleCreate}>
            {submitting ? '提交中…' : '创建用户'}
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <p className="muted" style={{ padding: 16 }}>加载中…</p>
        ) : users.length === 0 ? (
          <p className="muted" style={{ padding: 16 }}>暂无用户。</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>用户名</th>
                <th>角色</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td><span className={`badge badge-role-${u.role}`}>{roleLabel[u.role]}</span></td>
                  <td>{fmtDate(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
