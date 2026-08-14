import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GitBranch, Camera, TrafficCone, Brain, Plus, MapPin, Power } from 'lucide-react'
import { useJunction } from '../JunctionContext'
import AddJunctionModal from '../components/AddJunctionModal'
import FlowchartModal from '../components/FlowchartModal'

const STATUS_STYLE = {
  active: 'bg-success/15 text-success border-success/20',
  training: 'bg-warning/15 text-warning border-warning/20',
}

export default function Junctions() {
  const { junctions, hierarchy, selectJunction, addJunction, updateJunction, activeJunctionId } = useJunction()
  const [showAdd, setShowAdd] = useState(false)
  const [flowJunction, setFlowJunction] = useState(null)
  const navigate = useNavigate()

  const handleSwitch = (id) => {
    selectJunction(id)
    navigate('/')
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text">Junctions</h1>
          <p className="text-muted mt-1">All traffic junctions — switch or add new</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25"
        >
          <Plus className="w-4 h-4" />
          Add Junction
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {junctions.map(junction => {
          const isActive = junction.id === activeJunctionId
          return (
            <div
              key={junction.id}
              className={`glass rounded-[var(--radius-card)] shadow-card hover:shadow-card-hover p-6 ${isActive ? 'ring-2 ring-accent/40' : ''}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isActive ? 'bg-accent text-white' : 'bg-accent/15 text-accent'}`}>
                    <GitBranch className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-text">{junction.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full capitalize border ${STATUS_STYLE[junction.status]}`}>
                        {junction.status}
                      </span>
                      {isActive && <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-accent/15 text-accent border border-accent/20">Current</span>}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => updateJunction(junction.id, { status: junction.status === 'active' ? 'training' : 'active' })}
                  className={`relative w-12 h-6 rounded-full cursor-pointer transition-colors shrink-0 ${
                    junction.status === 'active' ? 'bg-success' : 'bg-warning/40'
                  }`}
                  title={junction.status === 'active' ? 'Set to Training' : 'Set to Active'}
                >
                  <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform flex items-center justify-center ${
                    junction.status === 'active' ? 'left-[calc(100%-1.375rem)]' : 'left-0.5'
                  }`}>
                    <Power className={`w-3 h-3 ${junction.status === 'active' ? 'text-success' : 'text-warning'}`} />
                  </span>
                </button>
              </div>

              {junction.location && (
                <div className="flex items-center gap-1.5 text-xs text-muted mb-4">
                  <MapPin className="w-3 h-3" />
                  {junction.location}
                </div>
              )}

              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="glass-subtle rounded-xl p-3 text-center">
                  <Camera className="w-4 h-4 text-muted mx-auto mb-1" />
                  <p className="text-lg font-bold text-text">{junction.cameras.length}</p>
                  <p className="text-xs text-muted">Cameras</p>
                </div>
                <div className="glass-subtle rounded-xl p-3 text-center">
                  <TrafficCone className="w-4 h-4 text-muted mx-auto mb-1" />
                  <p className="text-lg font-bold text-text">{junction.signals}</p>
                  <p className="text-xs text-muted">Signals</p>
                </div>
                <div className="glass-subtle rounded-xl p-3 text-center">
                  <Brain className="w-4 h-4 text-muted mx-auto mb-1" />
                  <p className="text-xs font-bold text-text mt-1">{junction.model}</p>
                  <p className="text-xs text-muted">Model</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 mb-4">
                {junction.directions.map(dir => (
                  <span key={dir} className="text-xs glass-subtle px-2.5 py-1 rounded-lg text-muted">{dir}</span>
                ))}
              </div>

              <div className="flex gap-2">
                {!isActive && (
                  <button
                    onClick={() => handleSwitch(junction.id)}
                    className="flex-1 py-2.5 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-medium rounded-2xl flex items-center justify-center gap-2 cursor-pointer text-sm shadow-lg shadow-accent/20"
                  >
                    Switch to this
                  </button>
                )}
                <button
                  onClick={() => setFlowJunction(junction)}
                  className={`${isActive ? 'flex-1' : ''} py-2.5 px-4 glass hover:bg-accent/10 text-text font-medium rounded-2xl flex items-center justify-center gap-2 cursor-pointer text-sm`}
                >
                  <GitBranch className="w-4 h-4" />
                  Flowchart
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {showAdd && (
        <AddJunctionModal
          onClose={() => setShowAdd(false)}
          onAdd={addJunction}
          existingDistricts={Object.keys(hierarchy)}
        />
      )}
      {flowJunction && <FlowchartModal junction={flowJunction} onClose={() => setFlowJunction(null)} />}
    </div>
  )
}
