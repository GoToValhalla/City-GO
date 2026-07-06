import { DiagnosticsPanel } from './DiagnosticsPanel'
import { useDebugMode } from './useDebugMode'

export const GlobalDebugToolbar = () => {
  const { enabled, setDebug } = useDebugMode()
  return (
    <div className="global-debug-toolbar">
      {enabled ? <button type="button" onClick={() => setDebug(false)}>DEBUG включён</button> : null}
      {enabled ? <DiagnosticsPanel compact payload={{ screen: 'unknown', category: 'ui', severity: 'info', title: 'UI report', summary: 'Manual user report' }} /> : null}
    </div>
  )
}
