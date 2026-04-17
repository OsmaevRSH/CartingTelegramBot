import { useState, useEffect, useCallback, useRef } from 'react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { fetchLeaderboard, fetchLeaderboardToday, fetchKartsToday } from '../api/client.js'

const SEG_ALL = 'all'
const SEG_TODAY = 'today'
const SEG_KARTS = 'karts'

function todayDDMMYYYY() {
  const d = new Date()
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  return `${dd}.${mm}.${yyyy}`
}

function Avatar({ name, photoUrl, size = 32 }) {
  const [imgError, setImgError] = useState(false)
  const initials = (name || '?').trim().split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const style = { width: size, height: size, minWidth: size, minHeight: size, overflow: 'hidden' }

  if (photoUrl && !imgError) {
    return <img src={photoUrl} alt={name} style={style} className="object-cover" onError={() => setImgError(true)} />
  }
  return (
    <div style={style} className="flex items-center justify-center text-[10px] font-bold bg-[#353534] text-[#ebbbb4]">
      {initials}
    </div>
  )
}

function getDisplayName(entry) {
  if (entry.telegram_name && entry.telegram_name.trim()) return entry.telegram_name.trim()
  if (entry.name && entry.name.trim() && !(entry.display_name || '').startsWith('Карт #')) return entry.name.trim()
  if (entry.display_name && !entry.display_name.startsWith('Карт #')) return entry.display_name
  return `К#${entry.num}`
}

