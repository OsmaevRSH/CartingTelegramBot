import { useState } from 'react'
import LapTimesTable from './LapTimesTable.jsx'

function PositionBadge({ pos }) {
  const posNum = parseInt(pos)
  if (posNum === 1) return <span className="text-lg">🥇</span>
  if (posNum === 2) return <span className="text-lg">🥈</span>
  if (posNum === 3) return <span className="text-lg">🥉</span>
  return (
    <span className="text-[#FF6B00] font-bold text-sm lap-time">
      P{pos}
    </span>
  )
}

export default function RaceCard({ race, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  let lapTimes = []
  try {
    if (race.lap_times_json) {
      lapTimes = typeof race.lap_times_json === 'string'
        ? JSON.parse(race.lap_times_json)
        : race.lap_times_json
    }
  } catch (_) {}

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setDeleting(true)
    try {
      await onDelete(race)
    } finally {
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  return (
    <div
      className="bg-[#141414] border border-[#222222] rounded-xl overflow-hidden transition-all duration-200"
    >
      {/* Header row — always visible, tap to expand */}
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3"
        onClick={() => {
          setExpanded(e => !e)
          setConfirmDelete(false)
        }}
      >
        {/* Date + race */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[#888888] text-xs lap-time">{race.date}</span>
            <span className="text-[#444] text-xs">•</span>
            <span className="text-[#888888] text-xs">Заезд {race.race_number}</span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-white text-sm font-medium">
              Карт #{race.num}
            </span>
            {race.display_name && race.display_name !== race.num?.toString() && (
              <span className="text-[#888888] text-xs truncate">
                {race.display_name}
              </span>
            )}
          </div>
        </div>

        {/* Best lap */}
        <div className="text-right shrink-0">
          <div className="text-[#00FF7F] lap-time text-sm font-medium">
            {race.best_lap || '—'}
          </div>
          <div className="text-[#888888] text-xs mt-0.5">лучший</div>
        </div>

        {/* Position */}
        <div className="shrink-0 w-8 text-center">
          <PositionBadge pos={race.pos} />
        </div>

        {/* Chevron */}
        <div
          className={`shrink-0 text-[#444] transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-[#1e1e1e]">
          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-3 mt-3 mb-4">
            <StatItem label="Позиция" value={race.pos} highlight="orange" />
            <StatItem label="Кругов" value={race.laps} />
            <StatItem label="Теор. круг" value={race.theor_lap_formatted} highlight="accent" mono />
          </div>

          {race.gap_to_leader && (
            <div className="mb-3 text-xs text-[#888888]">
              Отставание от лидера:{' '}
              <span className="text-white lap-time">{race.gap_to_leader}</span>
            </div>
          )}

          {/* Lap times */}
          {lapTimes.length > 0 && (
            <div className="mt-3">
              <div className="text-xs text-[#888888] mb-2 uppercase tracking-wider">
                Время кругов
              </div>
              <LapTimesTable lapTimes={lapTimes} />
            </div>
          )}

          {/* Delete button */}
          <div className="mt-4 flex justify-end">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-[#888888] text-xs">Удалить заезд?</span>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-3 py-1.5 rounded-lg border border-[#333] text-[#888] text-xs"
                >
                  Отмена
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-3 py-1.5 rounded-lg bg-[#FF4444] text-white text-xs font-medium disabled:opacity-50"
                >
                  {deleting ? '...' : 'Удалить'}
                </button>
              </div>
            ) : (
              <button
                onClick={handleDelete}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#2a1a1a] text-[#FF4444] text-xs hover:bg-[#1a0a0a] transition-colors"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
                  <path d="M10 11v6M14 11v6"/>
                  <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
                </svg>
                Удалить
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatItem({ label, value, highlight, mono }) {
  const valClass = [
    'text-sm font-medium',
    mono ? 'lap-time' : '',
    highlight === 'accent' ? 'text-[#00FF7F]' :
    highlight === 'orange' ? 'text-[#FF6B00]' :
    'text-white',
  ].join(' ')

  return (
    <div className="bg-[#0f0f0f] rounded-lg px-2.5 py-2 text-center">
      <div className={valClass}>{value ?? '—'}</div>
      <div className="text-[#666] text-xs mt-0.5">{label}</div>
    </div>
  )
}
