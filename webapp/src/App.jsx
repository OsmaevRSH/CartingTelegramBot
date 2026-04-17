import { useState, useEffect } from 'react'
import { useTelegram } from './hooks/useTelegram.js'
import { setUserId, registerUser } from './api/client.js'
import BottomNav from './components/BottomNav.jsx'
import MyStats from './pages/MyStats.jsx'
import Leaderboard from './pages/Leaderboard.jsx'

export default function App() {
  const [activeTab, setActiveTab] = useState('stats')
  const [statsReset, setStatsReset] = useState(0)
  const [lbReset, setLbReset] = useState(0)
  const { userId, userName, userUsername, userPhotoUrl, isDevMode } = useTelegram()

  useEffect(() => {
    setUserId(userId)
    if (userId && userName) {
      registerUser(userId, userName, userUsername, userPhotoUrl).catch(() => {})
    }
  }, [userId, userName, userUsername, userPhotoUrl])

  function handleTabPress(tabId) {
    if (tabId === activeTab) {
      // Tap on active tab — signal the page to pop to root or scroll to top
      if (tabId === 'stats') setStatsReset(n => n + 1)
      else setLbReset(n => n + 1)
    } else {
      setActiveTab(tabId)
    }
  }

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

      {/* Page content — both tabs stay mounted to preserve scroll position */}
      <div className="flex-1 overflow-hidden" style={{ paddingBottom: '64px' }}>
        <div className={`h-full overflow-hidden flex flex-col ${activeTab === 'stats' ? '' : 'hidden'}`}>
          <MyStats userId={userId} userName={userName} resetSignal={statsReset} />
        </div>
        <div className={`h-full overflow-hidden flex flex-col ${activeTab === 'leaderboard' ? '' : 'hidden'}`}>
          <Leaderboard userId={userId} resetSignal={lbReset} />
        </div>
      </div>

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabPress} />
    </div>
  )
}