export default function Leaderboard({ userId, resetSignal }) {
  const [segment, setSegment] = useState(SEG_ALL)
  const [allData, setAllData] = useState([])
  const [todayData, setTodayData] = useState([])
  const [kartsData, setKartsData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const scrollRef = useRef(null)

  useEffect(() => {
    if (!resetSignal) return
    scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }, [resetSignal])

  const loadAll = useCallback(async () => {
    setLoading(true); setError(null)
    try { setAllData((await fetchLeaderboard()) || []) }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, [])

  const loadToday = useCallback(async () => {
    setLoading(true); setError(null)
    try { setTodayData((await fetchLeaderboardToday(todayDDMMYYYY())) || []) }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, [])

  const loadKarts = useCallback(async () => {
    setLoading(true); setError(null)
    try { setKartsData((await fetchKartsToday(todayDDMMYYYY())) || []) }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (segment === SEG_ALL) loadAll()
    else if (segment === SEG_TODAY) loadToday()
    else loadKarts()
  }, [segment, loadAll, loadToday, loadKarts])

  function handleRefresh() {
    if (segment === SEG_ALL) loadAll()
    else if (segment === SEG_TODAY) loadToday()
    else loadKarts()
  }

  const currentData = segment === SEG_ALL ? allData : segment === SEG_TODAY ? todayData : kartsData

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-xl font-bold text-[#e5e2e1] tracking-tighter leading-none">РЕЙТИНГ</h1>
            {!loading && currentData.length > 0 && (
              <p className="text-[#ebbbb4] text-[9px] mt-1 uppercase tracking-widest">
                {currentData.length} пилотов
              </p>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2 bg-[#1c1b1b] text-[#ebbbb4] disabled:opacity-50 hover:bg-[#2a2a2a] transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter" className={loading ? 'animate-spin' : ''}>
              <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
          </button>
        </div>

        {/* Segment control */}
        <div className="flex bg-[#1c1b1b] p-0.5 gap-0">
          {[
            { id: SEG_ALL, label: 'Все времена' },
            { id: SEG_TODAY, label: 'Сегодня' },
            { id: SEG_KARTS, label: 'Карты' },
          ].map((seg) => (
            <button
              key={seg.id}
              onClick={() => setSegment(seg.id)}
              className={`flex-1 py-2 text-[9px] font-bold uppercase tracking-widest transition-all duration-150 ${
                segment === seg.id
                  ? 'bg-[#ff5540] text-white'
                  : 'text-[#ebbbb4] hover:text-[#e5e2e1]'
              }`}
            >
              {seg.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pb-4 tab-content">
        {loading && (
          <div className="flex justify-center py-16">
            <LoadingSpinner size="lg" label="Загрузка..." />
          </div>
        )}

        {!loading && error && (
          <div className="bg-[#0e0e0e] p-4 flex items-start gap-3" style={{ borderLeft: '3px solid #FF4444' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="square" className="shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
              <p className="text-[#FF4444] text-sm">{error}</p>
              <button onClick={handleRefresh} className="text-[9px] text-[#ebbbb4] uppercase tracking-widest mt-1">Повторить</button>
            </div>
          </div>
        )}

        {!loading && !error && currentData.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="text-[#ff5540] text-4xl font-black tracking-tighter">—</div>
            <p className="text-[#e5e2e1] font-bold text-sm uppercase tracking-tight">Нет данных</p>
            <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest text-center">
              {segment === SEG_KARTS ? 'Сегодня заездов ещё не было' :
               segment === SEG_TODAY ? 'Сегодня заездов ещё не было' :
               'Добавьте первый заезд'}
            </p>
          </div>
        )}

        {/* Leaderboard (all / today) */}
        {!loading && !error && currentData.length > 0 && segment !== SEG_KARTS && (
          <div>
            {currentData.length >= 3 && (
              <PodiumRow entries={currentData.slice(0, 3)} userId={userId} />
            )}
            <div className="space-y-1.5 mt-2">
              {currentData.map((entry, idx) => {
                const rank = idx + 1
                const isCurrentUser = userId !== null && userId !== undefined &&
                  String(entry.user_id) === String(userId)
                const displayName = getDisplayName(entry)
                const photoUrl = entry.photo_url || null

                return (
                  <div
                    key={`${entry.user_id}-${idx}`}
                    className={`flex items-center gap-3 px-3 py-2.5 transition-all ${
                      isCurrentUser
                        ? 'bg-[#0e0e0e]'
                        : 'bg-[#1c1b1b]'
                    }`}
                    style={isCurrentUser ? { borderLeft: '3px solid #ff5540' } : { borderLeft: '3px solid transparent' }}
                  >
                    <div className="shrink-0 w-7 flex justify-center">
                      <RankBadge rank={rank} isCurrentUser={isCurrentUser} />
                    </div>
                    <Avatar name={displayName} photoUrl={photoUrl} size={32} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-sm font-bold uppercase tracking-tight truncate ${isCurrentUser ? 'text-[#ffb4a8]' : 'text-[#e5e2e1]'}`}>
                          {displayName}
                        </span>
                        {isCurrentUser && (
                          <span className="text-[8px] bg-[#ff5540] text-white px-1.5 py-0.5 font-bold uppercase tracking-widest">ВЫ</span>
                        )}
                      </div>
                      <div className="text-[#454747] text-[9px] uppercase tracking-widest mt-0.5">
                        Карт #{entry.num}
                        {entry.date && <span> · {entry.date}</span>}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className={`lap-time text-sm font-bold ${isCurrentUser ? 'text-[#ffb4a8]' : 'text-[#ff5540]'}`}>
                        {entry.best_lap || '—'}
                      </div>
                      <div className="text-[#454747] text-[9px] uppercase tracking-widest">лучший</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Karts today */}
        {!loading && !error && currentData.length > 0 && segment === SEG_KARTS && (
          <div className="space-y-1.5">
            <p className="text-[#454747] text-[9px] mb-3 uppercase tracking-widest">Лучший круг каждого карта за сегодня</p>
            {currentData.map((kart, idx) => {
              const rank = idx + 1
              const isTop3 = rank <= 3
              return (
                <div
                  key={kart.num}
                  className={`flex items-center gap-3 px-3 py-3 transition-all ${
                    isTop3 ? 'bg-[#0e0e0e]' : 'bg-[#1c1b1b]'
                  }`}
                  style={isTop3 ? { borderLeft: '3px solid #ff5540' } : { borderLeft: '3px solid transparent' }}
                >
                  <div className="shrink-0 w-7 flex justify-center">
                    <RankBadge rank={rank} />
                  </div>

                  {/* Cart number badge */}
                  <div className={`shrink-0 w-14 h-10 flex items-center justify-center font-black text-base tracking-tighter ${
                    rank === 1 ? 'bg-[#ff5540] text-white' :
                    rank === 2 ? 'bg-[#2a2a2a] text-[#e5e2e1]' :
                    rank === 3 ? 'bg-[#201f1f] text-[#ebbbb4]' :
                    'bg-[#1c1b1b] text-[#454747]'
                  }`}>
                    #{kart.num}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="text-[#454747] text-[9px] uppercase tracking-widest">
                      {kart.races} {pluralRaces(kart.races)} сегодня
                    </div>
                  </div>

                  <div className="shrink-0 text-right">
                    <div className={`lap-time text-sm font-bold ${isTop3 ? 'text-[#ff5540]' : 'text-[#e5e2e1]'}`}>
                      {kart.best_lap || '—'}
                    </div>
                    <div className="text-[#454747] text-[9px] uppercase tracking-widest">лучший</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function RankBadge({ rank, isCurrentUser }) {
  if (rank === 1) return (
    <span className="text-sm font-black text-[#ff5540] lap-time">01</span>
  )
  if (rank === 2) return (
    <span className="text-sm font-black text-[#e5e2e1] lap-time">02</span>
  )
  if (rank === 3) return (
    <span className="text-sm font-black text-[#ebbbb4] lap-time">03</span>
  )
  return (
    <span className={`text-xs font-bold lap-time ${isCurrentUser ? 'text-[#ffb4a8]' : 'text-[#454747]'}`}>
      {String(rank).padStart(2, '0')}
    </span>
  )
}

function pluralRaces(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'заезд'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'заезда'
  return 'заездов'
}

function PodiumRow({ entries, userId }) {
  const order = [entries[1], entries[0], entries[2]]
  const heights = [80, 96, 64]
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
        const photoUrl = entry.photo_url || null

        return (
          <div key={i} className="flex flex-col items-center gap-1 flex-1">
            {/* Avatar */}
            <Avatar name={displayName} photoUrl={photoUrl} size={rank === 1 ? 44 : 36} />
            {/* Name */}
            <div className={`text-[9px] font-bold uppercase tracking-widest text-center truncate max-w-[80px] ${
              rank === 1 ? 'text-[#ffb4a8]' : isCurrentUser ? 'text-[#ff5540]' : 'text-[#ebbbb4]'
            }`}>
              {displayName}
            </div>
            {/* Lap */}
            <div className={`lap-time text-[9px] font-bold ${rank === 1 ? 'text-[#ff5540]' : 'text-[#454747]'}`}>
              {entry.best_lap || '—'}
            </div>
            {/* Podium block */}
            <div
              style={{ height }}
              className={`w-full flex items-start justify-center pt-2 relative overflow-hidden ${
                rank === 1
                  ? 'bg-[#0e0e0e]'
                  : 'bg-[#1c1b1b]'
              }`}
              {...(rank === 1 ? { style: { height, borderTop: '2px solid #ff5540' } } : { style: { height } })}
            >
              <span className={`text-2xl font-black tracking-tighter ${
                rank === 1 ? 'text-[#ff5540]' : 'text-[#353534]'
              }`}>
                {rank}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
