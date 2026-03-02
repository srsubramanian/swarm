export function Logomark(props: React.ComponentPropsWithoutRef<'svg'>) {
  return (
    <svg aria-hidden="true" viewBox="0 0 36 36" fill="none" {...props}>
      <circle cx="18" cy="18" r="15" stroke="#38BDF8" strokeWidth="2" />
      <circle cx="10" cy="14" r="3" fill="#38BDF8" opacity="0.8" />
      <circle cx="26" cy="14" r="3" fill="#38BDF8" opacity="0.8" />
      <circle cx="18" cy="24" r="3" fill="#38BDF8" opacity="0.8" />
      <line x1="10" y1="14" x2="26" y2="14" stroke="#38BDF8" strokeWidth="1.5" opacity="0.4" />
      <line x1="10" y1="14" x2="18" y2="24" stroke="#38BDF8" strokeWidth="1.5" opacity="0.4" />
      <line x1="26" y1="14" x2="18" y2="24" stroke="#38BDF8" strokeWidth="1.5" opacity="0.4" />
    </svg>
  )
}

export function Logo(props: React.ComponentPropsWithoutRef<'svg'>) {
  return (
    <svg aria-hidden="true" viewBox="0 0 140 36" fill="none" {...props}>
      <circle cx="18" cy="18" r="15" stroke="#38BDF8" strokeWidth="2" />
      <circle cx="10" cy="14" r="3" fill="#38BDF8" opacity="0.8" />
      <circle cx="26" cy="14" r="3" fill="#38BDF8" opacity="0.8" />
      <circle cx="18" cy="24" r="3" fill="#38BDF8" opacity="0.8" />
      <line x1="10" y1="14" x2="26" y2="14" stroke="#38BDF8" strokeWidth="1.5" opacity="0.4" />
      <line x1="10" y1="14" x2="18" y2="24" stroke="#38BDF8" strokeWidth="1.5" opacity="0.4" />
      <line x1="26" y1="14" x2="18" y2="24" stroke="#38BDF8" strokeWidth="1.5" opacity="0.4" />
      <text x="40" y="24" fontFamily="system-ui, sans-serif" fontSize="18" fontWeight="700" fill="currentColor">
        SwarmOps
      </text>
    </svg>
  )
}
