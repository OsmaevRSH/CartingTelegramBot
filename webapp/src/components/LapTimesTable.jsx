// F1 timing colors:
// Purple  #B370FF — personal best (absolute best sector/lap)
// Green   #39FF6A — improvement over previous lap (not absolute best)
// Yellow  #F5C518 — no improvement, slower than best
// Grey              — start lap / no data

function timeToMs(str) {
  if (!str || str === '—') return Infinity
  try {
    const clean = str.trim()
    const [minPart, rest] = clean.split(':')
    if (!rest) return Infinity
    const [sec, ms] = rest.split('.')
    return parseInt(minPart) * 60000 + parseInt(sec) * 1000 + parseInt((ms || '0').padEnd(3, '0').slice(0, 3))
  } catch {
    return Infinity
  }
}

// Returns F1 color class for a sector value
// purple = absolute best, green = improved vs prev, yellow = no improvement
function sectorClass(val, bestMs, prevMs) {
  const ms = timeToMs(val)
  if (ms === Infinity) return 'text-[#353534]'
  if (ms === bestMs)   return 'text-[#B370FF] font-bold'   // purple — personal best
  if (ms < prevMs)     return 'text-[#39FF6A]'             // green  — improved
  return 'text-[#F5C518]'                                  // yellow — no improvement
}

// Returns F1 color class for full lap time
function lapClass(ms, bestLapMs, prevLapMs) {
  if (ms === Infinity) return 'text-[#353534]'
  if (ms === bestLapMs) return 'text-[#B370FF] font-bold'  // purple — best lap
  if (ms < prevLapMs)   return 'text-[#39FF6A]'            // green  — faster than prev
  return 'text-[#F5C518]'                                  // yellow — slower than prev
}

export default function LapTimesTable({ lapTimes }) {
  if (!lapTimes || lapTimes.length === 0) {
    return (
      <p className="text-[#ebbbb4] text-xs text-center py-2 uppercase tracking-widest">
        Нет данных по кругам
      </p>
    )
  }

  const raceLaps = lapTimes.filter(l => l.lap_number !== 0)

  // Absolute bests across all race laps
  const bestLapMs = Math.min(...raceLaps.map(l => timeToMs(l.lap_time)))
  const bestS1Ms  = Math.min(...raceLaps.map(l => timeToMs(l.sector1)))
  const bestS2Ms  = Math.min(...raceLaps.map(l => timeToMs(l.sector2)))
  const bestS3Ms  = Math.min(...raceLaps.map(l => timeToMs(l.sector3)))
  const bestS4Ms  = Math.min(...raceLaps.map(l => timeToMs(l.sector4)))

  const bestLapRow = raceLaps.find(l => timeToMs(l.lap_time) === bestLapMs)

  return (
    <div className="space-y-3">
      {/* Best lap banner */}
      {bestLapRow && (
        <div className="flex items-center gap-2 px-3 py-2 bg-[#0e0e0e]" style={{ borderLeft: '2px solid #B370FF' }}>
          <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: '#B370FF' }}>Лучший круг</span>
          <span className="lap-time text-sm font-bold ml-auto" style={{ color: '#B370FF' }}>{bestLapRow.lap_time}</span>
          <span className="text-[#ebbbb4] lap-time text-xs">Круг {bestLapRow.lap_number}</span>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs lap-time border-collapse">
          <thead>
            <tr className="text-[#454747] uppercase tracking-widest text-[9px]">
              <th className="pb-2 text-left w-5">#</th>
              <th className="pb-2 text-right px-1">Время</th>
              <th className="pb-2 text-right px-1">S1</th>
              <th className="pb-2 text-right px-1">S2</th>
              <th className="pb-2 text-right px-1">S3</th>
              <th className="pb-2 text-right px-1">S4</th>
            </tr>
          </thead>
          <tbody>
            {lapTimes.map((lap, idx) => {
              const isStart = lap.lap_number === 0
              const lapMs   = timeToMs(lap.lap_time)
              const isBestLap = !isStart && lapMs === bestLapMs

              // Previous race lap for "improved?" comparison
              const prevRaceIdx = raceLaps.findIndex(l => l.lap_number === lap.lap_number) - 1
              const prevLap = prevRaceIdx >= 0 ? raceLaps[prevRaceIdx] : null
              const prevLapMs = prevLap ? timeToMs(prevLap.lap_time) : Infinity
              const prevS1Ms  = prevLap ? timeToMs(prevLap.sector1)  : Infinity
              const prevS2Ms  = prevLap ? timeToMs(prevLap.sector2)  : Infinity
              const prevS3Ms  = prevLap ? timeToMs(prevLap.sector3)  : Infinity
              const prevS4Ms  = prevLap ? timeToMs(prevLap.sector4)  : Infinity

              return (
                <tr
                  key={idx}
                  className={`border-b border-[#201f1f] last:border-0 ${isBestLap ? 'bg-[#0e0e0e]' : ''}`}
                  style={isBestLap ? { borderLeft: '2px solid #B370FF' } : {}}
                >
                  {/* Lap number */}
                  <td className="py-1.5 text-left">
                    <span className={isStart ? 'text-[#454747]' : isBestLap ? 'text-[#B370FF]' : 'text-[#454747]'}>
                      {isStart ? 'S' : lap.lap_number}
                    </span>
                  </td>

                  {/* Lap time */}
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#454747]' : lapClass(lapMs, bestLapMs, prevLapMs)
                  }`}>
                    {lap.lap_time || '—'}
                  </td>

                  {/* Sectors */}
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#454747]' : sectorClass(lap.sector1, bestS1Ms, prevS1Ms)
                  }`}>
                    {isStart ? '—' : (lap.sector1 || '—')}
                  </td>
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#454747]' : sectorClass(lap.sector2, bestS2Ms, prevS2Ms)
                  }`}>
                    {lap.sector2 || '—'}
                  </td>
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#454747]' : sectorClass(lap.sector3, bestS3Ms, prevS3Ms)
                  }`}>
                    {lap.sector3 || '—'}
                  </td>
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#454747]' : sectorClass(lap.sector4, bestS4Ms, prevS4Ms)
                  }`}>
                    {lap.sector4 || '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2" style={{ background: '#B370FF' }} />
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">Личный рекорд</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2" style={{ background: '#39FF6A' }} />
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">Улучшение</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2" style={{ background: '#F5C518' }} />
          <span className="text-[#454747] text-[9px] uppercase tracking-widest">Без улучш.</span>
        </div>
      </div>
    </div>
  )
}
