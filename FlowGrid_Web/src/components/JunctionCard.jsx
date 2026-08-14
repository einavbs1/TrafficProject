import { GitBranch, Camera, TrafficCone, Brain, MapPin } from 'lucide-react'

const STATUS_STYLE = {
  active: 'bg-success/15 text-success border-success/20',
  training: 'bg-warning/15 text-warning border-warning/20',
}

export default function JunctionCard({ junction, onSelect }) {
  return (
    <button
      onClick={() => onSelect(junction.id)}
      className="glass rounded-2xl shadow-card hover:shadow-card-hover p-5 text-left cursor-pointer group transition-all hover:scale-[1.01] w-full"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent/15 text-accent flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
            <GitBranch className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h3 className="font-bold text-text text-sm">{junction.name}</h3>
            <p className="text-xs text-muted flex items-center gap-1 mt-0.5">
              <MapPin className="w-3 h-3 shrink-0" />
              <span className="truncate">{junction.location}</span>
            </p>
          </div>
        </div>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize border shrink-0 ${STATUS_STYLE[junction.status]}`}>
          {junction.status}
        </span>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1"><Camera className="w-3 h-3" />{junction.cameras.length} cameras</span>
        <span className="flex items-center gap-1"><TrafficCone className="w-3 h-3" />{junction.signals} signals</span>
        <span className="flex items-center gap-1"><Brain className="w-3 h-3" />{junction.model}</span>
      </div>
      <div className="mt-2.5 flex flex-wrap gap-1">
        {junction.directions.map(d => (
          <span key={d} className="text-[10px] glass-subtle px-2 py-0.5 rounded-md text-muted">{d}</span>
        ))}
      </div>
    </button>
  )
}
