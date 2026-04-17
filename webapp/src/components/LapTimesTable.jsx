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

export default function LapTimesTable({ lapTimes }) {
  if (!lapTimes || lapTimes.length === 0) {
    return (
      <p className="text-[#888888] text-xs text-center py-2">
        Нет данных по кругам
      </p>
    )
  }

  const raceLaps = lapTimes.filter(l => l.lap_number !== 0)

  // Find best values across all race laps
  const bestLapMs  = Math.min(...raceLaps.map(l => timeToMs(l.lap_time)))
  const bestS1Ms   = Math.min(...raceLaps.map(l => timeToMs(l.sector1)))
  const bestS2Ms   = Math.min(...raceLaps.map(l => timeToMs(l.sector2)))
  const bestS3Ms   = Math.min(...raceLaps.map(l => timeToMs(l.sector3)))
  const bestS4Ms   = Math.min(...raceLaps.map(l => timeToMs(l.sector4)))

  function lapColor(val) {
    const ms = timeToMs(val)
    if (ms === Infinity) return 'text-[#555]'
    if (ms === bestLapMs) return 'text-[#C084FC] font-bold'  // purple — best lap
    return 'text-[#ccc]'
  }

  function sectorColor(val, bestMs) {
    const ms = timeToMs(val)
    if (ms === Infinity) return 'text-[#555]'
    if (ms === bestMs) return 'text-[#00FF7F]'  // green — best sector
    return 'text-[#888]'
  }

  const bestLapRow = raceLaps.find(l => timeToMs(l.lap_time) === bestLapMs)

  return (
    <div className="space-y-3">
      {/* Best lap banner */}
      {bestLapRow && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#1a0033] border border-[#C084FC33]">
          <span className="text-[#C084FC] text-xs font-bold uppercase tracking-wider">Лучший круг</span>
          <span className="text-[#C084FC] lap-time text-sm font-bold ml-auto">{bestLapRow.lap_time}</span>
          <span className="text-[#888] lap-time text-xs">Круг {bestLapRow.lap_number}</span>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs lap-time border-collapse">
          <thead>
            <tr className="text-[#555] uppercase tracking-wider text-[10px]">
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
              const isBestLap = !isStart && timeToMs(lap.lap_time) === bestLapMs

              return (
                <tr
                  key={idx}
                  className={`border-b border-[#1a1a1a] last:border-0 ${
                    isBestLap ? 'bg-[#1a0033]' : ''
                  }`}
                >
                  {/* Lap number */}
                  <td className="py-1.5 text-left">
                    <span className={`${isBestLap ? 'text-[#C084FC]' : 'text-[#555]'}`}>
                      {isStart ? 'S' : lap.lap_number}
                    </span>
                  </td>

                  {/* Lap time */}
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#555]' : lapColor(lap.lap_time)
                  }`}>
                    {lap.lap_time || '—'}
                  </td>

                  {/* Sectors */}
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? 'text-[#555]' : sectorColor(lap.sector1, bestS1Ms)
                  }`}>
                    {isStart ? '—' : (lap.sector1 || '—')}
                  </td>
                  <td className={`py-1.5 text-right px-1 ${
                    isStart ? sectorColor(lap.sector2, bestS2Ms) : sectorColor(lap.sector2, bestS2Ms)
                  }`}>
                    {lap.sector2 || '—'}
                  </td>
                  <td className={`py-1.5 text-right px-1 ${
                    sectorColor(lap.sector3, bestS3Ms)
                  }`}>
                    {lap.sector3 || '—'}
                  </td>
                  <td className={`py-1.5 text-right px-1 ${
                    sectorColor(lap.sector4, bestS4Ms)
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
          <div className="w-2 h-2 rounded-full bg-[#C084FC]" />
          <span className="text-[#555] text-[10px]">Лучший круг</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-[#00FF7F]" />
          <span className="text-[#555] text-[10px]">Лучший сектор</span>
        </div>
      </div>
    </div>
  )
}
