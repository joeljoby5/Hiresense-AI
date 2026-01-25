import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { request, setCsrf } from '../../services/api'
import { Modal, RequestFailure } from '../resumes/ResumeUi'
import { accountKey, useAccount } from './api'
import type { Account } from './api'

export function Login() { return <SignIn register={false} /> }
export function Register() { return <SignIn register /> }

function SignIn({ register }: { register: boolean }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const cache = useQueryClient()
  const navigate = useNavigate()
  const action = useMutation({
    mutationFn: () => request<Account>(register ? '/auth/register' : '/auth/login', 'POST',
      { email, password, ...(register ? { display_name: name } : {}) }),
    onSuccess: (account) => {
      cache.clear()
      setCsrf(account.csrf_token)
      cache.setQueryData(accountKey, account)
      void navigate('/workspace', { replace: true })
    },
  })
  return <main className="auth-page stack">
    <Link to="/">HireSense AI</Link>
    <h1>{register ? 'Create account' : 'Sign in'}</h1>
    <form className="surface stack" onSubmit={(event) => { event.preventDefault(); if (!action.isPending) action.mutate() }}>
      {register && <label>Display name (optional)<input autoComplete="name" maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>}
      <label>Email<input type="email" autoComplete="username" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>Password<input type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 12 : 1}
        maxLength={256} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {register && <p>Use at least 12 characters.</p>}
      {action.error && <RequestFailure error={action.error} />}
      <button className="button primary" disabled={action.isPending}>{action.isPending ? 'Working…' : register ? 'Create account' : 'Sign in'}</button>
    </form>
    <Link to={register ? '/login' : '/register'}>{register ? 'Sign in to an existing account' : 'Create an account'}</Link>
  </main>
}

export function AccountPage() {
  const account = useAccount()
  if (account.isPending) return <p role="status">Loading account…</p>
  if (account.error) return <RequestFailure error={account.error} retry={() => void account.refetch()} />
  if (!account.data) return <section className="surface stack"><h1>Account</h1><p>Sign in to manage your private workspace and sessions.</p>
    <div className="row"><Link className="button primary" to="/login">Sign in</Link><Link className="button secondary" to="/register">Create account</Link></div>
  </section>
  return <Settings key={account.data.profile.id} account={account.data} />
}

function Settings({ account }: { account: Account }) {
  const [name, setName] = useState(account.profile.display_name)
  const [current, setCurrent] = useState('')
  const [replacement, setReplacement] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [message, setMessage] = useState('')
  const cache = useQueryClient()
  const navigate = useNavigate()
  const action = useMutation({
    mutationFn: (kind: 'profile' | 'password' | 'revoke') => {
      if (kind === 'profile') return request<Account>('/auth/me', 'PATCH', { display_name: name })
      if (kind === 'password') return request<Account>('/auth/password', 'POST', { current_password: current, new_password: replacement })
      return request<Account>('/auth/revoke-sessions', 'POST')
    },
    onSuccess: (result, kind) => {
      setCsrf(result.csrf_token)
      cache.setQueryData(accountKey, result)
      setName(result.profile.display_name)
      setCurrent('')
      setReplacement('')
      setMessage(kind === 'profile' ? 'Profile saved.' : kind === 'password' ? 'Password changed and sessions rotated.' : 'Other sessions revoked.')
    },
  })
  const close = useMutation({
    mutationFn: (permanent: boolean) => permanent ? request<void>('/auth/me', 'DELETE', { password: deletePassword }) : request<void>('/auth/logout', 'POST'),
    onSuccess: () => {
      cache.clear()
      setCsrf(null)
      cache.setQueryData(accountKey, null)
      void navigate('/login', { replace: true })
    },
  })
  const busy = action.isPending || close.isPending
  return <div className="stack account-page">
    <header className="page-heading"><div><h1>Account</h1><p>{account.profile.email}</p></div>
      <button className="button secondary" disabled={busy} onClick={() => close.mutate(false)}>Sign out</button>
    </header>
    {message && <p role="status">{message}</p>}
    {action.error && <RequestFailure error={action.error} />}
    {!confirm && close.error && <RequestFailure error={close.error} />}
    <form className="surface stack" onSubmit={(event) => { event.preventDefault(); if (!busy) action.mutate('profile') }}>
      <h2>Profile</h2>
      <label>Display name<input maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <div><button className="button primary" disabled={busy || name === account.profile.display_name}>Save profile</button></div>
    </form>
    <form className="surface stack" onSubmit={(event) => { event.preventDefault(); if (!busy) action.mutate('password') }}>
      <h2>Change password</h2>
      <label>Current password<input type="password" autoComplete="current-password" required maxLength={256} value={current} onChange={(event) => setCurrent(event.target.value)} /></label>
      <label>New password<input type="password" autoComplete="new-password" required minLength={12} maxLength={256} value={replacement} onChange={(event) => setReplacement(event.target.value)} /></label>
      <div><button className="button primary" disabled={busy}>Change password</button></div>
    </form>
    <section className="surface stack"><h2>Active sessions</h2><div><button className="button secondary" disabled={busy} onClick={() => action.mutate('revoke')}>Revoke other sessions</button></div></section>
    <section className="surface stack"><h2>Delete account</h2><p>Permanent deletion removes your resumes, job listings, checkpoints, exports and analyses.</p>
      <div><button className="button danger" disabled={busy} onClick={() => { close.reset(); setDeletePassword(''); setConfirm(true) }}>Delete account</button></div>
    </section>
    {confirm && <Modal title="Delete account?" onDismiss={() => { if (!close.isPending) setConfirm(false) }}>
      <form className="stack" onSubmit={(event) => { event.preventDefault(); if (!busy) close.mutate(true) }}>
        <p>Confirm your password to permanently delete this account and its workspace data.</p>
        <label>Password<input type="password" autoComplete="current-password" required maxLength={256} value={deletePassword} onChange={(event) => setDeletePassword(event.target.value)} /></label>
        {close.error && <RequestFailure error={close.error} />}
        <div className="dialog-actions"><button className="button secondary" type="button" disabled={close.isPending} onClick={() => setConfirm(false)}>Cancel</button>
          <button className="button danger" disabled={busy}>Delete account</button></div>
      </form>
    </Modal>}
  </div>
}
