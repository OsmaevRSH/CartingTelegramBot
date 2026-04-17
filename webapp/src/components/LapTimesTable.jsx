export default function LapTimesTable({ lapTimes }) {
  if (!lapTimes || lapTimes.length === 0) {
    return (
      <p className="text-[#888888] text-xs text-center py-2">
        Нет данных по кругам
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs lap-time">
        <thead>
          <tr className="text-[#888888] border-b border-[#222222]">
            <th className="pb-1.5 text-left w-6">#</th>
            <th className="pb-1.5 text-right">Время</th>
            <th className="pb-1.5 text-right">S1</th>
            <th className="pb-1.5 text-right">S2</th>
            <th className="pb-1.5 text-right">S3</th>
            <th className="pb-1.5 text-right">S4</th>
          </tr>
        </thead>
        <tbody>
          {lapTimes.map((lap, idx) => {
            const isStart = lap.lap_number === 0
            const isFirst = idx === 0
            return (
              <tr
                key={idx}
                className={`border-b border-[#1a1a1a] last:border-0 ${
                  isStart ? 'text-[#888888]' : 'text-[#FFFFFF]'
                }`}
              >
                <td className="py-1 text-left text-[#888888]">
                  {isStart ? 'S' : lap.lap_number}
                </td>
                <td className="py-1 text-right text-[#00FF7F]">
                  {lap.lap_time || '—'}
                </td>
                <td className="py-1 text-right">
                  {isStart ? '—' : (lap.sector1 || '—')}
                </td>
                <td className="py-1 text-right">
                  {lap.sector2 || '—'}
                </td>
                <td className="py-1 text-right">
                  {lap.sector3 || '—'}
                </td>
                <td className="py-1 text-right">
                  {lap.sector4 || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
