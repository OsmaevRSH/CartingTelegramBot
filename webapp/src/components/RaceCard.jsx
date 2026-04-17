import { useState } from 'react'
import LapTimesTable from './LapTimesTable.jsx'

function PositionBadge({ pos }) {
  const posNum = parseInt(pos)
  const label = `P${pos}`
  const color =
    posNum === 1 ? 'text-[#ffb4a8] font-bold' :
    posNum === 2 ? 'text-[#e5e2e1]' :
    posNum === 3 ? 'text-[#ebbbb4]' :
    'text-[#454747]'
  return (
    <span className={`text-xs lap-time ${color} bg-[#2a2a2a] px-2 py-0.5`}>
      {label}
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

  const isP1 = parseInt(race.pos) === 1

  return (
    <div
      className="bg-[#0e0e0e] overflow-hidden transition-all duration-200"
      style={{ borderLeft: `3px solid ${isP1 ? '#ff5540' : '#2a2a2a'}` }}
    >
      {/* Header row */}
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
            <span className="text-[#ebbbb4] text-[10px] lap-time uppercase tracking-widest">{race.date}</span>
            <span className="text-[#353534] text-xs">·</span>
            <span className="text-[#ebbbb4] text-[10px] uppercase tracking-widest">{race.race_number}</span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[#e5e2e1] text-sm font-bold tracking-tight">
              Карт #{race.num}
            </span>
            {race.display_name && !race.display_name.startsWith('Карт #') && race.display_name !== race.num?.toString() && (
              <span className="text-[#454747] text-xs truncate">
                {race.display_name}
              </span>
            )}
          </div>
        </div>

        {/* Best lap */}
        <div className="text-right shrink-0">
          <div className="text-[#ffb4a8] lap-time text-sm font-bold">
            {race.best_lap || '—'}
          </div>
          <div className="text-[#454747] text-[9px] uppercase tracking-widest mt-0.5">лучший</div>
        </div>

        {/* Position */}
        <div className="shrink-0">
          <PositionBadge pos={race.pos} />
        </div>

        {/* Chevron */}
        <div className={`shrink-0 text-[#353534] transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="square" strokeLinejoin="miter"/>
          </svg>
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4" style={{ borderTop: '1px solid #201f1f' }}>
          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-2 mt-3 mb-4">
            <StatItem label="Позиция" value={race.pos} highlight="primary" />
            <StatItem label="Кругов" value={race.laps} />
            <StatItem label="Теор. круг" value={race.theor_lap_formatted} highlight="accent" mono />
          </div>

          {race.gap_to_leader && (
            <div className="mb-3 text-xs text-[#454747] uppercase tracking-widest">
              Отставание:{' '}
              <span className="text-[#e5e2e1] lap-time">{race.gap_to_leader}</span>
            </div>
          )}

          {/* Lap times */}
          {lapTimes.length > 0 && (
            <div className="mt-3">
              <div className="text-[9px] text-[#454747] mb-2 uppercase tracking-widest">
                Телеметрия кругов
              </div>
              <LapTimesTable lapTimes={lapTimes} />
            </div>
          )}

          {/* Delete button */}
          <div className="mt-4 flex justify-end">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-[#ebbbb4] text-xs uppercase tracking-widest">Удалить?</span>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-3 py-1.5 bg-[#1c1b1b] text-[#ebbbb4] text-xs uppercase tracking-wider"
                >
                  Отмена
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-3 py-1.5 bg-[#FF4444] text-white text-xs font-bold uppercase tracking-wider disabled:opacity-50"
                >
                  {deleting ? '...' : 'Удалить'}
                </button>
              </div>
            ) : (
              <button
                onClick={handleDelete}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[#FF4444] text-xs uppercase tracking-wider hover:bg-[#1a0000] transition-colors"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
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
    'text-sm font-bold tracking-tight',
    mono ? 'lap-time' : '',
    highlight === 'accent' ? 'text-[#ff5540]' :
    highlight === 'primary' ? 'text-[#ffb4a8]' :
    'text-[#e5e2e1]',
  ].join(' ')

  return (
    <div className="bg-[#1c1b1b] px-2.5 py-2 text-center">
      <div className={valClass}>{value ?? '—'}</div>
      <div className="text-[#454747] text-[9px] uppercase tracking-widest mt-0.5">{label}</div>
    </div>
  )
}
