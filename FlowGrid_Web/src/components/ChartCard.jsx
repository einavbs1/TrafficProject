export default function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <div className={`glass rounded-[var(--radius-card)] shadow-card p-6 ${className}`}>
      <div className="mb-5">
        <h3 className="text-lg font-bold text-text">{title}</h3>
        {subtitle && <p className="text-sm text-muted mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}
