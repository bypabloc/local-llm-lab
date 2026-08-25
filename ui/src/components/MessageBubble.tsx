import type { Role } from "../api/types"

interface Props {
  role: Role
  content: string
}

export function MessageBubble({ role, content }: Props) {
  return (
    <div className={`message message--${role}`}>
      <span className="message__role">{role}</span>
      <p className="message__content">{content}</p>
    </div>
  )
}
