import { useState, useEffect } from 'react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { fetchStats, fetchUsers } from '../api/client.js'

// ─── helpers ─────────────────────────────────────────────────────────────────

function timeToMs(str) {
  if (!str || str === '—') return null
  try {
    const [minPart, rest] = str.trim().split(':')
    if (!rest) return null
    const [sec, ms] = rest.split('.')
    return parseInt(minPart) * 60000 + parseInt(sec) * 1000 + parseInt((ms || '0').padEnd(3, '0').slice(0, 3))
  } catch { return null }
}

function fmtDelta(ms) {
  if (ms === null) return null
  const sign = ms <= 0 ? '' : '+'
  const abs  = Math.abs(ms)
  const s    = Math.floor(abs / 1000)
  const m    = abs % 1000
  return `${sign}${ms <= 0 ? '-' : '+'}${s}.${String(m).padStart(3, '0')}`
}

function parseLaps(json) {
  try {
    const arr = typeof json === 'string' ? JSON.parse(json) : json
    return (arr || []).filter(l => l.lap_number !== 0)
  } catch { return [] }
}

// ─── mini components ──────────────────────────────────────────────────────────

function Avatar({ name, photoUrl, size = 28 }) {
  const [err, setErr] = useState(false)
  const initials = (name || '?').trim().split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const style = { width: size, height: size, minWidth: size, overflow: 'hidden' }
  if (photoUrl && !err) return <img src={photoUrl} alt={name} style={style} className="object-cover" onError={() => setErr(true)} />
  return <div style={style} className="flex items-center justify-center text-[9px] font-bold bg-[#353534] text-[#ebbbb4]">{initials}</div>
}

// Bar showing who's faster in a sector
function DeltaBar({ myMs, theirMs, label }) {
  if (myMs === null || theirMs === null) return null
  const delta  = myMs - theirMs       // negative = I'm faster
  const absDelta = Math.abs(delta)
  const iAmFaster = delta < 0
  const isTie     = delta === 0

  const color  = isTie ? '#454747' : iAmFaster ? '#39FF6A' : '#FF4444'
  const deltaStr = isTie ? '0.000' : (iAmFaster ? '-' : '+') + (absDelta / 1000).toFixed(3)

  // Bar width 0–100%, capped at ±2 seconds
  const maxMs  = 2000
  const pct    = Math.min(100, (absDelta / maxMs) * 100)

  return (
    <div className="flex items-center gap-2 py-0.5">
      <span className="text-[#454747] text-[9px] uppercase tracking-widest w-5 shrink-0">{label}</span>
      <div className="flex-1 flex items-center gap-1">
        {/* my side */}
        <div className="flex-1 flex justify-end">
          {iAmFaster && !isTie && (
            <div className="h-2 transition-all" style={{ width: `${pct}%`, background: color }} />
          )}
        </div>
        {/* delta label */}
        <span className="text-[9px] font-bold lap-time w-16 text-center" style={{ color }}>
          {deltaStr}
        </span>
        {/* their side */}
        <div className="flex-1">
          {!iAmFaster && !isTie && (
            <div className="h-2 transition-all" style={{ width: `${pct}%`, background: color }} />
          )}
        </div>
      </div>
    </div>
  )
}

// ─── main comparison view ─────────────────────────────────────────────────────

