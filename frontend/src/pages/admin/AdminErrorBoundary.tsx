import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode; title?: string }
type State = { error: Error | null }

const isDebug = import.meta.env.DEV || import.meta.env.MODE === 'test'

export class AdminErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Admin render error', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="admin-state admin-state-error admin-state-section-error" role="alert">
        <strong>{this.props.title ?? 'Ошибка раздела админки'}</strong>
        <p>{this.state.error.message || 'Не удалось отрисовать блок.'}</p>
        {isDebug && <pre>{this.state.error.stack}</pre>}
        <button type="button" className="admin-btn admin-btn-sm" onClick={() => this.setState({ error: null })}>Повторить</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={() => window.location.reload()}>Обновить страницу</button>
      </div>
    )
  }
}
