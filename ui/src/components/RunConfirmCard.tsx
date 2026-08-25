interface Props {
  command: string
  onApprove: () => void
  onReject: () => void
}

export function RunConfirmCard({ command, onApprove, onReject }: Props) {
  return (
    <div className="run-confirm">
      <p className="run-confirm__label">el modelo propone ejecutar:</p>
      <code className="run-confirm__command">{command}</code>
      <div className="run-confirm__actions">
        <button type="button" onClick={onApprove} className="run-confirm__approve">
          Ejecutar
        </button>
        <button type="button" onClick={onReject} className="run-confirm__reject">
          Rechazar
        </button>
      </div>
    </div>
  )
}
