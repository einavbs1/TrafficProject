import { X, ArrowRight } from 'lucide-react'

const FLOW_STEPS = [
  { label: 'Vehicle Detected', color: 'from-accent to-blue-500' },
  { label: 'Queue Analysis', color: 'from-blue-500 to-cyan-500' },
  { label: 'DQN Inference', color: 'from-warning to-orange-500' },
  { label: 'Signal Update', color: 'from-success to-emerald-500' },
  { label: 'Metrics Logged', color: 'from-muted to-slate-500' },
]

export default function FlowchartModal({ junction, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="glass-strong rounded-[var(--radius-card)] shadow-card-hover w-full max-w-2xl p-8" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-xl font-bold text-text">Junction Flowchart</h2>
          <button onClick={onClose} className="text-muted hover:text-text cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-muted mb-6">{junction.name} — Traffic Signal Decision Pipeline</p>

        <div className="flex items-center justify-center gap-2 flex-wrap">
          {FLOW_STEPS.map((step, i) => (
            <div key={step.label} className="flex items-center gap-2">
              <div className={`bg-gradient-to-r ${step.color} text-white px-5 py-3 rounded-2xl text-sm font-semibold text-center min-w-[130px] shadow-lg`}>
                {step.label}
              </div>
              {i < FLOW_STEPS.length - 1 && (
                <ArrowRight className="w-5 h-5 text-accent shrink-0" />
              )}
            </div>
          ))}
        </div>

        <div className="mt-8 p-5 glass-subtle rounded-2xl">
          <p className="text-sm text-muted">
            Traffic flows from sensor detection through deep Q-network inference, resulting in optimized signal timing across {junction.signals} signals with {junction.cameras.length} camera feeds.
          </p>
        </div>
      </div>
    </div>
  )
}
