import { useState, useEffect } from 'react'
import { useTelegram } from './hooks/useTelegram.js'
import { setUserId } from './api/client.js'
import BottomNav from './components/BottomNav.jsx'
import AddRace from './pages/AddRace.jsx'
import MyStats from './pages/MyStats.jsx'
import Leaderboard from './pages/Leaderboard.jsx'

export default function App() {
  const [activeTab, setActiveTab] = useState('add')
  const { userId, userName, isDevMode } = useTelegram()

  // Sync userId to API client whenever it changes
  useEffect(() => {
    setUserId(userId)
  }, [userId])

  return (
    <div
      className="flex flex-col"
      style={{
        height: '100dvh',
        backgroundColor: '#0A0A0A',
        // Account for Telegram WebApp header/bottom bar
        paddingTop: 'env(safe-area-inset-top, 0px)',
      }}
    >
      {/* Dev mode banner */}
      {isDevMode && (
        <div className="bg-[#1a1000] border-b border-[#FF6B0044] px-4 py-2 flex items-center gap-2 shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span className="text-[#FF6B00] text-xs">
            Режим разработки — Telegram не обнаружен
          </span>
        </div>
      )}

      {/* Page content */}
      <div className="flex-1 overflow-hidden" style={{ paddingBottom: '64px' }}>
        {activeTab === 'add' && (
          <div className="h-full overflow-hidden flex flex-col tab-content">
            <AddRace userId={userId} />
          </div>
        )}
        {activeTab === 'stats' && (
          <div className="h-full overflow-hidden flex flex-col tab-content">
            <MyStats userId={userId} />
          </div>
        )}
        {activeTab === 'leaderboard' && (
          <div className="h-full overflow-hidden flex flex-col tab-content">
            <Leaderboard userId={userId} />
          </div>
        )}
      </div>

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  )
}
