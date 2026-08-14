import { useTheme } from '../ThemeContext'

export default function BackgroundDecor() {
  const { isDark } = useTheme()

  const strokeMain = isDark ? 'rgba(255,255,255,0.5)' : 'rgba(124,92,252,0.55)'
  const dotClass = isDark ? 'text-white' : 'text-accent'
  const ringBorder = isDark ? 'border-white/10' : 'border-accent/25'
  const ringBorder2 = isDark ? 'border-white/[0.07]' : 'border-pink-500/20'

  const dotOpacity1 = isDark ? 'opacity-[0.12]' : 'opacity-[0.35]'
  const dotOpacity2 = isDark ? 'opacity-[0.1]' : 'opacity-[0.3]'
  const svgTrafficLight = isDark ? 'opacity-[0.08]' : 'opacity-[0.25]'
  const svgJunction = isDark ? 'opacity-[0.06]' : 'opacity-[0.2]'
  const svgCrossroad = isDark ? 'opacity-[0.06]' : 'opacity-[0.18]'

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      <div className="orb orb-1 -top-40 -right-40 opacity-60" />
      <div className="orb orb-2 top-1/3 -left-32 opacity-50" />
      <div className="orb orb-3 bottom-20 right-1/4 opacity-40" />
      <div className="orb orb-4 -bottom-32 left-1/3 opacity-50" />

      <div className={`absolute top-[12%] right-[8%] w-28 h-28 rounded-full bg-gradient-to-br from-success/60 to-emerald-400/30 ${isDark ? 'blur-sm' : 'blur-md'} animate-[float-slow_18s_ease-in-out_infinite]`} />
      <div className={`absolute top-[55%] right-[5%] w-20 h-20 rounded-full bg-gradient-to-br from-warning/50 to-amber-400/20 ${isDark ? 'blur-sm' : 'blur-md'} animate-[float-medium_14s_ease-in-out_infinite]`} />
      <div className={`absolute bottom-[15%] left-[7%] w-24 h-24 rounded-full bg-gradient-to-br from-danger/50 to-rose-400/25 ${isDark ? 'blur-sm' : 'blur-md'} animate-[float-fast_16s_ease-in-out_infinite]`} />

      <div className={`absolute top-[8%] left-[15%] w-16 h-16 rounded-full border-2 ${ringBorder} animate-[float-medium_20s_ease-in-out_infinite]`} />
      <div className={`absolute top-[40%] right-[12%] w-32 h-32 rounded-full border-2 ${ringBorder2} animate-[float-slow_25s_ease-in-out_infinite_reverse]`} />
      <div className={`absolute bottom-[25%] right-[30%] w-20 h-20 rounded-full ${isDark ? 'border' : 'border-2'} border-accent/15 animate-[float-fast_22s_ease-in-out_infinite]`} />
      <div className={`absolute bottom-[40%] left-[25%] w-40 h-40 rounded-full ${isDark ? 'border' : 'border-2'} ${isDark ? 'border-pink-500/10' : 'border-pink-500/20'} animate-[float-slow_28s_ease-in-out_infinite]`} />

      <svg className={`absolute top-[6%] right-[22%] ${dotOpacity1} animate-[float-slow_30s_ease-in-out_infinite]`} width="48" height="48" viewBox="0 0 48 48">
        {[4,16,28,40].map(y => [4,16,28,40].map(x => (
          <circle key={`${x}-${y}`} cx={x} cy={y} r="2" fill="currentColor" className={dotClass} />
        )))}
      </svg>

      <svg className={`absolute bottom-[12%] left-[10%] ${dotOpacity2} animate-[float-medium_24s_ease-in-out_infinite_reverse]`} width="60" height="60" viewBox="0 0 60 60">
        {[6,18,30,42,54].map(y => [6,18,30,42,54].map(x => (
          <circle key={`${x}-${y}`} cx={x} cy={y} r="2.5" fill="currentColor" className={dotClass} />
        )))}
      </svg>

      <svg className={`absolute top-[30%] left-[5%] ${svgTrafficLight} animate-[float-slow_35s_ease-in-out_infinite]`} width="80" height="160" viewBox="0 0 80 160">
        <rect x="10" y="0" width="60" height="155" rx="30" fill="none" stroke={strokeMain} strokeWidth="2" />
        <circle cx="40" cy="35" r="16" fill="none" stroke="#34d399" strokeWidth="2.5" />
        <circle cx="40" cy="80" r="16" fill="none" stroke="#fbbf24" strokeWidth="2.5" />
        <circle cx="40" cy="125" r="16" fill="none" stroke="#f87171" strokeWidth="2.5" />
      </svg>

      <svg className={`absolute bottom-[30%] right-[15%] ${svgJunction} animate-[float-medium_28s_ease-in-out_infinite_reverse]`} width="120" height="120" viewBox="0 0 120 120">
        <line x1="60" y1="0" x2="60" y2="120" stroke={strokeMain} strokeWidth="1.5" strokeDasharray="6 4" />
        <line x1="0" y1="60" x2="120" y2="60" stroke={strokeMain} strokeWidth="1.5" strokeDasharray="6 4" />
        <circle cx="60" cy="60" r="20" fill="none" stroke="rgba(124,92,252,0.5)" strokeWidth="2" />
        <circle cx="60" cy="60" r="40" fill="none" stroke="rgba(124,92,252,0.3)" strokeWidth="1.5" />
      </svg>

      <svg className={`absolute top-[65%] left-[35%] ${svgCrossroad} animate-[float-fast_20s_ease-in-out_infinite]`} width="100" height="100" viewBox="0 0 100 100">
        <line x1="50" y1="0" x2="50" y2="100" stroke={strokeMain} strokeWidth="1.5" strokeDasharray="4 6" />
        <line x1="0" y1="50" x2="100" y2="50" stroke={strokeMain} strokeWidth="1.5" strokeDasharray="4 6" />
        <line x1="15" y1="15" x2="85" y2="85" stroke="rgba(236,72,153,0.4)" strokeWidth="1.5" strokeDasharray="4 6" />
        <line x1="85" y1="15" x2="15" y2="85" stroke="rgba(236,72,153,0.4)" strokeWidth="1.5" strokeDasharray="4 6" />
      </svg>

      <div className={`absolute top-[18%] right-[35%] w-5 h-5 rounded-full bg-gradient-to-br from-success to-emerald-300 ${isDark ? 'opacity-40' : 'opacity-70'} animate-[float-fast_12s_ease-in-out_infinite]`} />
      <div className={`absolute top-[70%] right-[40%] w-3 h-3 rounded-full bg-gradient-to-br from-warning to-amber-300 ${isDark ? 'opacity-35' : 'opacity-65'} animate-[float-medium_10s_ease-in-out_infinite_reverse]`} />
      <div className={`absolute top-[45%] left-[40%] w-4 h-4 rounded-full bg-gradient-to-br from-danger to-rose-300 ${isDark ? 'opacity-30' : 'opacity-60'} animate-[float-slow_14s_ease-in-out_infinite]`} />
      <div className={`absolute top-[25%] left-[50%] w-3 h-3 rounded-full bg-gradient-to-br from-accent to-violet-300 ${isDark ? 'opacity-35' : 'opacity-65'} animate-[float-fast_11s_ease-in-out_infinite_reverse]`} />
      <div className={`absolute bottom-[10%] right-[20%] w-4 h-4 rounded-full bg-gradient-to-br from-cyan-400 to-sky-300 ${isDark ? 'opacity-30' : 'opacity-60'} animate-[float-medium_13s_ease-in-out_infinite]`} />
    </div>
  )
}
