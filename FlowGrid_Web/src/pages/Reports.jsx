import { useState, useMemo } from 'react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'
import {
  Clock, Car, Zap, Activity, AlertTriangle, CameraOff,
  WifiOff, ShieldAlert, ServerCrash, CircleDot, ChevronDown,
  CheckCircle2, XCircle, Info, GitBranch, Filter, TriangleAlert
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useJunction } from '../JunctionContext'
import KpiCard from '../components/KpiCard'
import ChartCard from '../components/ChartCard'

const CHART_ACCENT = '#7c5cfc'
const CHART_PINK = '#ec4899'
const CHART_GREEN = '#34d399'
const CHART_WARNING = '#fbbf24'
const CHART_DANGER = '#f87171'

function seededRandom(seed) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function generateJunctionData(junctionId, junctionName, cameraCount, directionNames) {
  const rng = seededRandom(junctionId * 137 + 42)
  const r = (min, max) => Math.floor(rng() * (max - min + 1)) + min

  const hourly = Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(i).padStart(2, '0')}:00`,
    vehicles: r(20 + cameraCount * 10, 80 + cameraCount * 60),
    avgWait: r(8, 55),
  }))

  const weekly = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => {
    const row = { day }
    directionNames.forEach(dir => { row[dir] = r(100, 600) })
    return row
  })

  const monthly = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map(month => ({
    month,
    score: r(68, 98),
  }))

  const totalVehicles = hourly.reduce((s, h) => s + h.vehicles, 0)
  const avgWait = (hourly.reduce((s, h) => s + h.avgWait, 0) / 24).toFixed(1)
  const efficiency = r(75, 96)
  const uptime = (97 + rng() * 3).toFixed(1)
  const totalFailures = r(0, 12)
  const cameraOffline = r(0, Math.min(2, cameraCount))

  const pieData = [
    { name: 'Green', value: r(35, 55), color: CHART_GREEN },
    { name: 'Yellow', value: r(10, 20), color: CHART_WARNING },
    { name: 'Red', value: r(30, 50), color: CHART_DANGER },
  ]
  const pieTotal = pieData.reduce((s, d) => s + d.value, 0)
  pieData.forEach(d => { d.value = Math.round(d.value / pieTotal * 100) })

  const INCIDENT_TYPES = [
    { type: 'Camera Offline', severity: 'warning', icon: 'CameraOff' },
    { type: 'Signal Malfunction', severity: 'critical', icon: 'AlertTriangle' },
    { type: 'Connection Lost', severity: 'critical', icon: 'WifiOff' },
    { type: 'DQN Model Timeout', severity: 'warning', icon: 'ServerCrash' },
    { type: 'Sensor Drift Detected', severity: 'info', icon: 'Info' },
    { type: 'Power Fluctuation', severity: 'critical', icon: 'Zap' },
    { type: 'Firmware Update Failed', severity: 'warning', icon: 'ShieldAlert' },
    { type: 'Queue Overflow', severity: 'warning', icon: 'AlertTriangle' },
    { type: 'Camera Feed Frozen', severity: 'warning', icon: 'CameraOff' },
    { type: 'Emergency Override Activated', severity: 'info', icon: 'ShieldAlert' },
  ]

  const incidentCount = r(3, 14)
  const incidents = Array.from({ length: incidentCount }, (_, i) => {
    const inc = INCIDENT_TYPES[r(0, INCIDENT_TYPES.length - 1)]
    const daysAgo = r(0, 29)
    const hour = r(0, 23)
    const minute = r(0, 59)
    const date = new Date(2026, 4, 16 - daysAgo, hour, minute)
    const resolved = rng() > 0.25
    return {
      id: `INC-${junctionId}${String(i + 1).padStart(3, '0')}`,
      ...inc,
      junction: junctionName,
      junctionId,
      timestamp: date,
      resolved,
      duration: resolved ? `${r(2, 180)} min` : null,
    }
  }).sort((a, b) => b.timestamp - a.timestamp)

  const incidentTimeline = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(2026, 4, 16 - (29 - i))
    const dayStr = `${d.getMonth() + 1}/${d.getDate()}`
    const dayIncidents = incidents.filter(inc => {
      const id = inc.timestamp
      return id.getDate() === d.getDate() && id.getMonth() === d.getMonth()
    })
    return {
      date: dayStr,
      critical: dayIncidents.filter(x => x.severity === 'critical').length,
      warning: dayIncidents.filter(x => x.severity === 'warning').length,
      info: dayIncidents.filter(x => x.severity === 'info').length,
    }
  })

  return {
    hourly, weekly, monthly, pieData, incidents, incidentTimeline,
    kpis: {
      avgWait: `${avgWait}s`,
      avgWaitChange: r(-20, 15),
      totalVehicles: totalVehicles.toLocaleString(),
      vehicleChange: r(-5, 25),
      efficiency: `${efficiency}%`,
      efficiencyChange: r(-8, 12),
      uptime: `${uptime}%`,
      uptimeChange: parseFloat((rng() * 2 - 0.5).toFixed(1)),
      totalFailures,
      failureChange: r(-30, 30),
      cameraOffline,
    },
    directionNames,
  }
}

const SEVERITY_STYLES = {
  critical: { bg: 'bg-danger/12', text: 'text-danger', border: 'border-danger/20', dot: 'bg-danger' },
  warning: { bg: 'bg-warning/12', text: 'text-warning', border: 'border-warning/20', dot: 'bg-warning' },
  info: { bg: 'bg-accent/12', text: 'text-accent', border: 'border-accent/20', dot: 'bg-accent' },
}

const INCIDENT_ICONS = {
  CameraOff, AlertTriangle: TriangleAlert, WifiOff, ServerCrash, Info, Zap, ShieldAlert,
}

const DIR_COLORS = [CHART_ACCENT, CHART_PINK, CHART_GREEN, '#fbbf24', '#f97316', '#06b6d4', '#8b5cf6', '#64748b']

export default function Reports() {
  const { isDark } = useTheme()
  const { junctions, activeJunctionId } = useJunction()
  const [range, setRange] = useState('today')
  const [selectedJunctionId, setSelectedJunctionId] = useState(() =>
    activeJunctionId ? String(activeJunctionId) : 'all'
  )
  const [showJunctionPicker, setShowJunctionPicker] = useState(false)
  const [severityFilter, setSeverityFilter] = useState('all')
  const [incidentPage, setIncidentPage] = useState(0)

  const INCIDENTS_PER_PAGE = 8

  const allJunctionData = useMemo(() => {
    const map = {}
    for (const j of junctions) {
      map[j.id] = generateJunctionData(j.id, j.name, j.cameras.length, j.directions)
    }
    return map
  }, [junctions])

  const aggregateData = useMemo(() => {
    const allData = Object.values(allJunctionData)
    if (allData.length === 0) return null

    const hourly = Array.from({ length: 24 }, (_, i) => ({
      hour: `${String(i).padStart(2, '0')}:00`,
      vehicles: allData.reduce((s, d) => s + d.hourly[i].vehicles, 0),
      avgWait: Math.round(allData.reduce((s, d) => s + d.hourly[i].avgWait, 0) / allData.length),
    }))

    const totalVehicles = allData.reduce((s, d) => s + parseInt(d.kpis.totalVehicles.replace(/,/g, '')), 0)
    const avgWait = (allData.reduce((s, d) => s + parseFloat(d.kpis.avgWait), 0) / allData.length).toFixed(1)
    const avgEfficiency = Math.round(allData.reduce((s, d) => s + parseInt(d.kpis.efficiency), 0) / allData.length)
    const avgUptime = (allData.reduce((s, d) => s + parseFloat(d.kpis.uptime), 0) / allData.length).toFixed(1)
    const totalFailures = allData.reduce((s, d) => s + d.kpis.totalFailures, 0)
    const totalCameraOffline = allData.reduce((s, d) => s + d.kpis.cameraOffline, 0)

    const allIncidents = allData.flatMap(d => d.incidents).sort((a, b) => b.timestamp - a.timestamp)

    const incidentTimeline = Array.from({ length: 30 }, (_, i) => {
      const d = new Date(2026, 4, 16 - (29 - i))
      const dayStr = `${d.getMonth() + 1}/${d.getDate()}`
      return {
        date: dayStr,
        critical: allData.reduce((s, jd) => s + jd.incidentTimeline[i].critical, 0),
        warning: allData.reduce((s, jd) => s + jd.incidentTimeline[i].warning, 0),
        info: allData.reduce((s, jd) => s + jd.incidentTimeline[i].info, 0),
      }
    })

    const junctionCompare = junctions.map(j => ({
      name: j.name.length > 18 ? j.name.slice(0, 16) + '…' : j.name,
      vehicles: parseInt(allJunctionData[j.id].kpis.totalVehicles.replace(/,/g, '')),
      efficiency: parseInt(allJunctionData[j.id].kpis.efficiency),
      failures: allJunctionData[j.id].kpis.totalFailures,
    }))

    const monthly = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((month, i) => ({
      month,
      score: Math.round(allData.reduce((s, d) => s + d.monthly[i].score, 0) / allData.length),
    }))

    return {
      hourly, monthly, incidents: allIncidents, incidentTimeline, junctionCompare,
      kpis: {
        avgWait: `${avgWait}s`, avgWaitChange: -8,
        totalVehicles: totalVehicles.toLocaleString(), vehicleChange: 12,
        efficiency: `${avgEfficiency}%`, efficiencyChange: 3,
        uptime: `${avgUptime}%`, uptimeChange: 0.1,
        totalFailures, failureChange: -5,
        cameraOffline: totalCameraOffline,
      },
    }
  }, [allJunctionData, junctions])

  const isAll = selectedJunctionId === 'all'
  const currentJunction = !isAll ? junctions.find(j => j.id === parseInt(selectedJunctionId)) : null
  const data = isAll ? aggregateData : allJunctionData[parseInt(selectedJunctionId)]

  if (!data) return null

  const filteredIncidents = useMemo(() => {
    if (severityFilter === 'all') return data.incidents
    return data.incidents.filter(i => i.severity === severityFilter)
  }, [data.incidents, severityFilter])

  const paginatedIncidents = filteredIncidents.slice(incidentPage * INCIDENTS_PER_PAGE, (incidentPage + 1) * INCIDENTS_PER_PAGE)
  const totalIncidentPages = Math.ceil(filteredIncidents.length / INCIDENTS_PER_PAGE)

  const gridStroke = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
  const tickFill = isDark ? '#a0a0c0' : '#6b7194'
  const tooltipStyle = {
    borderRadius: 16, border: 'none',
    background: isDark ? 'rgba(15, 11, 46, 0.9)' : 'rgba(255, 255, 255, 0.85)',
    backdropFilter: 'blur(20px)',
    boxShadow: isDark ? '0 8px 32px rgba(0,0,0,0.3)' : '0 8px 32px rgba(80,60,160,0.12)',
    fontSize: 13, color: isDark ? '#f1f0f7' : '#1e1b3a',
  }

  const formatTimestamp = (ts) => {
    const d = new Date(ts)
    const now = new Date(2026, 4, 16, 12, 0)
    const diff = now - d
    const mins = Math.floor(diff / 60000)
    const hours = Math.floor(mins / 60)
    const days = Math.floor(hours / 24)
    if (mins < 60) return `${mins}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  }

  const kpiCards = [
    { label: 'Avg Wait Time', value: data.kpis.avgWait, change: data.kpis.avgWaitChange, icon: Clock, gradient: 'from-accent to-blue-500' },
    { label: 'Total Vehicles', value: data.kpis.totalVehicles, change: data.kpis.vehicleChange, icon: Car, gradient: 'from-success to-emerald-500' },
    { label: 'Signal Efficiency', value: data.kpis.efficiency, change: data.kpis.efficiencyChange, icon: Zap, gradient: 'from-warning to-orange-500' },
    { label: 'System Uptime', value: data.kpis.uptime, change: data.kpis.uptimeChange, icon: Activity, gradient: 'from-pink-500 to-rose-500' },
    { label: 'Total Incidents', value: String(data.kpis.totalFailures), change: data.kpis.failureChange, icon: AlertTriangle, gradient: 'from-danger to-red-600', subtitle: data.kpis.failureChange < 0 ? 'Improving' : 'Needs attention' },
    { label: 'Cameras Offline', value: String(data.kpis.cameraOffline), change: 0, icon: CameraOff, gradient: 'from-slate-500 to-gray-600', subtitle: `of ${isAll ? junctions.reduce((s, j) => s + j.cameras.length, 0) : currentJunction?.cameras.length || 0} total` },
  ]

  return (
    <div>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text">Reports</h1>
          <p className="text-muted mt-1">Traffic analytics, performance & incident tracking</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <button
              onClick={() => setShowJunctionPicker(!showJunctionPicker)}
              className="flex items-center gap-2 px-4 py-2.5 glass-strong rounded-2xl text-sm font-medium text-text cursor-pointer hover:shadow-card min-w-[200px] justify-between"
            >
              <div className="flex items-center gap-2 truncate">
                <GitBranch className="w-4 h-4 text-accent shrink-0" />
                <span className="truncate">{isAll ? 'All Junctions' : currentJunction?.name}</span>
              </div>
              <ChevronDown className={`w-4 h-4 text-muted shrink-0 transition-transform ${showJunctionPicker ? 'rotate-180' : ''}`} />
            </button>
            {showJunctionPicker && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowJunctionPicker(false)} />
                <div className="absolute right-0 top-full mt-2 w-72 glass-strong rounded-2xl shadow-card-hover p-2 z-50 max-h-80 overflow-y-auto">
                  <button
                    onClick={() => { setSelectedJunctionId('all'); setShowJunctionPicker(false); setIncidentPage(0) }}
                    className={`w-full text-left px-4 py-2.5 rounded-xl text-sm cursor-pointer transition-all flex items-center gap-2.5 ${
                      isAll ? 'bg-accent/15 text-accent font-semibold' : 'text-text hover:bg-white/5'
                    }`}
                  >
                    <CircleDot className="w-4 h-4 shrink-0" />
                    All Junctions (Aggregate)
                  </button>
                  <div className="h-px bg-border my-1.5" />
                  {junctions.map(j => (
                    <button
                      key={j.id}
                      onClick={() => { setSelectedJunctionId(String(j.id)); setShowJunctionPicker(false); setIncidentPage(0) }}
                      className={`w-full text-left px-4 py-2.5 rounded-xl text-sm cursor-pointer transition-all flex items-center gap-2.5 ${
                        selectedJunctionId === String(j.id) ? 'bg-accent/15 text-accent font-semibold' : 'text-text hover:bg-white/5'
                      }`}
                    >
                      <GitBranch className="w-3.5 h-3.5 shrink-0" />
                      <div className="min-w-0">
                        <span className="block truncate">{j.name}</span>
                        <span className="text-xs text-muted">{j.district} · {j.cameras.length} cameras</span>
                      </div>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
          <div className="flex glass rounded-2xl p-1">
            {['today', 'week', 'month'].map(r => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-4 py-2 rounded-xl text-sm font-medium capitalize cursor-pointer ${
                  range === r ? 'bg-gradient-to-r from-accent to-pink-500 text-white shadow-lg shadow-accent/20' : 'text-muted hover:text-text'
                }`}
              >{r}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        {kpiCards.map(kpi => <KpiCard key={kpi.label} {...kpi} />)}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <ChartCard
          title="Vehicle Flow"
          subtitle={isAll ? 'Aggregate hourly count across all junctions' : `Hourly count at ${currentJunction?.name}`}
        >
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={data.hourly}>
              <defs>
                <linearGradient id="purpleGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_ACCENT} stopOpacity={isDark ? 0.3 : 0.2} />
                  <stop offset="95%" stopColor={CHART_ACCENT} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} interval={3} />
              <YAxis tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="vehicles" stroke={CHART_ACCENT} strokeWidth={2} fill="url(#purpleGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {isAll ? (
          <ChartCard title="Junction Comparison" subtitle="Vehicles and efficiency per junction">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={aggregateData.junctionCompare} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} width={100} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="vehicles" fill={CHART_ACCENT} radius={[0, 4, 4, 0]} name="Vehicles" />
                <Bar dataKey="failures" fill={CHART_DANGER} radius={[0, 4, 4, 0]} name="Incidents" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        ) : (
          <ChartCard title="Corridor Comparison" subtitle="Weekly vehicle distribution by direction">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.weekly} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                {data.directionNames.map((dir, i) => (
                  <Bar key={dir} dataKey={dir} fill={DIR_COLORS[i % DIR_COLORS.length]} radius={[4, 4, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <ChartCard title="Incident Timeline" subtitle="Daily incidents over the last 30 days" className="xl:col-span-2">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.incidentTimeline} barGap={1}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} interval={4} />
              <YAxis tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="critical" stackId="a" fill={CHART_DANGER} radius={[0, 0, 0, 0]} name="Critical" />
              <Bar dataKey="warning" stackId="a" fill={CHART_WARNING} radius={[0, 0, 0, 0]} name="Warning" />
              <Bar dataKey="info" stackId="a" fill={CHART_ACCENT} radius={[4, 4, 0, 0]} name="Info" />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex items-center justify-center gap-5 mt-3">
            <span className="flex items-center gap-1.5 text-xs text-muted"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: CHART_DANGER }} />Critical</span>
            <span className="flex items-center gap-1.5 text-xs text-muted"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: CHART_WARNING }} />Warning</span>
            <span className="flex items-center gap-1.5 text-xs text-muted"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: CHART_ACCENT }} />Info</span>
          </div>
        </ChartCard>

        <ChartCard title="Signal Distribution" subtitle="Current light phase breakdown">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={isAll ? [
                  { name: 'Green', value: 45, color: CHART_GREEN },
                  { name: 'Yellow', value: 15, color: CHART_WARNING },
                  { name: 'Red', value: 40, color: CHART_DANGER },
                ] : data.pieData}
                cx="50%" cy="50%"
                innerRadius={55} outerRadius={85}
                paddingAngle={4} dataKey="value" strokeWidth={0}
              >
                {(isAll ? [
                  { name: 'Green', color: CHART_GREEN },
                  { name: 'Yellow', color: CHART_WARNING },
                  { name: 'Red', color: CHART_DANGER },
                ] : data.pieData).map(entry => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex items-center justify-center gap-5 mt-1">
            {[
              { name: 'Green', color: CHART_GREEN },
              { name: 'Yellow', color: CHART_WARNING },
              { name: 'Red', color: CHART_DANGER },
            ].map(entry => (
              <div key={entry.name} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-xs text-muted">{entry.name}</span>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <div className="xl:col-span-2">
          <ChartCard title="Efficiency Trend" subtitle="Monthly optimization score">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={isAll ? aggregateData.monthly : data.monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} />
                <YAxis domain={[60, 100]} tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="score" stroke={CHART_ACCENT} strokeWidth={2.5}
                  dot={{ fill: CHART_ACCENT, r: 4, stroke: 'rgba(124,92,252,0.3)', strokeWidth: 4 }}
                  activeDot={{ r: 6, fill: CHART_ACCENT, stroke: 'rgba(124,92,252,0.3)', strokeWidth: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <ChartCard title="Avg Wait Time" subtitle="Hourly wait distribution">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data.hourly}>
              <defs>
                <linearGradient id="waitGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_WARNING} stopOpacity={isDark ? 0.3 : 0.2} />
                  <stop offset="95%" stopColor={CHART_WARNING} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} interval={5} />
              <YAxis tick={{ fontSize: 11, fill: tickFill }} tickLine={false} axisLine={false} unit="s" />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="avgWait" stroke={CHART_WARNING} strokeWidth={2} fill="url(#waitGrad)" name="Wait (sec)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="glass rounded-[var(--radius-card)] shadow-card p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-5">
          <div>
            <h3 className="text-lg font-bold text-text">Incident Log</h3>
            <p className="text-sm text-muted mt-0.5">
              {filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''}
              {!isAll ? ` at ${currentJunction?.name}` : ' across all junctions'}
              {severityFilter !== 'all' ? ` · ${severityFilter}` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-muted" />
            {['all', 'critical', 'warning', 'info'].map(sev => (
              <button
                key={sev}
                onClick={() => { setSeverityFilter(sev); setIncidentPage(0) }}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize cursor-pointer transition-all border ${
                  severityFilter === sev
                    ? sev === 'all'
                      ? 'bg-accent/15 text-accent border-accent/20'
                      : `${SEVERITY_STYLES[sev].bg} ${SEVERITY_STYLES[sev].text} ${SEVERITY_STYLES[sev].border}`
                    : 'glass-subtle text-muted hover:text-text border-transparent'
                }`}
              >{sev}</button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          {paginatedIncidents.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle2 className="w-10 h-10 text-success/30 mx-auto mb-3" />
              <p className="text-muted">No incidents to show</p>
            </div>
          ) : paginatedIncidents.map(inc => {
            const sty = SEVERITY_STYLES[inc.severity]
            const IconComp = INCIDENT_ICONS[inc.icon] || AlertTriangle
            return (
              <div key={inc.id} className={`flex items-center gap-4 p-4 rounded-2xl glass-subtle border ${sty.border} transition-all hover:shadow-card`}>
                <div className={`w-9 h-9 rounded-xl ${sty.bg} ${sty.text} flex items-center justify-center shrink-0`}>
                  <IconComp className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-text">{inc.type}</span>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${sty.bg} ${sty.text} ${sty.border}`}>
                      {inc.severity}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted">
                    {isAll && <span className="flex items-center gap-1"><GitBranch className="w-3 h-3" />{inc.junction}</span>}
                    <span>{formatTimestamp(inc.timestamp)}</span>
                    <span className="font-mono">{inc.id}</span>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  {inc.resolved ? (
                    <span className="flex items-center gap-1 text-xs font-semibold text-success">
                      <CheckCircle2 className="w-3.5 h-3.5" />Resolved
                      {inc.duration && <span className="text-muted ml-1">({inc.duration})</span>}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs font-semibold text-danger">
                      <XCircle className="w-3.5 h-3.5" />Open
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {totalIncidentPages > 1 && (
          <div className="flex items-center justify-between mt-5 pt-4 border-t border-border">
            <p className="text-xs text-muted">
              Page {incidentPage + 1} of {totalIncidentPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setIncidentPage(p => Math.max(0, p - 1))}
                disabled={incidentPage === 0}
                className="px-3 py-1.5 glass rounded-xl text-xs font-medium cursor-pointer disabled:opacity-30 text-text"
              >Previous</button>
              <button
                onClick={() => setIncidentPage(p => Math.min(totalIncidentPages - 1, p + 1))}
                disabled={incidentPage >= totalIncidentPages - 1}
                className="px-3 py-1.5 glass rounded-xl text-xs font-medium cursor-pointer disabled:opacity-30 text-text"
              >Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
