import { createContext, useContext, useState, useCallback, useMemo } from 'react'

const INITIAL_JUNCTIONS = [
  {
    id: 1,
    name: 'Central Ave Intersection',
    district: 'Tel Aviv',
    city: 'Tel Aviv',
    roadType: 'urban',
    location: '32.0853° N, 34.7818° E',
    directions: ['North', 'East', 'South', 'West'],
    signals: 8,
    model: 'DQN v3.2.1',
    status: 'active',
    cameras: [
      { id: 'CAM-101', name: 'North Corridor', direction: 'North', ip: '192.168.1.101', rtsp: 'rtsp://192.168.1.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-102', name: 'East Corridor', direction: 'East', ip: '192.168.1.102', rtsp: 'rtsp://192.168.1.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-103', name: 'South Corridor', direction: 'South', ip: '192.168.1.103', rtsp: 'rtsp://192.168.1.103:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.1.8' },
      { id: 'CAM-104', name: 'West Corridor', direction: 'West', ip: '192.168.1.104', rtsp: 'rtsp://192.168.1.104:554/stream1', status: 'offline', type: 'Fixed Camera', firmware: 'v4.0.3' },
    ],
  },
  {
    id: 2,
    name: 'Dizengoff Square',
    district: 'Tel Aviv',
    city: 'Tel Aviv',
    roadType: 'urban',
    location: '32.0770° N, 34.7744° E',
    directions: ['North', 'East', 'South', 'West'],
    signals: 8,
    model: 'DQN v3.2.1',
    status: 'active',
    cameras: [
      { id: 'CAM-201', name: 'North Entry', direction: 'North', ip: '192.168.2.101', rtsp: 'rtsp://192.168.2.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-202', name: 'East Entry', direction: 'East', ip: '192.168.2.102', rtsp: 'rtsp://192.168.2.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-203', name: 'South Entry', direction: 'South', ip: '192.168.2.103', rtsp: 'rtsp://192.168.2.103:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.1.8' },
      { id: 'CAM-204', name: 'West Entry', direction: 'West', ip: '192.168.2.104', rtsp: 'rtsp://192.168.2.104:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
    ],
  },
  {
    id: 3,
    name: 'Herzl Blvd Junction',
    district: 'Tel Aviv',
    city: 'Ramat Gan',
    roadType: 'urban',
    location: '32.0830° N, 34.8100° E',
    directions: ['North', 'South', 'West'],
    signals: 6,
    model: 'DQN v3.1.0',
    status: 'active',
    cameras: [
      { id: 'CAM-301', name: 'North Approach', direction: 'North', ip: '192.168.3.101', rtsp: 'rtsp://192.168.3.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-302', name: 'South Approach', direction: 'South', ip: '192.168.3.102', rtsp: 'rtsp://192.168.3.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-303', name: 'West Ramp', direction: 'West', ip: '192.168.3.103', rtsp: 'rtsp://192.168.3.103:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.1.8' },
    ],
  },
  {
    id: 4,
    name: 'Ayalon Hwy — Hashalom Exit',
    district: 'Tel Aviv',
    city: null,
    roadType: 'freeway',
    freeway: 'Ayalon Highway (Route 20)',
    location: '32.0700° N, 34.7900° E',
    directions: ['North', 'South'],
    signals: 4,
    model: 'DQN v3.2.1',
    status: 'active',
    cameras: [
      { id: 'CAM-401', name: 'Northbound', direction: 'North', ip: '192.168.4.101', rtsp: 'rtsp://192.168.4.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-402', name: 'Southbound', direction: 'South', ip: '192.168.4.102', rtsp: 'rtsp://192.168.4.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
    ],
  },
  {
    id: 5,
    name: 'Route 2 — Netanya Interchange',
    district: 'Haifa',
    city: null,
    roadType: 'freeway',
    freeway: 'Coastal Highway (Route 2)',
    location: '32.3340° N, 34.8560° E',
    directions: ['North', 'East', 'South', 'West'],
    signals: 8,
    model: 'DQN v3.1.0',
    status: 'training',
    cameras: [
      { id: 'CAM-501', name: 'North Lane', direction: 'North', ip: '192.168.5.101', rtsp: 'rtsp://192.168.5.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-502', name: 'East Ramp', direction: 'East', ip: '192.168.5.102', rtsp: 'rtsp://192.168.5.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-503', name: 'South Lane', direction: 'South', ip: '192.168.5.103', rtsp: 'rtsp://192.168.5.103:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.1.8' },
      { id: 'CAM-504', name: 'West Ramp', direction: 'West', ip: '192.168.5.104', rtsp: 'rtsp://192.168.5.104:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
    ],
  },
  {
    id: 6,
    name: 'Horev Center Junction',
    district: 'Haifa',
    city: 'Haifa',
    roadType: 'urban',
    location: '32.7880° N, 34.9780° E',
    directions: ['North', 'East', 'South'],
    signals: 6,
    model: 'DQN v3.2.1',
    status: 'active',
    cameras: [
      { id: 'CAM-601', name: 'North Boulevard', direction: 'North', ip: '192.168.6.101', rtsp: 'rtsp://192.168.6.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-602', name: 'East Tunnel Exit', direction: 'East', ip: '192.168.6.102', rtsp: 'rtsp://192.168.6.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-603', name: 'South Approach', direction: 'South', ip: '192.168.6.103', rtsp: 'rtsp://192.168.6.103:554/stream1', status: 'offline', type: 'PTZ Camera', firmware: 'v4.1.8' },
    ],
  },
  {
    id: 7,
    name: 'Jaffa Gate Roundabout',
    district: 'Jerusalem',
    city: 'Jerusalem',
    roadType: 'urban',
    location: '31.7767° N, 35.2281° E',
    directions: ['North', 'Northeast', 'East', 'South', 'Southwest', 'West'],
    signals: 12,
    model: 'DQN v2.9.5',
    status: 'active',
    cameras: [
      { id: 'CAM-701', name: 'North Main', direction: 'North', ip: '192.168.7.101', rtsp: 'rtsp://192.168.7.101:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
      { id: 'CAM-702', name: 'Northeast Lane', direction: 'Northeast', ip: '192.168.7.102', rtsp: 'rtsp://192.168.7.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-703', name: 'East Boulevard', direction: 'East', ip: '192.168.7.103', rtsp: 'rtsp://192.168.7.103:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.1.8' },
      { id: 'CAM-704', name: 'South Gate', direction: 'South', ip: '192.168.7.104', rtsp: 'rtsp://192.168.7.104:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.0.3' },
      { id: 'CAM-705', name: 'Southwest Alley', direction: 'Southwest', ip: '192.168.7.105', rtsp: 'rtsp://192.168.7.105:554/stream1', status: 'offline', type: 'Fixed Camera', firmware: 'v4.0.3' },
      { id: 'CAM-706', name: 'West Promenade', direction: 'West', ip: '192.168.7.106', rtsp: 'rtsp://192.168.7.106:554/stream1', status: 'online', type: 'PTZ Camera', firmware: 'v4.2.1' },
    ],
  },
  {
    id: 8,
    name: 'Route 1 — Latrun Interchange',
    district: 'Jerusalem',
    city: null,
    roadType: 'freeway',
    freeway: 'Jerusalem Highway (Route 1)',
    location: '31.8380° N, 34.9780° E',
    directions: ['East', 'West'],
    signals: 4,
    model: 'DQN v3.2.1',
    status: 'training',
    cameras: [
      { id: 'CAM-801', name: 'Eastbound', direction: 'East', ip: '192.168.8.101', rtsp: 'rtsp://192.168.8.101:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
      { id: 'CAM-802', name: 'Westbound', direction: 'West', ip: '192.168.8.102', rtsp: 'rtsp://192.168.8.102:554/stream1', status: 'online', type: 'Fixed Camera', firmware: 'v4.2.1' },
    ],
  },
]

// The one junction in this app backed by real data: its Dashboard panel is
// wired to the actual PPO agent running a live SUMO episode (see
// pages/Dashboard.jsx), not the Math.random() mock the other junctions use.
export const LIVE_JUNCTION_ID = 100

const LIVE_JUNCTION = {
  id: LIVE_JUNCTION_ID,
  name: 'Live Junction (SUMO Simulation)',
  district: 'Simulation',
  city: 'FlowGrid Lab',
  roadType: 'urban',
  location: 'Simulated intersection -- SUMO, no GPS coordinates',
  directions: ['North', 'East', 'South', 'West'],
  signals: 4,
  model: 'MaskablePPO V8',
  status: 'active',
  cameras: [
    { id: 'CAM-N', name: 'North Approach', direction: 'North', ip: '-', rtsp: '-', status: 'online', type: 'SUMO Simulation', firmware: '-' },
    { id: 'CAM-E', name: 'East Approach', direction: 'East', ip: '-', rtsp: '-', status: 'online', type: 'SUMO Simulation', firmware: '-' },
    { id: 'CAM-S', name: 'South Approach', direction: 'South', ip: '-', rtsp: '-', status: 'online', type: 'SUMO Simulation', firmware: '-' },
    { id: 'CAM-W', name: 'West Approach', direction: 'West', ip: '-', rtsp: '-', status: 'online', type: 'SUMO Simulation', firmware: '-' },
  ],
}

const JunctionContext = createContext(null)

export function JunctionProvider({ children }) {
  const [junctions, setJunctions] = useState([LIVE_JUNCTION, ...INITIAL_JUNCTIONS])
  const [activeJunctionId, setActiveJunctionId] = useState(null)

  const activeJunction = junctions.find(j => j.id === activeJunctionId) || null

  const hierarchy = useMemo(() => {
    const districts = {}
    for (const j of junctions) {
      if (!districts[j.district]) {
        districts[j.district] = { cities: {}, freeways: {} }
      }
      if (j.roadType === 'freeway') {
        const fw = j.freeway || 'Unnamed Freeway'
        if (!districts[j.district].freeways[fw]) {
          districts[j.district].freeways[fw] = []
        }
        districts[j.district].freeways[fw].push(j)
      } else {
        const city = j.city || 'Other'
        if (!districts[j.district].cities[city]) {
          districts[j.district].cities[city] = []
        }
        districts[j.district].cities[city].push(j)
      }
    }
    return districts
  }, [junctions])

  const selectJunction = useCallback((id) => {
    setActiveJunctionId(id)
  }, [])

  const clearJunction = useCallback(() => {
    setActiveJunctionId(null)
  }, [])

  const updateJunction = useCallback((id, updates) => {
    setJunctions(prev => prev.map(j => j.id === id ? { ...j, ...updates } : j))
  }, [])

  const addJunction = useCallback((junction) => {
    const newId = Math.max(...junctions.map(j => j.id), 0) + 1
    const directions = junction.directions || ['North', 'South']
    const newJunction = {
      id: newId,
      name: junction.name,
      district: junction.district || 'Tel Aviv',
      city: junction.roadType === 'freeway' ? null : (junction.city || 'Other'),
      roadType: junction.roadType || 'urban',
      freeway: junction.freeway || null,
      location: junction.location || '',
      directions,
      signals: junction.signals || directions.length * 2,
      model: junction.model || 'DQN v3.2.1',
      status: 'training',
      cameras: directions.map((dir, i) => ({
        id: `CAM-${newId}0${i + 1}`,
        name: `${dir} Camera`,
        direction: dir,
        ip: `192.168.${newId + 10}.${101 + i}`,
        rtsp: `rtsp://192.168.${newId + 10}.${101 + i}:554/stream1`,
        status: 'online',
        type: i % 2 === 0 ? 'PTZ Camera' : 'Fixed Camera',
        firmware: 'v4.2.1',
      })),
    }
    setJunctions(prev => [...prev, newJunction])
    return newId
  }, [junctions])

  return (
    <JunctionContext.Provider value={{
      junctions,
      hierarchy,
      activeJunction,
      activeJunctionId,
      selectJunction,
      clearJunction,
      addJunction,
      updateJunction,
      hasSelectedJunction: !!activeJunctionId,
    }}>
      {children}
    </JunctionContext.Provider>
  )
}

export const useJunction = () => useContext(JunctionContext)
