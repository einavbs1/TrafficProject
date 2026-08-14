export default function StatusPill({ status }) {
  const isActive = status === 'Active'
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
      isActive ? 'bg-success/15 text-success border-success/20' : 'bg-white/5 text-muted border-white/10'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-success' : 'bg-muted'}`} />
      {status}
    </span>
  )
}
