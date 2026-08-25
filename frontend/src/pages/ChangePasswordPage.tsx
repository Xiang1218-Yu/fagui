import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { User, useCurrentUser } from '../types'

export default function ChangePasswordPage() {
  const user = useCurrentUser()
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!oldPassword || !newPassword) {
      setError('请填写原密码和新密码')
      return
    }
    if (newPassword.length < 8) {
      setError('新密码长度至少 8 位')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const updated = await api<User>('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      })
      localStorage.setItem('regintel_user', JSON.stringify(updated))
      alert('密码修改成功')
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '密码修改失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="center-wrap">
      <div className="login-card">
        <h1>修改密码</h1>
        <p className="muted login-sub">
          {user?.must_change_password ? '首次登录请先修改初始密码' : '请定期修改密码以保障账号安全'}
        </p>
        <form onSubmit={handleSubmit}>
          <div className="form-item">
            <label htmlFor="old-password">原密码</label>
            <input
              id="old-password"
              type="password"
              value={oldPassword}
              autoComplete="current-password"
              onChange={(e) => setOldPassword(e.target.value)}
            />
          </div>
          <div className="form-item">
            <label htmlFor="new-password">新密码</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              autoComplete="new-password"
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div className="form-item">
            <label htmlFor="confirm-password">确认新密码</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              autoComplete="new-password"
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <button className="btn primary login-btn" type="submit" disabled={submitting}>
            {submitting ? '提交中…' : '确认修改'}
          </button>
          {error && <p className="login-error">{error}</p>}
        </form>
      </div>
    </div>
  )
}
