import { ConnectionStatus } from '../components/ConnectionStatus'

export function FoundationPage() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="site-header">
        <a className="brand" href="/" aria-label="HireSense AI home">
          <span className="brand-mark" aria-hidden="true">H<span>.</span></span>
          <span>HireSense <span className="text-teal">AI</span></span>
        </a>
        <span className="stage-badge">Development foundation</span>
      </header>
      <main id="main-content" className="page-content">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow text-teal">A considered start. A clearer career.</p>
          <h1 id="page-title">Build Smarter.<br />Apply Better.<br /><span className="text-teal">Grow Faster.</span></h1>
          <h2 className="project-title">HireSense AI — AI-Powered Resume Builder, ATS Optimization and Career Intelligence Platform</h2>
          <p className="description">A platform being built to help professionals create stronger resumes, understand job requirements and make informed career decisions.</p>
          <div className="scope-note">
            <span className="scope-line" aria-hidden="true" />
            <p><strong>Project foundation · Task 001</strong><br />This initial screen verifies the application connection. Resume tools and career intelligence are planned for future milestones.</p>
          </div>
        </section>
        <ConnectionStatus />
      </main>
      <footer className="site-footer"><span>HireSense AI</span><span>Built with purpose. Developed incrementally.</span></footer>
    </div>
  )
}
