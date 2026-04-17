export default function LoadingSpinner({ size = 'md', label = null }) {
  const sizes = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-10 h-10 border-[3px]',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`${sizes[size]} rounded-full border-[#353534] border-t-[#ff5540] animate-spin`}
      />
      {label && (
        <p className="text-[#ebbbb4] text-xs uppercase tracking-widest">{label}</p>
      )}
    </div>
  )
}
