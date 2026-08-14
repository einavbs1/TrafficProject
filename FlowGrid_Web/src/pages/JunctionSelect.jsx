import { useState, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJunction } from '../JunctionContext'
import { Plus, X, ChevronRight, Search, Building2, Map, ChevronLeft, Route } from 'lucide-react'
import AddJunctionModal from '../components/AddJunctionModal'
import JunctionCard from '../components/JunctionCard'
import Tour from '../Tour'

export default function JunctionSelect() {
  const { junctions, hierarchy, selectJunction, addJunction } = useJunction()
  const [showAdd, setShowAdd] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedDistrict, setSelectedDistrict] = useState(null)
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [showNewDistrict, setShowNewDistrict] = useState(false)
  const [newDistrictName, setNewDistrictName] = useState('')
  const navigate = useNavigate()
  const searchRef = useRef(null)
  const districtGridRef = useRef(null)

  const handleSelect = (id) => {
    selectJunction(id)
    navigate('/')
  }

  const handleAdd = (data) => {
    const newId = addJunction(data)
    handleSelect(newId)
  }

  const searchResults = useMemo(() => {
    if (!search.trim()) return null
    const q = search.toLowerCase()
    return junctions.filter(j =>
      j.name.toLowerCase().includes(q) ||
      j.district.toLowerCase().includes(q) ||
      (j.city && j.city.toLowerCase().includes(q)) ||
      (j.freeway && j.freeway.toLowerCase().includes(q)) ||
      j.location.toLowerCase().includes(q)
    )
  }, [search, junctions])

  const districtData = selectedDistrict ? hierarchy[selectedDistrict] : null
  const cities = districtData ? Object.keys(districtData.cities) : []
  const freeways = districtData ? Object.keys(districtData.freeways) : []

  const groupJunctions = useMemo(() => {
    if (!selectedDistrict || !selectedGroup || !districtData) return []
    if (selectedGroup.startsWith('freeway:')) {
      const fw = selectedGroup.replace('freeway:', '')
      return districtData.freeways[fw] || []
    }
    return districtData.cities[selectedGroup] || []
  }, [selectedDistrict, selectedGroup, districtData])

  const goBack = () => {
    if (selectedGroup) {
      setSelectedGroup(null)
    } else if (selectedDistrict) {
      setSelectedDistrict(null)
    }
  }

  const breadcrumb = []
  if (selectedDistrict) breadcrumb.push(selectedDistrict)
  if (selectedGroup) breadcrumb.push(selectedGroup.replace('freeway:', ''))

  const isSearching = !!search.trim()

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text">Select Junction</h1>
        <p className="text-muted mt-1">Choose a junction to monitor and manage, or add a new one</p>
      </div>

        <div className="max-w-lg mb-8" ref={searchRef}>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search junctions by name, city, district, or freeway..."
              className="w-full pl-11 pr-4 py-3 rounded-2xl glass-strong text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {isSearching ? (
          <div>
            <p className="text-sm text-muted mb-4">{searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{search}"</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {searchResults.map(j => (
                <JunctionCard key={j.id} junction={j} onSelect={handleSelect} />
              ))}
              {searchResults.length === 0 && (
                <div className="col-span-2 text-center py-16">
                  <Search className="w-10 h-10 text-muted/30 mx-auto mb-3" />
                  <p className="text-muted">No junctions found matching your search</p>
                </div>
              )}
            </div>
          </div>
        ) : !selectedDistrict ? (
          <>
            {breadcrumb.length > 0 && (
              <div className="flex items-center gap-1.5 mb-6 text-sm">
                <button onClick={goBack} className="text-accent hover:text-accent-hover font-medium cursor-pointer flex items-center gap-1">
                  <ChevronLeft className="w-4 h-4" />Back
                </button>
              </div>
            )}
            <p className="text-sm font-semibold text-muted uppercase tracking-wider mb-4">Select District</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8" ref={districtGridRef}>
              {Object.keys(hierarchy).map(district => {
                const data = hierarchy[district]
                const totalJunctions = Object.values(data.cities).flat().length + Object.values(data.freeways).flat().length
                const totalCities = Object.keys(data.cities).length
                const totalFreeways = Object.keys(data.freeways).length
                return (
                  <button
                    key={district}
                    onClick={() => setSelectedDistrict(district)}
                    className="glass rounded-[var(--radius-card)] shadow-card hover:shadow-card-hover p-6 text-left cursor-pointer group transition-all hover:scale-[1.02]"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-2xl bg-accent/15 text-accent flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
                        <Map className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-text">{district}</h3>
                        <p className="text-xs text-muted">{totalJunctions} junction{totalJunctions !== 1 ? 's' : ''}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted">
                      {totalCities > 0 && <span className="flex items-center gap-1"><Building2 className="w-3 h-3" />{totalCities} cit{totalCities !== 1 ? 'ies' : 'y'}</span>}
                      {totalFreeways > 0 && <span className="flex items-center gap-1"><Route className="w-3 h-3" />{totalFreeways} freeway{totalFreeways !== 1 ? 's' : ''}</span>}
                    </div>
                    <div className="mt-3 flex items-center justify-end gap-1 text-accent text-sm font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
                      Browse <ChevronRight className="w-4 h-4" />
                    </div>
                  </button>
                )
              })}

              {showNewDistrict ? (
                <div className="glass rounded-[var(--radius-card)] shadow-card p-6 flex flex-col justify-between">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-2xl bg-success/15 text-success flex items-center justify-center">
                      <Plus className="w-6 h-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-text mb-1.5">New District Name</p>
                      <input
                        value={newDistrictName}
                        onChange={e => setNewDistrictName(e.target.value)}
                        placeholder="e.g., South, Negev..."
                        autoFocus
                        className="w-full px-3 py-2 rounded-xl glass-input text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30"
                        onKeyDown={e => {
                          if (e.key === 'Enter' && newDistrictName.trim()) {
                            setSelectedDistrict(newDistrictName.trim())
                            setShowNewDistrict(false)
                            setShowAdd(true)
                            setNewDistrictName('')
                          }
                          if (e.key === 'Escape') { setShowNewDistrict(false); setNewDistrictName('') }
                        }}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setShowNewDistrict(false); setNewDistrictName('') }}
                      className="flex-1 py-2 glass text-muted text-sm rounded-xl cursor-pointer hover:text-text"
                    >Cancel</button>
                    <button
                      onClick={() => {
                        if (!newDistrictName.trim()) return
                        setSelectedDistrict(newDistrictName.trim())
                        setShowNewDistrict(false)
                        setShowAdd(true)
                        setNewDistrictName('')
                      }}
                      disabled={!newDistrictName.trim()}
                      className="flex-1 py-2 bg-gradient-to-r from-accent to-pink-500 text-white text-sm font-semibold rounded-xl cursor-pointer disabled:opacity-40"
                    >Create & Add Junction</button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowNewDistrict(true)}
                  className="glass rounded-[var(--radius-card)] shadow-card hover:shadow-card-hover p-6 text-left cursor-pointer group transition-all hover:scale-[1.02] border-2 border-dashed border-border hover:border-accent/30 flex flex-col items-center justify-center gap-3 min-h-[140px]"
                >
                  <div className="w-12 h-12 rounded-2xl bg-accent/10 text-accent flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
                    <Plus className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-semibold text-muted group-hover:text-text transition-colors">Add New District</span>
                </button>
              )}
            </div>

            <div className="flex items-center justify-center">
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-2 px-6 py-3 glass hover:bg-accent/10 text-text font-semibold rounded-2xl cursor-pointer text-sm border-2 border-dashed border-border hover:border-accent/30"
              >
                <Plus className="w-5 h-5" />
                Add New Junction
              </button>
            </div>
          </>
        ) : !selectedGroup ? (
          <div>
            <div className="flex items-center gap-2 mb-6">
              <button onClick={goBack} className="text-accent hover:text-accent-hover cursor-pointer flex items-center gap-1 text-sm font-medium">
                <ChevronLeft className="w-4 h-4" />All Districts
              </button>
              <ChevronRight className="w-3 h-3 text-muted" />
              <span className="text-sm font-semibold text-text">{selectedDistrict}</span>
            </div>

            {cities.length > 0 && (
              <>
                <p className="text-sm font-semibold text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Building2 className="w-4 h-4" />Cities
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {cities.map(city => {
                    const cityJunctions = districtData.cities[city]
                    return (
                      <button
                        key={city}
                        onClick={() => setSelectedGroup(city)}
                        className="glass rounded-2xl shadow-card hover:shadow-card-hover p-5 text-left cursor-pointer group transition-all hover:scale-[1.02]"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-accent/15 text-accent flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
                            <Building2 className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className="font-bold text-text">{city}</h3>
                            <p className="text-xs text-muted">{cityJunctions.length} junction{cityJunctions.length !== 1 ? 's' : ''}</p>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </>
            )}

            {freeways.length > 0 && (
              <>
                <p className="text-sm font-semibold text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Route className="w-4 h-4" />Freeways
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {freeways.map(fw => {
                    const fwJunctions = districtData.freeways[fw]
                    return (
                      <button
                        key={fw}
                        onClick={() => setSelectedGroup(`freeway:${fw}`)}
                        className="glass rounded-2xl shadow-card hover:shadow-card-hover p-5 text-left cursor-pointer group transition-all hover:scale-[1.02]"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-warning/15 text-warning flex items-center justify-center group-hover:bg-warning group-hover:text-white transition-colors">
                            <Route className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className="font-bold text-text text-sm">{fw}</h3>
                            <p className="text-xs text-muted">{fwJunctions.length} junction{fwJunctions.length !== 1 ? 's' : ''}</p>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </>
            )}

            <div className="flex items-center justify-center mt-4">
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-2 px-5 py-2.5 glass hover:bg-accent/10 text-text font-medium rounded-2xl cursor-pointer text-sm border-2 border-dashed border-border hover:border-accent/30"
              >
                <Plus className="w-4 h-4" />
                Add junction to {selectedDistrict}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2 mb-6">
              <button onClick={() => { setSelectedGroup(null); setSelectedDistrict(null) }} className="text-accent hover:text-accent-hover cursor-pointer text-sm font-medium">Districts</button>
              <ChevronRight className="w-3 h-3 text-muted" />
              <button onClick={goBack} className="text-accent hover:text-accent-hover cursor-pointer text-sm font-medium">{selectedDistrict}</button>
              <ChevronRight className="w-3 h-3 text-muted" />
              <span className="text-sm font-semibold text-text">{selectedGroup.replace('freeway:', '')}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {groupJunctions.map(j => (
                <JunctionCard key={j.id} junction={j} onSelect={handleSelect} />
              ))}
            </div>

            <div className="flex items-center justify-center">
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-2 px-5 py-2.5 glass hover:bg-accent/10 text-text font-medium rounded-2xl cursor-pointer text-sm border-2 border-dashed border-border hover:border-accent/30"
              >
                <Plus className="w-4 h-4" />
                Add junction here
              </button>
            </div>
          </div>
        )}

      {showAdd && (
        <AddJunctionModal
          onClose={() => setShowAdd(false)}
          onAdd={handleAdd}
          initialDistrict={selectedDistrict}
          initialCity={selectedGroup && !selectedGroup.startsWith('freeway:') ? selectedGroup : ''}
          existingDistricts={Object.keys(hierarchy)}
        />
      )}

      <Tour
        steps={[
          {
            target: searchRef,
            title: 'Find a junction',
            text: 'Search by name, city, district, or freeway to jump straight to any junction instead of browsing the hierarchy below.',
          },
          {
            target: districtGridRef,
            title: 'Browse by district',
            text: 'Junctions are grouped by district, then by city or freeway. Click a district to drill in. "Live Junction (SUMO Simulation)" under Simulation is the one backed by the real trained PPO agent -- every other junction here is a UI mockup with simulated numbers.',
          },
        ]}
      />
    </div>
  )
}
