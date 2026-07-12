import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

const isDebug = import.meta.env.DEV || import.meta.env.MODE === 'test'

export class PublicErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Public application render error', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div role="alert" style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        minHeight: '100vh',
        padding: '24px',
        textAlign: 'center',
        fontFamily: 'system-ui, sans-serif',
      }}>
        <strong>Что-то пошло не так</strong>
        <p>Попробуйте обновить страницу.</p>
        {isDebug && <pre style={{ whiteSpace: 'pre-wrap', textAlign: 'left' }}>{this.state.error.stack}</pre>}
        <button type="button" onClick={() => window.location.reload()}>Обновить страницу</button>
      </div>
    )
  }
}