function CompareView({ myRace, myLaps, theirRace, theirName, theirLaps, myName }) {
  const myBestMs    = Math.min(...myLaps.map(l => timeToMs(l.lap_time)).filter(Boolean))
  const theirBestMs = Math.min(...theirLaps.map(l => timeToMs(l.lap_time)).filter(Boolean))
  const overallDelta = myBestMs - theirBestMs  // negative = I'm faster

  const allNums = [...new Set([
    ...myLaps.map(l => l.lap_number),
    ...theirLaps.map(l => l.lap_number),
  ])].sort((a, b) => a - b)

  return (
    <div className="space-y-4">
      {/* Overall header */}
      <div className="flex gap-2">
        <div
          className="flex-1 px-3 py-3 text-center bg-[#0e0e0e]"
          style={{ borderTop: `2px solid ${overallDelta <= 0 ? '#B370FF' : '#353534'}` }}
        >
          <div className="text-[9px] font-bold uppercase tracking-widest text-[#ebbbb4] truncate mb-1">{myName}</div>
          <div className="lap-time text-lg font-black" style={{ color: overallDelta <= 0 ? '#B370FF' : '#e5e2e1' }}>
            {myLaps.find(l => timeToMs(l.lap_time) === myBestMs)?.lap_time || '—'}
          </div>
          <div className="text-[9px] text-[#454747] uppercase tracking-widest mt-0.5">
            {myRace.date} · К#{myRace.num}
          </div>
        </div>

        <div className="flex flex-col items-center justify-center px-2 gap-1">
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">vs</span>
          {overallDelta !== 0 && (
            <span className="text-[9px] font-black lap-time" style={{ color: overallDelta < 0 ? '#39FF6A' : '#FF4444' }}>
              {overallDelta < 0 ? '' : '+'}{(overallDelta / 1000).toFixed(3)}
            </span>
          )}
        </div>

        <div
          className="flex-1 px-3 py-3 text-center bg-[#0e0e0e]"
          style={{ borderTop: `2px solid ${overallDelta >= 0 ? '#B370FF' : '#353534'}` }}
        >
          <div className="text-[9px] font-bold uppercase tracking-widest text-[#ebbbb4] truncate mb-1">{theirName}</div>
          <div className="lap-time text-lg font-black" style={{ color: overallDelta >= 0 ? '#B370FF' : '#e5e2e1' }}>
            {theirLaps.find(l => timeToMs(l.lap_time) === theirBestMs)?.lap_time || '—'}
          </div>
          <div className="text-[9px] text-[#454747] uppercase tracking-widest mt-0.5">
            {theirRace.date} · К#{theirRace.num}
          </div>
        </div>
      </div>

      {/* Per-lap comparison */}
      {allNums.map(lapNum => {
        const myLap    = myLaps.find(l => l.lap_number === lapNum)
        const theirLap = theirLaps.find(l => l.lap_number === lapNum)
        const myMs     = timeToMs(myLap?.lap_time)
        const theirMs  = timeToMs(theirLap?.lap_time)
        const lapDelta = myMs !== null && theirMs !== null ? myMs - theirMs : null

        const iAmFasterLap = lapDelta !== null && lapDelta < 0
        const isMyBest     = myMs !== null && myMs === myBestMs
        const isTheirBest  = theirMs !== null && theirMs === theirBestMs

        return (
          <div key={lapNum} className="bg-[#0e0e0e]" style={{ borderLeft: '2px solid #201f1f' }}>
            {/* Lap header */}
            <div className="flex items-center justify-between px-3 py-2" style={{ borderBottom: '1px solid #201f1f' }}>
              <span className="text-[9px] font-bold uppercase tracking-widest text-[#454747]">
                Круг {lapNum}
              </span>
              {lapDelta !== null && (
                <span className="text-[9px] font-black lap-time" style={{ color: lapDelta < 0 ? '#39FF6A' : lapDelta > 0 ? '#FF4444' : '#454747' }}>
                  {lapDelta === 0 ? '0.000' : (lapDelta < 0 ? '' : '+') + (lapDelta / 1000).toFixed(3)}
                </span>
              )}
            </div>

            {/* Times row */}
            <div className="flex items-center justify-between px-3 py-2">
              <span
                className="lap-time text-sm font-bold"
                style={{ color: isMyBest ? '#B370FF' : iAmFasterLap ? '#39FF6A' : myMs !== null ? '#e5e2e1' : '#454747' }}
              >
                {myLap?.lap_time || '—'}
              </span>
              <span className="text-[9px] text-[#454747] uppercase tracking-widest">общее</span>
              <span
                className="lap-time text-sm font-bold"
                style={{ color: isTheirBest ? '#B370FF' : !iAmFasterLap && lapDelta !== null && lapDelta !== 0 ? '#39FF6A' : theirMs !== null ? '#e5e2e1' : '#454747' }}
              >
                {theirLap?.lap_time || '—'}
              </span>
            </div>

            {/* Sector delta bars */}
            <div className="px-3 pb-3 space-y-1">
              <div className="flex items-center justify-between text-[8px] text-[#353534] uppercase tracking-widest mb-1">
                <span>← быстрее</span>
                <span>быстрее →</span>
              </div>
              {[
                { key: 'sector1', label: 'S1' },
                { key: 'sector2', label: 'S2' },
                { key: 'sector3', label: 'S3' },
                { key: 'sector4', label: 'S4' },
              ].map(({ key, label }) => {
                const mySec    = timeToMs(myLap?.[key])
                const theirSec = timeToMs(theirLap?.[key])
                if (mySec === null && theirSec === null) return null
                return <DeltaBar key={key} myMs={mySec} theirMs={theirSec} label={label} />
              })}
            </div>
          </div>
        )
      })}

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1 pb-2">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2" style={{ background: '#B370FF' }} />
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">Рекорд</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-[#39FF6A]" />
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">Быстрее</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-[#FF4444]" />
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">Медленнее</span>
        </div>
      </div>
    </div>
  )
}

