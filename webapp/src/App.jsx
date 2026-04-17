import { useState, useEffect } from 'react'
import { useTelegram } from './hooks/useTelegram.js'
import { setUserId, registerUser } from './api/client.js'
import BottomNav from './components/BottomNav.jsx'
import MyStats from './pages/MyStats.jsx'
import Leaderboard from './pages/Leaderboard.jsx'

export default function App() {
  const [activeTab, setActiveTab] = useState('stats')
  const { userId, userName, userUsername, userPhotoUrl, isDevMode } = useTelegram()

  useEffect(() => {
    setUserId(userId)
    if (userId && userName) {
      registerUser(userId, userName, userUsername, userPhotoUrl).catch(() => {})
    }
  }, [userId, userName, userUsername, userPhotoUrl])

  return (
    <div
      className="flex flex-col"
      style={{
        height: '100dvh',
        backgroundColor: '#131313',
        paddingTop: 'env(safe-area-inset-top, 0px)',
      }}
    >
      {/* Dev mode banner */}
      {isDevMode && (
        <div className="bg-[#0e0e0e] px-4 py-2 flex items-center gap-2 shrink-0" style={{ borderBottom: '2px solid #ff5540' }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ffb4a8" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span className="text-[#ffb4a8] text-[9px] uppercase tracking-widest font-bold">
            Dev mode — Telegram не обнаружен
          </span>
        </div>
      )}

      {/* Page content */}
      <div className="flex-1 overflow-hidden" style={{ paddingBottom: '64px' }}>
        {activeTab === 'stats' && (
          <div className="h-full overflow-hidden flex flex-col tab-content">
            <MyStats userId={userId} userName={userName} />
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
