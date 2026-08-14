import { useState } from 'react'
import { X, ChevronRight, Building2, Route } from 'lucide-react'

const ALL_DIRECTIONS = ['North', 'Northeast', 'East', 'Southeast', 'South', 'Southwest', 'West', 'Northwest']

export default function AddJunctionModal({ onClose, onAdd, initialDistrict, initialCity, existingDistricts = [] }) {
  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [district, setDistrict] = useState(initialDistrict || '')
  const [roadType, setRoadType] = useState('urban')
  const [city, setCity] = useState(initialCity || '')
  const [freeway, setFreeway] = useState('')
  const [location, setLocation] = useState('')
  const [selectedDirs, setSelectedDirs] = useState(['North', 'South'])
  const [signals, setSignals] = useState(4)
  const [model, setModel] = useState('DQN v3.2.1 (Latest)')
  const steps = ['Location', 'Directions', 'Signals', 'AI Model']

  const toggleDir = (dir) => {
    setSelectedDirs(prev => prev.includes(dir) ? prev.filter(d => d !== dir) : [...prev, dir])
  }

  const handleCreate = () => {
    if (!name.trim()) return
    onAdd({
      name: name.trim(),
      district,
      roadType,
      city: roadType === 'freeway' ? null : city.trim(),
      freeway: roadType === 'freeway' ? freeway.trim() : null,
      location: location.trim(),
      directions: selectedDirs,
      signals,
      model: model.split(' (')[0],
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="glass-strong rounded-[var(--radius-card)] shadow-card-hover w-full max-w-lg p-8 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text">Add New Junction</h2>
          <button onClick={onClose} className="text-muted hover:text-text cursor-pointer"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex items-center gap-1 mb-8">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center gap-1 flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold shrink-0 ${
                i <= step ? 'bg-gradient-to-r from-accent to-pink-500 text-white shadow-lg shadow-accent/20' : 'glass-subtle text-muted'
              }`}>{i + 1}</div>
              <span className={`text-xs font-medium hidden lg:block truncate ${i <= step ? 'text-text' : 'text-muted'}`}>{s}</span>
              {i < steps.length - 1 && <ChevronRight className="w-3 h-3 text-muted shrink-0" />}
            </div>
          ))}
        </div>

        <div className="space-y-4 mb-6 min-h-[180px]">
          {step === 0 && (
            <>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Junction Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Herzl Blvd Intersection" className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">District</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {existingDistricts.map(d => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDistrict(d)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition-all border ${
                        district === d
                          ? 'bg-gradient-to-r from-accent to-pink-500 text-white border-accent/30 shadow-lg shadow-accent/20'
                          : 'glass-subtle text-muted hover:text-text border-transparent'
                      }`}
                    >{d}</button>
                  ))}
                </div>
                <input
                  value={!existingDistricts.includes(district) ? district : ''}
                  onChange={e => setDistrict(e.target.value)}
                  placeholder="Or type a new district name..."
                  className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none"
                />
                {district && !existingDistricts.includes(district) && (
                  <p className="text-xs text-accent mt-1.5">New district: "{district}"</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-2">Road Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {[['urban', 'City Road', Building2], ['freeway', 'Freeway', Route]].map(([val, label, Icon]) => (
                    <button key={val} onClick={() => setRoadType(val)} className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl text-sm font-medium cursor-pointer transition-all ${
                      roadType === val ? 'bg-gradient-to-r from-accent to-pink-500 text-white shadow-lg shadow-accent/20' : 'glass-subtle text-muted hover:text-text'
                    }`}>
                      <Icon className="w-4 h-4" />{label}
                    </button>
                  ))}
                </div>
              </div>
              {roadType === 'urban' ? (
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">City</label>
                  <input value={city} onChange={e => setCity(e.target.value)} placeholder="e.g., Tel Aviv, Haifa..." className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Freeway Name</label>
                  <input value={freeway} onChange={e => setFreeway(e.target.value)} placeholder="e.g., Ayalon Highway (Route 20)" className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">GPS / Address</label>
                <input value={location} onChange={e => setLocation(e.target.value)} placeholder="Coordinates or address" className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
              </div>
            </>
          )}
          {step === 1 && (
            <div>
              <label className="block text-sm font-medium text-text mb-3">Directions (one camera each)</label>
              <div className="grid grid-cols-2 gap-2">
                {ALL_DIRECTIONS.map(dir => (
                  <button key={dir} onClick={() => toggleDir(dir)} className={`px-4 py-2.5 rounded-2xl text-sm font-medium cursor-pointer transition-all ${
                    selectedDirs.includes(dir) ? 'bg-gradient-to-r from-accent to-pink-500 text-white shadow-lg shadow-accent/20' : 'glass-subtle text-muted hover:text-text'
                  }`}>{dir}</button>
                ))}
              </div>
              <p className="text-xs text-muted mt-3">{selectedDirs.length} camera{selectedDirs.length !== 1 ? 's' : ''}</p>
            </div>
          )}
          {step === 2 && (
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Traffic Signals</label>
              <input type="number" value={signals} onChange={e => setSignals(+e.target.value)} min={2} max={24} className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
              <p className="text-xs text-muted mt-2">Recommended: {selectedDirs.length * 2}</p>
            </div>
          )}
          {step === 3 && (
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">DQN Model Version</label>
              <select value={model} onChange={e => setModel(e.target.value)} className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none">
                <option>DQN v3.2.1 (Latest)</option>
                <option>DQN v3.1.0 (Stable)</option>
                <option>DQN v2.9.5 (Legacy)</option>
              </select>
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <button onClick={() => step > 0 ? setStep(step - 1) : onClose()} className="flex-1 py-3 glass text-text font-semibold rounded-2xl hover:bg-accent/10 cursor-pointer text-sm">
            {step === 0 ? 'Cancel' : 'Back'}
          </button>
          <button onClick={() => step < steps.length - 1 ? setStep(step + 1) : handleCreate()} disabled={step === 0 && (!name.trim() || !district.trim())} className="flex-1 py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25 disabled:opacity-40">
            {step === steps.length - 1 ? 'Create Junction' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  )
}