// ─── main screen ──────────────────────────────────────────────────────────────

const STEP_USER = 'user'
const STEP_RACE = 'race'
const STEP_VIEW = 'view'

export default function CompareScreen({ myRace, myLaps, myName, onClose }) {
  const [step, setStep]         = useState(STEP_USER)
  const [users, setUsers]       = useState([])
  const [loading, setLoading]   = useState(false)
  const [pickedUser, setPickedUser] = useState(null)
  const [races, setRaces]       = useState([])
  const [pickedRace, setPickedRace] = useState(null)
  const [sortBy, setSortBy]     = useState('date') // 'date' | 'time'

  useEffect(() => {
    setLoading(true)
    fetchUsers()
      .then(u => setUsers(u || []))
      .catch(() => setUsers([]))
      .finally(() => setLoading(false))
  }, [])

  async function handlePickUser(user) {
    setPickedUser(user)
    setStep(STEP_RACE)
    setLoading(true)
    try {
      const data = await fetchStats(user.user_id)
      const withLaps = (data || []).filter(r => {
        try {
          const l = parseLaps(r.lap_times_json)
          return l.length > 0
        } catch { return false }
      }).sort((a, b) => {
        const ts = d => d.substr(6,4)+d.substr(3,2)+d.substr(0,2)
        return ts(b.date).localeCompare(ts(a.date))
      })
      setRaces(withLaps)
    } catch { setRaces([]) }
    finally { setLoading(false) }
  }

  function handlePickRace(race) {
    setPickedRace(race)
    setStep(STEP_VIEW)
  }

  const theirLaps = pickedRace ? parseLaps(pickedRace.lap_times_json) : []

  const sortedRaces = [...races].sort((a, b) => {
    if (sortBy === 'time') return timeToMs(a.best_lap) - timeToMs(b.best_lap)
    const ts = d => d.substr(6, 4) + d.substr(3, 2) + d.substr(0, 2)
    return ts(b.date).localeCompare(ts(a.date))
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3" style={{ borderBottom: '1px solid #201f1f' }}>
        <div className="flex items-center gap-3">
          <button
            onClick={step === STEP_USER ? onClose : () => setStep(step === STEP_VIEW ? STEP_RACE : STEP_USER)}
            className="p-2 bg-[#1c1b1b] text-[#ebbbb4] hover:bg-[#2a2a2a] transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div className="min-w-0">
            <h1 className="text-base font-black text-[#e5e2e1] uppercase tracking-tighter leading-none">
              Сравнение
            </h1>
            <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest mt-0.5">
              {step === STEP_USER && `${myRace.date} · К#${myRace.num} — выберите пилота`}
              {step === STEP_RACE && `${pickedUser?.display_name} — выберите заезд`}
              {step === STEP_VIEW && `${myName} vs ${pickedUser?.display_name}`}
            </p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-1 mt-3">
          {[STEP_USER, STEP_RACE, STEP_VIEW].map((s, i) => (
            <div key={s} className="flex items-center gap-1">
              <div className={`w-5 h-1 transition-all ${
                s === step ? 'bg-[#ff5540]' :
                [STEP_USER, STEP_RACE, STEP_VIEW].indexOf(s) < [STEP_USER, STEP_RACE, STEP_VIEW].indexOf(step) ? 'bg-[#ff554066]' :
                'bg-[#1c1b1b]'
              }`} />
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 tab-content">

        {/* Step 1: Pick user */}
        {step === STEP_USER && (
          <div className="space-y-1.5">
            {loading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" label="Загрузка пилотов..." /></div>}
            {!loading && users.map(u => (
              <button
                key={u.user_id}
                onClick={() => handlePickUser(u)}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-[#1c1b1b] hover:bg-[#2a2a2a] transition-colors text-left"
                style={{ borderLeft: '3px solid transparent' }}
              >
                <div className="flex items-center gap-3">
                  <Avatar name={u.display_name} photoUrl={u.photo_url} size={32} />
                  <span className="text-[#e5e2e1] text-sm font-bold uppercase tracking-tight">{u.display_name}</span>
                </div>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#353534" strokeWidth="2" strokeLinecap="square">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            ))}
            {!loading && users.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="text-[#ff5540] text-4xl font-black">—</div>
                <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest">Нет других пилотов</p>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Pick race */}
        {step === STEP_RACE && (
          <div className="space-y-1.5">
            {!loading && races.length > 0 && (
              <div className="flex justify-end mb-2">
                <button
                  onClick={() => setSortBy(prev => prev === 'date' ? 'time' : 'date')}
                  className="px-2 py-1.5 bg-[#1c1b1b] text-[#ebbbb4] text-[9px] font-bold uppercase tracking-widest flex items-center gap-1 transition-colors hover:bg-[#2a2a2a]"
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
                    <line x1="4" y1="6" x2="11" y2="6"/><line x1="4" y1="12" x2="16" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/>
                  </svg>
                  {sortBy === 'date' ? 'По дате' : 'По времени'}
                </button>
              </div>
            )}
            {loading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" label="Загрузка заездов..." /></div>}
            {!loading && sortedRaces.map((r, idx) => (
              <button
                key={idx}
                onClick={() => handlePickRace(r)}
                className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1b1b] hover:bg-[#2a2a2a] transition-colors text-left"
                style={{ borderLeft: '3px solid transparent' }}
              >
                <div>
                  <div className="text-[#e5e2e1] text-sm font-bold tracking-tight">{r.date} · {r.race_number}</div>
                  <div className="text-[#454747] text-[9px] uppercase tracking-widest mt-0.5">Карт #{r.num} · P{r.pos}</div>
                </div>
                <div className="text-right">
                  <div className="text-[#ffb4a8] lap-time text-sm font-bold">{r.best_lap || '—'}</div>
                </div>
              </button>
            ))}
            {!loading && races.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="text-[#ff5540] text-4xl font-black">—</div>
                <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest">Нет заездов с телеметрией</p>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Comparison view */}
        {step === STEP_VIEW && pickedRace && theirLaps.length > 0 && (
          <CompareView
            myRace={myRace}
            myLaps={myLaps}
            myName={myName}
            theirRace={pickedRace}
            theirLaps={theirLaps}
            theirName={pickedUser?.display_name || '?'}
          />
        )}
      </div>
    </div>
  )
}
