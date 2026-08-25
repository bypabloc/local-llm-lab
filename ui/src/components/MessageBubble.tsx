import type { Role } from "../api/types"

interface Props {
  role: Role
  content: string
}

const ROLE_CLASSES: Record<Role, string> = {
  user: "self-end bg-blue-100 dark:bg-blue-950",
  assistant: "self-start bg-slate-100 dark:bg-slate-800",
  system:
    "self-center border border-dashed border-slate-400 bg-transparent text-sm opacity-80 dark:border-slate-500",
}

export function MessageBubble({ role, content }: Props) {
  return (
    <div className={`max-w-[70ch] rounded-lg px-3 py-2 ${ROLE_CLASSES[role]}`}>
      <span className="block text-xs uppercase opacity-60">{role}</span>
      <p className="m-0 whitespace-pre-wrap">{content}</p>
    </div>
  )
}
