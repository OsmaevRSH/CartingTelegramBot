import { useState, useEffect, useCallback } from 'react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { fetchLeaderboard, fetchLeaderboardToday } from '../api/client.js'

const SEG_ALL = 'all'
const SEG_TODAY = 'today'

function todayDDMMYYYY() {
  const d = new Date()
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  return `${dd}.${mm}.${yyyy}`
}

function RankBadge({ rank }) {
  if (rank === 1) return <span className="text-2xl leading-none">🥇</span>
  if (rank === 2) return <span className="text-2xl leading-none">🥈</span>
  if (rank === 3) return <span className="text-2xl leading-none">🥉</span>
  return (
    <div className="w-7 h-7 rounded-full bg-[#1e1e1e] flex items-center justify-center">
      <span className="text-[#888] text-xs font-bold lap-time">{rank}</span>
    </div>
  )
}

export default function Leaderboard({ userId }) {
  const [segment, setSegment] = useState(SEG_ALL)
  const [allData, setAllData] = useState([])
  const [todayData, setTodayData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchLeaderboard()
      setAllData(data || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadToday = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchLeaderboardToday(todayDDMMYYYY())
      setTodayData(data || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (segment === SEG_ALL) {
      loadAll()
    } else {
      loadToday()
    }
  }, [segment, loadAll, loadToday])

  function handleRefresh() {
    if (segment === SEG_ALL) loadAll()
    else loadToday()
  }

  const currentData = segment === SEG_ALL ? allData : todayData

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-bold text-white">Рейтинг</h1>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2 rounded-lg bg-[#1e1e1e] text-[#888] disabled:opacity-50"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={loading ? 'animate-spin' : ''}
            >
              <path d="M23 4v6h-6"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
          </button>
        </div>

        {/* Segment control */}
        <div className="flex bg-[#141414] border border-[#222] rounded-xl p-1 gap-1">
          {[
            { id: SEG_ALL, label: 'Все времена' },
            { id: SEG_TODAY, label: 'Сегодня' },
          ].map((seg) => (
            <button
              key={seg.id}
              onClick={() => setSegment(seg.id)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                segment === seg.id
                  ? 'bg-[#00FF7F] text-black'
                  : 'text-[#888] hover:text-white'
              }`}
            >
              {seg.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 tab-content">
        {loading && (
          <div className="flex justify-center py-16">
            <LoadingSpinner size="lg" label="Загрузка рейтинга..." />
          </div>
        )}

        {!loading && error && (
          <div className="bg-[#1a0000] border border-[#FF444433] rounded-xl p-4 flex items-start gap-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
              <p className="text-[#FF4444] text-sm">{error}</p>
              <button onClick={handleRefresh} className="text-xs text-[#888] underline mt-1">
                Повторить
              </button>
            </div>
          </div>
        )}

        {!loading && !error && currentData.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="text-5xl">🏆</div>
            <p className="text-white font-medium">Нет данных</p>
            <p className="text-[#888888] text-sm text-center">
              {segment === SEG_TODAY
                ? 'Сегодня заездов ещё не было'
                : 'Добавьте свой первый заезд'}
            </p>
          </div>
        )}

        {!loading && !error && currentData.length > 0 && (
          <div className="space-y-2">
            {/* Top 3 podium (if enough entries) */}
            {currentData.length >= 3 && (
              <PodiumRow entries={currentData.slice(0, 3)} userId={userId} />
            )}

            {/* Full list */}
            <div className="space-y-1.5 mt-1">
              {currentData.map((entry, idx) => {
                const rank = idx + 1
                const isCurrentUser = userId !== null && userId !== undefined &&
                  String(entry.user_id) === String(userId)
                const displayName = getDisplayName(entry)

                return (
                  <div
                    key={`${entry.user_id}-${idx}`}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all ${
                      isCurrentUser
                        ? 'border-[#00FF7F44] bg-[#001a0d] border-l-[3px] border-l-[#00FF7F]'
                        : 'border-[#222] bg-[#141414]'
                    }`}
                  >
                    {/* Rank */}
                    <div className="shrink-0 w-8 flex justify-center">
                      <RankBadge rank={rank} />
                    </div>

                    {/* Name + details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-sm font-medium truncate ${
                          isCurrentUser ? 'text-[#00FF7F]' : 'text-white'
                        }`}>
                          {displayName}
                        </span>
                        {isCurrentUser && (
                          <span className="text-[10px] text-[#00FF7F66] font-medium">Вы</span>
                        )}
                      </div>
                      <div className="text-[#666] text-xs mt-0.5">
                        Карт #{entry.num}
                        {entry.date && <span> · {entry.date}</span>}
                      </div>
                    </div>

                    {/* Best lap */}
                    <div className="shrink-0 text-right">
                      <div className="text-[#00FF7F] lap-time text-sm font-medium">
                        {entry.best_lap || '—'}
                      </div>
                      <div className="text-[#555] text-xs">лучший</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function getDisplayName(entry) {
  if (entry.name && entry.name.trim() && !(entry.display_name || '').startsWith('Карт #')) {
    return entry.name.trim()
  }
  if (entry.display_name && !entry.display_name.startsWith('Карт #')) {
    return entry.display_name
  }
  return `К#${entry.num}`
}

function PodiumRow({ entries, userId }) {
  // Visual podium: 2nd left, 1st center, 3rd right
  const order = [entries[1], entries[0], entries[2]]
  const heights = ['h-20', 'h-24', 'h-16']
  const ranks = [2, 1, 3]

  return (
    <div className="flex items-end justify-center gap-2 py-4 mb-2">
      {order.map((entry, i) => {
        if (!entry) return null
        const rank = ranks[i]
        const height = heights[i]
        const isCurrentUser = userId !== null && userId !== undefined &&
          String(entry.user_id) === String(userId)
        const displayName = getDisplayName(entry)

        return (
          <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
            {/* Name */}
            <div className={`text-xs font-medium text-center truncate max-w-[80px] ${
              isCurrentUser ? 'text-[#00FF7F]' : 'text-[#ccc]'
            }`}>
              {displayName}
            </div>
            {/* Lap */}
            <div className="text-[#00FF7F] lap-time text-xs">
              {entry.best_lap || '—'}
            </div>
            {/* Podium block */}
            <div
              className={`${height} w-full rounded-t-lg flex items-end justify-center pb-2 ${
                rank === 1 ? 'bg-gradient-to-t from-[#1a1200] to-[#2d2000] border border-[#FFD700]/30' :
                rank === 2 ? 'bg-gradient-to-t from-[#0f1a1f] to-[#1a2d35] border border-[#C0C0C0]/20' :
                'bg-gradient-to-t from-[#1a0d00] to-[#2d1800] border border-[#CD7F32]/20'
              } rounded-t-lg`}
            >
              <span className="text-2xl">
                {rank === 1 ? '🥇' : rank === 2 ? '🥈' : '🥉'}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
