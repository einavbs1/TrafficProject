import { useTheme } from '../ThemeContext'
import { Sun, Moon } from 'lucide-react'

export default function ThemeToggle({ className = '' }) {
  const { isDark, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className={`relative w-14 h-7 rounded-full cursor-pointer transition-all duration-300 ${
        isDark
          ? 'bg-white/10 hover:bg-white/15'
          : 'bg-black/8 hover:bg-black/12'
      } ${className}`}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <span
        className={`absolute top-0.5 w-6 h-6 rounded-full flex items-center justify-center transition-all duration-300 shadow-md ${
          isDark
            ? 'left-0.5 bg-gradient-to-br from-indigo-500 to-purple-600'
            : 'left-[calc(100%-1.625rem)] bg-gradient-to-br from-amber-400 to-orange-500'
        }`}
      >
        {isDark
          ? <Moon className="w-3.5 h-3.5 text-white" />
          : <Sun className="w-3.5 h-3.5 text-white" />
        }
      </span>
    </button>
  )
}
