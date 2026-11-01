interface Props {
  tone: 'ok' | 'warn' | 'error' | 'neutral'
  children: string
}

export function StatusBadge({ tone, children }: Props) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}
