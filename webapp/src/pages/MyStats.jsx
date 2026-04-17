import { useState, useEffect, useCallback } from 'react'
import RaceCard from '../components/RaceCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import AddRace from './AddRace.jsx'
import { fetchStats, deleteStats, fetchUsers } from '../api/client.js'

export default function MyStats({ userId, userName }) {
  const [isAdding, setIsAdding] = useState(false)
  const [users, setUsers] = useState([])
  const [selectedId, setSelectedId] = useState(userId)
  const [selectedName, setSelectedName] = useState('Я')

  const [races, setRaces] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load pilots list on mount
  useEffect(() => {
    fetchUsers()
      .then(data => setUsers(data || []))
      .catch(() => setUsers([]))
  }, [])

  // Sync selectedId when userId changes (on first load)
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
  const headerName = isMyself ? 'Мои заезды' : `Заезды — ${selectedName}`

  // Other pilots (exclude current user)
  const otherPilots = users.filter(u => String(u.user_id) !== String(userId))

  function handleAddDone() {
    setIsAdding(false)
    load(selectedId)
  }

  if (isAdding) {
    return (
      <AddRace userId={userId} userName={userName} onDone={handleAddDone} />
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-lg font-bold text-white">{headerName}</h1>
            {!loading && races.length > 0 && (
              <p className="text-[#888888] text-xs mt-0.5">
                {races.length} {pluralRaces(races.length)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAdding(true)}
            className="p-2 rounded-lg bg-[#00FF7F20] text-[#00FF7F] transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          <button
            onClick={() => load(selectedId)}
            disabled={loading}
            className="p-2 rounded-lg bg-[#1e1e1e] text-[#888] disabled:opacity-50 transition-colors"
          >
            <svg
              width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              className={loading ? 'animate-spin' : ''}
            >
              <path d="M23 4v6h-6"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
          </button>
          </div>
        </div>

        {/* Pilot selector */}
        {(otherPilots.length > 0) && (
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {/* All pilots including current user */}
            {[
              { user_id: userId, display_name: userName || 'Я', photo_url: users.find(u => String(u.user_id) === String(userId))?.photo_url, telegram_username: users.find(u => String(u.user_id) === String(userId))?.telegram_username, _isMe: true },
              ...otherPilots,
            ].map(u => {
              const isSelected = String(selectedId) === String(u.user_id)
              return (
                <div key={u.user_id} className="shrink-0 flex items-center gap-0.5">
                  <button
                    onClick={() => handleSelectPilot(u.user_id, u.display_name)}
                    className={`flex items-center gap-1.5 pl-1 pr-3 py-1 rounded-full text-xs font-medium transition-all ${
                      isSelected
                        ? 'bg-[#00FF7F] text-black'
                        : 'bg-[#1e1e1e] text-[#888] border border-[#333]'
                    }`}
                  >
                    <Avatar name={u.display_name} photoUrl={u.photo_url} size={20} active={isSelected} />
                    {u._isMe ? (userName || 'Я') : u.display_name}
                  </button>
                  <button
                    onClick={() => openTgProfile(u.telegram_username, u.user_id)}
                    className="p-1 text-[#444] hover:text-[#777] transition-colors"
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                  </button>
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
          <div className="bg-[#1a0000] border border-[#FF444433] rounded-xl p-4 flex items-start gap-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
              <p className="text-[#FF4444] text-sm">{error}</p>
              <button onClick={() => load(selectedId)} className="text-xs text-[#888] underline mt-1">
                Повторить
              </button>
            </div>
          </div>
        )}

        {!loading && !error && selectedId === null && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="text-4xl">🔒</div>
            <p className="text-[#888888] text-sm text-center">
              Откройте приложение через Telegram-бота
            </p>
          </div>
        )}

        {!loading && !error && selectedId !== null && races.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="text-5xl">🏁</div>
            <p className="text-white font-medium">Заездов пока нет</p>
            <p className="text-[#888888] text-sm text-center">
              {isMyself
                ? 'Нажмите + чтобы добавить первый заезд'
                : `У ${selectedName} нет сохранённых заездов`}
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
    // открываем профиль по ID — из него можно перейти в чат
    const url = `tg://user?id=${userId}`
    window.open(url, '_blank')
  }
}

function Avatar({ name, photoUrl, size = 24, active = false }) {
  const initials = (name || '?').trim().split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const style = { width: size, height: size, minWidth: size, minHeight: size, borderRadius: '50%', overflow: 'hidden' }

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
      className={`flex items-center justify-center text-[9px] font-bold ${
        active ? 'bg-black/20 text-black' : 'bg-[#333] text-[#aaa]'
      }`}
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
