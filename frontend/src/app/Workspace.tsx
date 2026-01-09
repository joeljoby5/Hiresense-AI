import { useEffect, useState } from 'react'
import { FileText, LayoutDashboard, CircleHelp, Menu, Moon, Sun, X, ShieldCheck, Layers, Files } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'

function Brand() {
  return <Link className="brand" to="/"><span className="brand-mark"><FileText size={20} /></span> HireSense AI</Link>
}

function ThemeButton() {
  const [dark, setDark] = useState(() => window.localStorage.getItem('hiresense-theme') === 'dark')
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    window.localStorage.setItem('hiresense-theme', dark ? 'dark' : 'light')
  }, [dark])
  return <button className="icon-button" type="button" aria-label={dark ? 'Use light theme' : 'Use dark theme'} onClick={() => setDark(!dark)}>
    {dark ? <Sun size={19} /> : <Moon size={19} />}
  </button>
}

const navigation = [
  { to: '/workspace', label: 'Overview', icon: LayoutDashboard },
  { to: '/workspace/resumes', label: 'My resumes', icon: Files },
  { to: '/workspace/help', label: 'Help', icon: CircleHelp },
]

export function Workspace() {
  const { pathname } = useLocation()
  const [drawer, setDrawer] = useState('')
  const open = drawer === pathname
  const section = [...navigation].reverse().find(({ to }) => pathname.startsWith(to))?.label
  return <div className="workspace">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className={'sidebar' + (open ? ' sidebar-open' : '')} id="navigation">
      <Brand />
      <nav aria-label="Workspace" className="sidebar-nav">
        {navigation.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/workspace'} onClick={() => setDrawer('')}>
          <Icon size={18} aria-hidden="true" />{label}
        </NavLink>)}
      </nav>
      <span className="sidebar-note"><ShieldCheck size={17} /> Local workspace</span>
    </aside>
    <div className="workspace-body">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-controls="navigation" aria-expanded={open} aria-label={open ? 'Close navigation' : 'Open navigation'} onClick={() => setDrawer(open ? '' : pathname)}>
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>
        <span className="breadcrumb">Workspace <span aria-hidden="true">/</span> {section}</span>
        <ThemeButton />
      </header>
      <main className="workspace-content" id="main"><Outlet /></main>
    </div>
  </div>
}

export function LandingPage() {
  return <div className="public-page">
    <header className="public-header"><Brand /><nav aria-label="Main"><Link to="/workspace" className="button secondary">Open workspace</Link><ThemeButton /></nav></header>
    <main>
      <section className="hero">
        <div>
          <h1>Build a resume you can stand behind.</h1>
          <p>Organize experience, keep focused copies for different roles, and save checkpoints as your resume evolves.</p>
          <Link className="button primary" to="/workspace/resumes">Open resume library</Link>
        </div>
        <div className="hero-workflow">
          <div><FileText /><span><strong>Start a resume</strong><small>Give each draft a clear purpose.</small></span></div>
          <div><Layers /><span><strong>Keep a checkpoint</strong><small>Save a record of a specific draft.</small></span></div>
          <div><Files /><span><strong>Make an independent copy</strong><small>Explore changes while preserving the source.</small></span></div>
        </div>
      </section>
      <section className="public-faq">
        <h2>Before you get started</h2>
        <details><summary>Where are my resumes stored?</summary><p>Resumes are saved in the SQLite database configured for your local backend.</p></details>
        <details><summary>Does resume management require AI?</summary><p>Creating, copying and saving checkpoints works with the local app and database.</p></details>
        <details><summary>How do I connect a workspace?</summary><p>Run the frontend and backend locally, migrate the database, and configure the development owner.</p><Link to="/workspace/help">Read workspace setup</Link></details>
      </section>
    </main>
    <footer className="public-header"><Brand /><Link to="/workspace/help">Help</Link></footer>
  </div>
}

export function WorkspaceHelp() {
  return <section className="prose-panel">
    <h1>Workspace help</h1>
    <h2>Developer workspace setup</h2>
    <ol>
      <li>Apply the Alembic migrations in the repository README.</li>
      <li>Initialize the local owner with <code>python -m app.initialize_owner</code> and set the owner UUID in the backend environment.</li>
      <li>Start the local API and frontend on loopback addresses.</li>
    </ol>
    <p>Deleting a resume permanently removes its checkpoints. Independent copies remain available.</p>
    <Link className="button secondary" to="/workspace/resumes">Resume library</Link>
  </section>
}

export function WorkspaceError() {
  return <main className="workspace-content"><h1>Page unavailable</h1><p><Link to="/workspace">Return to the workspace</Link></p></main>
}
