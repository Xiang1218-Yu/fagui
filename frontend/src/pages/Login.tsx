import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'
import { useAuth } from '../auth'

export default function Login() {
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const u = await login(username, password)
      setUser(u)
      navigate('/dashboard')
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? '登录失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
      <form className="card" style={{ width: 360 }} onSubmit={submit}>
        <h2 style={{ marginTop: 0 }}>法规变更情报与影响研判平台</h2>
        <p className="muted" style={{ marginTop: -8 }}>请登录以继续</p>
        <div className="form-row">
          <label>用户名</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </div>
        <div className="form-row">
          <label>密码</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {err && <div style={{ color: 'var(--red)', marginBottom: 12 }}>{err}</div>}
        <button className="btn btn-primary" style={{ width: '100%' }} disabled={busy}>
          {busy ? '登录中…' : '登录'}
        </button>
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          演示账号：admin / admin123（管理员）、analyst / analyst123（分析师）
        </p>
      </form>
    </div>
  )
}
