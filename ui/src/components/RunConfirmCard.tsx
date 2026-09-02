interface Props {
  command: string
  onApprove: () => void
  onReject: () => void
}

export function RunConfirmCard({ command, onApprove, onReject }: Props) {
  return (
    <div className="max-w-[70ch] self-center rounded-lg border border-orange-500 p-3">
      <p className="m-0 text-sm">el modelo propone ejecutar:</p>
      <code className="my-2 block rounded bg-slate-100 px-2 py-1.5 text-sm dark:bg-slate-800">
        {command}
      </code>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onApprove}
          className="rounded bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-500"
        >
          Ejecutar
        </button>
        <button
          type="button"
          onClick={onReject}
          className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-500"
        >
          Rechazar
        </button>
      </div>
    </div>
  )
}
