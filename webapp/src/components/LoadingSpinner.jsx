export default function LoadingSpinner({ size = 'md', label = null }) {
  const sizes = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-12 h-12 border-[3px]',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`${sizes[size]} rounded-full border-[#222] border-t-[#00FF7F] animate-spin`}
      />
      {label && (
        <p className="text-[#888888] text-sm">{label}</p>
      )}
    </div>
  )
}
