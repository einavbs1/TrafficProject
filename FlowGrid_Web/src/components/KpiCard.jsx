import { TrendingUp, TrendingDown } from 'lucide-react'

export default function KpiCard({ label, value, change, icon: Icon, gradient, subtitle }) {
  const isPositive = change >= 0
  const isNeutral = Math.abs(change) < 0.5
  return (
    <div className="glass rounded-[var(--radius-card)] shadow-card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {!isNeutral && (
          <span className={`flex items-center gap-1 text-xs font-semibold ${isPositive ? 'text-success' : 'text-danger'}`}>
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {Math.abs(change)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-text">{value}</p>
      <p className="text-sm text-muted mt-0.5">{label}</p>
      {subtitle && <p className="text-xs text-muted/60 mt-0.5">{subtitle}</p>}
    </div>
  )
}
