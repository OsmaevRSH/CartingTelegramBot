export default function BottomNav({ activeTab, onTabChange }) {
  const tabs = [
    {
      id: 'add',
      label: 'Добавить',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="16" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
      ),
    },
    {
      id: 'stats',
      label: 'Мои заезды',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      ),
    },
    {
      id: 'leaderboard',
      label: 'Рейтинг',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 21H16M12 21V13" />
          <path d="M20 7V5H4V7C4 10.3 6.7 13 10 13H14C17.3 13 20 10.3 20 7Z" />
          <path d="M4 5C4 5 2 5 2 7C2 8.1 2.9 9 4 9" />
          <path d="M20 5C20 5 22 5 22 7C22 8.1 21.1 9 20 9" />
        </svg>
      ),
    },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-[#0f0f0f] border-t border-[#1e1e1e] safe-bottom z-50">
      <div className="flex">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-colors duration-150 ${
                isActive
                  ? 'text-[#00FF7F]'
                  : 'text-[#666666]'
              }`}
            >
              {tab.icon(isActive)}
              <span className="text-[10px] font-medium tracking-wide">
                {tab.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
