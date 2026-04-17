import { useState, useEffect, useCallback } from 'react'
import RaceCard from '../components/RaceCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import AddRace from './AddRace.jsx'
import { fetchStats, deleteStats, fetchUsers } from '../api/client.js'

export default function MyStats({ userId, userName }) {
  const [isAdding, setIsAdding] = useState(false)
  const [addTarget, setAddTarget] = useState(null)
  const [pickingUser, setPickingUser] = useState(false)
  const [users, setUsers] = useState([])
  const [selectedId, setSelectedId] = useState(userId)
  const [selectedName, setSelectedName] = useState('Я')

  const [races, setRaces] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchUsers()
      .then(data => setUsers(data || []))
      .catch(() => setUsers([]))
  }, [])

  useEffect(() => {
    setSelectedId(userId)
  }, [userId])

  const load = useCallback(async (uid) => {
    if (uid === null || uid === undefined) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchStats(uid)
      const sorted = (data || []).sort((a, b) => {
        const toSortable = (d) => d.substr(6, 4) + d.substr(3, 2) + d.substr(0, 2)
        return toSortable(b.date).localeCompare(toSortable(a.date))
      })
      setRaces(sorted)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(selectedId)
  }, [selectedId, load])

  function handleSelectPilot(uid, name) {
    if (String(uid) === String(selectedId)) return
    setSelectedId(uid)
    setSelectedName(name)
    setRaces([])
  }

  async function handleDelete(race) {
    try {
      await deleteStats(selectedId, race.date, race.race_number, race.num)
      setRaces(prev =>
        prev.filter(r =>
          !(r.date === race.date &&
            r.race_number === race.race_number &&
            String(r.num) === String(race.num))
        )
      )
    } catch (e) {
      alert(`Ошибка при удалении: ${e.message}`)
    }
  }

  const isMyself = String(selectedId) === String(userId)
  const headerName = isMyself ? 'МОИ ЗАЕЗДЫ' : `ЗАЕЗДЫ — ${selectedName.toUpperCase()}`
  const otherPilots = users.filter(u => String(u.user_id) !== String(userId))

  function handleAddDone() {
    setIsAdding(false)
    setAddTarget(null)
    load(selectedId)
  }

  if (isAdding) {
    return (
      <AddRace
        userId={userId}
        userName={userName}
        targetUserId={addTarget?.uid ?? userId}
        targetUserName={addTarget?.name ?? userName}
        onDone={handleAddDone}
      />
    )
  }

  if (pickingUser) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-4 pt-5 pb-4" style={{ borderBottom: '1px solid #201f1f' }}>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPickingUser(false)}
              className="p-2 bg-[#1c1b1b] text-[#ebbbb4]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
            <div>
              <h1 className="text-base font-bold text-[#e5e2e1] uppercase tracking-tight">Добавить другому</h1>
              <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest mt-0.5">Выберите гонщика</p>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
          {otherPilots.map(u => (
            <button
              key={u.user_id}
              onClick={() => {
                setAddTarget({ uid: u.user_id, name: u.display_name })
                setPickingUser(false)
                setIsAdding(true)
              }}
              className="w-full text-left px-4 py-3 bg-[#0e0e0e] transition-all hover:bg-[#1c1b1b]"
            >
              <div className="flex items-center gap-3">
                <Avatar name={u.display_name} photoUrl={u.photo_url} size={32} />
                <span className="text-[#e5e2e1] font-bold text-sm uppercase tracking-tight">{u.display_name}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-bold text-[#e5e2e1] tracking-tighter leading-none truncate">{headerName}</h1>
            {!loading && races.length > 0 && (
              <p className="text-[#ebbbb4] text-[9px] mt-1 uppercase tracking-widest">
                {races.length} {pluralRaces(races.length)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {/* Add for another person */}
            {otherPilots.length > 0 && (
              <button
                onClick={() => setPickingUser(true)}
                className="px-3 py-2 bg-[#1c1b1b] text-[#ebbbb4] text-[9px] font-bold uppercase tracking-widest flex items-center gap-1.5 transition-colors hover:bg-[#2a2a2a]"
                title="Добавить другому"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/>
                  <line x1="22" y1="11" x2="16" y2="11"/>
                </svg>
                Другому
              </button>
            )}
            {/* Add for self */}
            <button
              onClick={() => { setAddTarget(null); setIsAdding(true) }}
              className="px-3 py-2 bg-[#ff5540] text-white text-[9px] font-bold uppercase tracking-widest flex items-center gap-1.5 transition-colors hover:bg-[#e84b38]"
              title="Добавить себе"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Добавить
            </button>
            <button
              onClick={() => load(selectedId)}
              disabled={loading}
              className="p-2 bg-[#1c1b1b] text-[#ebbbb4] disabled:opacity-50 transition-colors hover:bg-[#2a2a2a]"
            >
              <svg
                width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter"
                className={loading ? 'animate-spin' : ''}
              >
                <path d="M23 4v6h-6"/>
                <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Pilot selector chips */}
        {otherPilots.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {[
              { user_id: userId, display_name: userName || 'Я', photo_url: users.find(u => String(u.user_id) === String(userId))?.photo_url, telegram_username: users.find(u => String(u.user_id) === String(userId))?.telegram_username, _isMe: true },
              ...otherPilots,
            ].map(u => {
              const isSelected = String(selectedId) === String(u.user_id)
              return (
                <div key={u.user_id} className="shrink-0 flex items-center gap-0.5">
                  <button
                    onClick={() => handleSelectPilot(u.user_id, u.display_name)}
                    className={`flex items-center gap-1.5 pl-1 pr-3 py-1 text-[9px] font-bold uppercase tracking-widest transition-all ${
                      isSelected
                        ? 'bg-[#ff5540] text-white'
                        : 'bg-[#1c1b1b] text-[#ebbbb4]'
                    }`}
                  >
                    <Avatar name={u.display_name} photoUrl={u.photo_url} size={20} square />
                    {u._isMe ? (userName || 'Я') : u.display_name}
                  </button>
                  {!u._isMe && u.telegram_username && (
                    <button
                      onClick={() => openTgProfile(u.telegram_username, u.user_id)}
                      className="p-1 text-[#353534] hover:text-[#ebbbb4] transition-colors"
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      </svg>
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 tab-content">
        {loading && (
          <div className="flex justify-center py-16">
            <LoadingSpinner size="lg" label="Загрузка заездов..." />
          </div>
        )}

        {!loading && error && (
          <div className="bg-[#0e0e0e] p-4 flex items-start gap-3" style={{ borderLeft: '3px solid #FF4444' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter" className="shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
              <p className="text-[#FF4444] text-sm">{error}</p>
              <button onClick={() => load(selectedId)} className="text-[9px] text-[#ebbbb4] uppercase tracking-widest mt-1">
                Повторить
              </button>
            </div>
          </div>
        )}

        {!loading && !error && selectedId === null && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="w-12 h-12 bg-[#1c1b1b] flex items-center justify-center text-[#ebbbb4]">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
                <rect x="3" y="11" width="18" height="11" rx="0"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
            <p className="text-[#ebbbb4] text-xs uppercase tracking-widest text-center">
              Откройте через Telegram-бота
            </p>
          </div>
        )}

        {!loading && !error && selectedId !== null && races.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="text-[#ff5540] text-4xl font-black tracking-tighter">0</div>
            <p className="text-[#e5e2e1] font-bold text-sm uppercase tracking-tight">Заездов пока нет</p>
            <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest text-center">
              {isMyself
                ? 'Нажмите Добавить'
                : `У ${selectedName} нет заездов`}
            </p>
          </div>
        )}

        {!loading && !error && races.length > 0 && (
          <div className="space-y-2">
            {races.map((race, idx) => (
              <RaceCard
                key={`${race.date}-${race.race_number}-${race.num}-${idx}`}
                race={race}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function openTgProfile(username, userId) {
  const tg = window.Telegram?.WebApp
  if (username) {
    const url = `https://t.me/${username}`
    tg?.openTelegramLink ? tg.openTelegramLink(url) : window.open(url, '_blank')
  } else {
    window.open(`tg://user?id=${userId}`, '_blank')
  }
}

function Avatar({ name, photoUrl, size = 24, square = false }) {
  const initials = (name || '?').trim().split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const style = {
    width: size,
    height: size,
    minWidth: size,
    minHeight: size,
    borderRadius: square ? '0px' : '50%',
    overflow: 'hidden',
  }

  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={name}
        style={style}
        className="object-cover"
        onError={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'flex' }}
      />
    )
  }

  return (
    <div
      style={style}
      className="flex items-center justify-center text-[9px] font-bold bg-[#353534] text-[#ebbbb4]"
    >
      {initials}
    </div>
  )
}

function pluralRaces(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'заезд'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'заезда'
  return 'заездов'
}
