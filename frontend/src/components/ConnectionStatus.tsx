import { useEffect, useState } from 'react'
import { fetchHealth, HealthError, type HealthResponse } from '../services/health'

type Connection =
  | { state: 'checking' }
  | { state: 'connected'; health: HealthResponse }
  | { state: 'unavailable' | 'invalid'; message: string }

export function ConnectionStatus() {
  const [connection, setConnection] = useState<Connection>({ state: 'checking' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal).then(
      (health) => {
        if (!controller.signal.aborted) setConnection({ state: 'connected', health })
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setConnection({
            state: error instanceof HealthError ? error.kind : 'unavailable',
            message: error instanceof Error ? error.message : 'An unexpected connection error occurred.',
          })
        }
      },
    )
    return () => controller.abort()
  }, [attempt])

  const labels = {
    checking: 'Checking connection', connected: 'Backend connected',
    unavailable: 'Backend unavailable', invalid: 'Invalid or unexpected response',
  }

  function retry() {
    setConnection({ state: 'checking' })
    setAttempt((value) => value + 1)
  }

  return (
    <section className="connection-panel" aria-labelledby="connection-heading">
      <div className="panel-heading">
        <h2 id="connection-heading">Application connection</h2>
        <span className="eyebrow">Live health check</span>
      </div>
      <div role="status" aria-live="polite" aria-atomic="true">
        <p className={`connection-label ${connection.state}`}>
          <span className="status-dot" aria-hidden="true" />{labels[connection.state]}
        </p>
        {connection.state === 'connected' ? (
          <>
            <p className="text-slate">The application API is responding successfully.</p>
            <dl className="metadata">
              <div><dt>Application</dt><dd>{connection.health.application}</dd></div>
              <div><dt>API version</dt><dd>{connection.health.version}</dd></div>
              <div><dt>Environment</dt><dd>{connection.health.environment}</dd></div>
            </dl>
          </>
        ) : connection.state === 'checking' ? (
          <p className="text-slate">Waiting for a response from the application API…</p>
        ) : (
          <p className="text-slate">{connection.message}</p>
        )}
      </div>
      <button className="retry-button" onClick={retry} disabled={connection.state === 'checking'}>
        {connection.state === 'checking' ? 'Checking…' : connection.state === 'connected' ? 'Check again' : 'Retry connection'}
      </button>
    </section>
  )
}
