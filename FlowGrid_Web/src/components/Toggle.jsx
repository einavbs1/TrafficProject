export default function Toggle({ value, onChange }) {
  return (
    <button onClick={onChange} className={`relative w-11 h-6 rounded-full cursor-pointer transition-colors ${
      value ? 'bg-gradient-to-r from-accent to-pink-500' : 'bg-accent/10'
    }`}>
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-lg transition-transform ${value ? 'translate-x-5' : ''}`} />
    </button>
  )
}
