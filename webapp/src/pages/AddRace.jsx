import { useState, useEffect } from 'react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { fetchArchive, fetchRaceCarts, fetchFullRace, saveStats } from '../api/client.js'

const STEP_DATE = 'date'
const STEP_RACE = 'race'
const STEP_CART = 'cart'
const STEP_RESULT = 'result'

const ALL_STEPS = [STEP_DATE, STEP_RACE, STEP_CART, STEP_RESULT]

function todayDDMMYYYY() {
  const d = new Date()
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  return `${dd}.${mm}.${yyyy}`
}

export default function AddRace({ userId, userName, targetUserId, targetUserName, onDone }) {
  const [step, setStep] = useState(STEP_DATE)

  const [archive, setArchive] = useState([])
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState(null)

  const [selectedDay, setSelectedDay] = useState(null)
  const [selectedRace, setSelectedRace] = useState(null)

  const [carts, setCarts] = useState([])
  const [cartsLoading, setCartsLoading] = useState(false)
  const [cartsError, setCartsError] = useState(null)
  const [selectedCart, setSelectedCart] = useState(null)

  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)

  const today = todayDDMMYYYY()

  const forUserId = targetUserId ?? userId
  const forUserName = targetUserName ?? userName ?? 'Я'
  const isForSelf = String(forUserId) === String(userId)

  useEffect(() => {
    async function load() {
      setArchiveLoading(true)
      setArchiveError(null)
      try {
        const data = await fetchArchive()
        setArchive(data || [])
      } catch (e) {
        setArchiveError(e.message)
      } finally {
        setArchiveLoading(false)
      }
    }
    load()
  }, [])

  const sortedArchive = [...archive].sort((a, b) => {
    const aIsToday = a.date === today
    const bIsToday = b.date === today
    if (aIsToday && !bIsToday) return -1
    if (!aIsToday && bIsToday) return 1
    const toSortable = (d) => d.substr(6, 4) + d.substr(3, 2) + d.substr(0, 2)
    return toSortable(b.date).localeCompare(toSortable(a.date))
  })

  function handleSelectDate(dayEntry) {
    setSelectedDay(dayEntry)
    setStep(STEP_RACE)
  }

  function handleSelectRace(race) {
    setSelectedRace(race)
    loadCarts(race.href)
  }

  async function loadCarts(href) {
    setCartsLoading(true)
    setCartsError(null)
    setCarts([])
    setStep(STEP_CART)
    try {
      const data = await fetchRaceCarts(href)
      setCarts(data || [])
    } catch (e) {
      setCartsError(e.message)
    } finally {
      setCartsLoading(false)
    }
  }

  async function handleSelectCart(cart) {
    setSelectedCart(cart)
    if (!forUserId && forUserId !== 0) {
      setSaveResult({ ok: false, error: 'Нет Telegram-аккаунта. Откройте приложение через бота.' })
      setStep(STEP_RESULT)
      return
    }
    setSaving(true)
    setStep(STEP_RESULT)
    setSaveResult(null)
    try {
      const fullRace = await fetchFullRace(selectedRace.href)
      const competitor = fullRace.find(
        (c) => String(c.num) === String(cart.number)
      ) || fullRace[0]

      if (!competitor) throw new Error('Участник не найден в заезде')

      const payload = {
        user_id: forUserId,
        date: selectedDay.date,
        race_number: selectedRace.number,
        race_href: selectedRace.href,
        competitor: {
          id: competitor.id,
          num: competitor.num,
          name: competitor.name,
          pos: competitor.pos,
          laps: competitor.laps,
          theor_lap: competitor.theor_lap,
          best_lap: competitor.best_lap,
          theor_lap_formatted: competitor.theor_lap_formatted,
          display_name: competitor.display_name,
          gap_to_leader: competitor.gap_to_leader,
          lap_times: competitor.lap_times || [],
        },
      }

      await saveStats(payload)
      setSaveResult({ ok: true, data: { ...competitor, date: selectedDay.date, race_number: selectedRace.number } })
    } catch (e) {
      setSaveResult({ ok: false, error: e.message })
    } finally {
      setSaving(false)
    }
  }

  function handleReset() {
    setStep(STEP_DATE)
    setSelectedDay(null)
    setSelectedRace(null)
    setCarts([])
    setSelectedCart(null)
    setSaveResult(null)
    setSaving(false)
  }

  function handleBack() {
    if (step === STEP_DATE) {
      onDone?.()
    } else if (step === STEP_RACE) {
      setStep(STEP_DATE)
      setSelectedDay(null)
    } else if (step === STEP_CART) {
      setStep(STEP_RACE)
      setCarts([])
      setSelectedCart(null)
    } else if (step === STEP_RESULT) {
      setStep(STEP_CART)
      setSaveResult(null)
    }
  }

  const bestLapCart = carts.reduce((best, c) => {
    if (!c.best_lap) return best
    if (!best) return c
    return c.best_lap < best.best_lap ? c : best
  }, null)

  const isBestCart = (cart) => bestLapCart && cart.number === bestLapCart.number
  const stepIndex = ALL_STEPS.indexOf(step)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3" style={{ borderBottom: '1px solid #201f1f' }}>
        {/* Step indicator */}
        <div className="flex items-center gap-1 mb-3">
          {ALL_STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-1">
              <div
                className={`w-5 h-5 flex items-center justify-center text-[9px] font-black transition-all ${
                  s === step
                    ? 'bg-[#ff5540] text-white'
                    : stepIndex > i
                    ? 'bg-[#201f1f] text-[#ff5540]'
                    : 'bg-[#1c1b1b] text-[#353534]'
                }`}
              >
                {stepIndex > i ? '✓' : i + 1}
              </div>
              {i < ALL_STEPS.length - 1 && (
                <div className={`w-4 h-px ${stepIndex > i ? 'bg-[#ff5540]' : 'bg-[#1c1b1b]'}`} />
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            disabled={saving}
            className="p-2 bg-[#1c1b1b] text-[#ebbbb4] disabled:opacity-50 hover:bg-[#2a2a2a] transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div>
            <h1 className="text-base font-bold text-[#e5e2e1] uppercase tracking-tight">Добавить заезд</h1>
            <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest mt-0.5">
              {!isForSelf && <span className="text-[#ff5540]">для {forUserName} · </span>}
              {step === STEP_DATE && 'Выберите дату'}
              {step === STEP_RACE && `${selectedDay?.date} — выберите заезд`}
              {step === STEP_CART && `${selectedRace?.number} — выберите карт`}
              {step === STEP_RESULT && 'Результат'}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 tab-content">

        {/* Step 0: Date list */}
        {step === STEP_DATE && (
          <div className="space-y-1.5">
            {archiveLoading && (
              <div className="flex justify-center py-16">
                <LoadingSpinner size="lg" label="Загрузка дат..." />
              </div>
            )}
            {archiveError && (
              <ErrorBanner message={archiveError} onRetry={() => {
                setArchiveError(null)
                setArchiveLoading(true)
                fetchArchive()
                  .then(d => setArchive(d || []))
                  .catch(e => setArchiveError(e.message))
                  .finally(() => setArchiveLoading(false))
              }} />
            )}
            {!archiveLoading && !archiveError && sortedArchive.map((day) => {
              const isToday = day.date === today
              return (
                <button
                  key={day.date}
                  onClick={() => handleSelectDate(day)}
                  className={`w-full text-left px-4 py-3 transition-all duration-150 ${
                    isToday
                      ? 'bg-[#0e0e0e]'
                      : 'bg-[#1c1b1b] hover:bg-[#2a2a2a]'
                  }`}
                  style={isToday ? { borderLeft: '3px solid #ff5540' } : { borderLeft: '3px solid transparent' }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`font-bold text-sm tracking-tight ${isToday ? 'text-[#ffb4a8]' : 'text-[#e5e2e1]'}`}>
                          {day.date}
                        </span>
                        {isToday && (
                          <span className="text-[8px] font-black uppercase tracking-widest bg-[#ff5540] text-white px-1.5 py-0.5">
                            Сегодня
                          </span>
                        )}
                      </div>
                      <div className="text-[#454747] text-[9px] uppercase tracking-widest mt-0.5">
                        {day.races?.length || 0} {pluralRaces(day.races?.length || 0)}
                      </div>
                    </div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#353534" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
                      <polyline points="9 18 15 12 9 6"/>
                    </svg>
                  </div>
                </button>
              )
            })}
            {!archiveLoading && !archiveError && sortedArchive.length === 0 && (
              <EmptyState message="Нет доступных заездов" />
            )}
          </div>
        )}

        {/* Step 1: Race list */}
        {step === STEP_RACE && selectedDay && (
          <div className="space-y-1.5">
            {(selectedDay.races || []).map((race) => (
              <button
                key={race.href}
                onClick={() => handleSelectRace(race)}
                className="w-full text-left px-4 py-3 bg-[#1c1b1b] hover:bg-[#2a2a2a] transition-all duration-150"
                style={{ borderLeft: '3px solid transparent' }}
              >
                <div className="flex items-center justify-between">
                  <div className="text-[#e5e2e1] font-bold text-sm tracking-tight">{race.number}</div>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#353534" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </div>
              </button>
            ))}
            {(!selectedDay.races || selectedDay.races.length === 0) && (
              <EmptyState message="Нет заездов для этой даты" />
            )}
          </div>
        )}

        {/* Step 2: Cart list */}
        {step === STEP_CART && (
          <div className="space-y-1.5">
            {cartsLoading && (
              <div className="flex justify-center py-16">
                <LoadingSpinner size="lg" label="Загрузка картов..." />
              </div>
            )}
            {cartsError && (
              <ErrorBanner message={cartsError} onRetry={() => loadCarts(selectedRace.href)} />
            )}
            {!cartsLoading && !cartsError && carts.map((cart) => {
              const isBest = isBestCart(cart)
              return (
                <button
                  key={cart.id}
                  onClick={() => handleSelectCart(cart)}
                  className={`w-full text-left px-4 py-3 transition-all duration-150 ${
                    isBest ? 'bg-[#0e0e0e]' : 'bg-[#1c1b1b] hover:bg-[#2a2a2a]'
                  }`}
                  style={isBest ? { borderLeft: '3px solid #ff5540' } : { borderLeft: '3px solid transparent' }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`font-bold text-sm tracking-tight ${isBest ? 'text-[#ffb4a8]' : 'text-[#e5e2e1]'}`}>
                          Карт #{cart.id || cart.number}
                        </span>
                        {isBest && (
                          <span className="text-[8px] font-black uppercase tracking-widest bg-[#ff5540] text-white px-1.5 py-0.5">
                            Лучший
                          </span>
                        )}
                      </div>
                      {cart.position && (
                        <div className="text-[#454747] text-[9px] uppercase tracking-widest mt-0.5">
                          Позиция {cart.position}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className={`lap-time text-sm font-bold ${isBest ? 'text-[#ff5540]' : 'text-[#ebbbb4]'}`}>
                        {cart.best_lap || '—'}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })}
            {!cartsLoading && !cartsError && carts.length === 0 && (
              <EmptyState message="Нет картов для этого заезда" />
            )}
          </div>
        )}

        {/* Step 3: Result */}
        {step === STEP_RESULT && (
          <div className="flex flex-col items-center justify-center py-8 gap-6">
            {saving && (
              <div className="flex flex-col items-center gap-4">
                <LoadingSpinner size="lg" />
                <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest">Сохранение результата...</p>
              </div>
            )}

            {!saving && saveResult?.ok && (
              <div className="w-full">
                <div className="flex justify-center mb-6">
                  <div className="w-16 h-16 bg-[#0e0e0e] flex items-center justify-center" style={{ borderTop: '3px solid #ff5540' }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ff5540" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </div>
                </div>

                <h2 className="text-center text-xl font-black text-[#e5e2e1] mb-1 uppercase tracking-tight">Сохранено!</h2>
                <p className="text-center text-[#ebbbb4] text-[9px] uppercase tracking-widest mb-1">Результат успешно добавлен</p>
                {!isForSelf && (
                  <p className="text-center text-[#ff5540] text-[9px] uppercase tracking-widest mb-5">для {forUserName}</p>
                )}
                {isForSelf && <div className="mb-5" />}

                {saveResult.data && (
                  <div className="bg-[#0e0e0e] p-4 mb-6" style={{ borderLeft: '3px solid #ff5540' }}>
                    <div className="grid grid-cols-2 gap-3">
                      <InfoRow label="Дата" value={saveResult.data.date} />
                      <InfoRow label="Заезд" value={saveResult.data.race_number} />
                      <InfoRow label="Карт" value={`#${saveResult.data.num}`} />
                      <InfoRow label="Позиция" value={`P${saveResult.data.pos}`} highlight="primary" />
                      <InfoRow label="Лучший круг" value={saveResult.data.best_lap} highlight="accent" mono />
                      <InfoRow label="Кругов" value={saveResult.data.laps} />
                    </div>
                  </div>
                )}

                <div className="flex flex-col gap-2">
                  <button
                    onClick={handleReset}
                    className="w-full py-3 bg-[#ff5540] text-white font-black text-sm uppercase tracking-widest hover:bg-[#e84b38] transition-colors"
                  >
                    Добавить ещё
                  </button>
                  {onDone && (
                    <button
                      onClick={onDone}
                      className="w-full py-3 bg-[#1c1b1b] text-[#ebbbb4] font-bold text-sm uppercase tracking-widest hover:bg-[#2a2a2a] transition-colors"
                    >
                      Готово
                    </button>
                  )}
                </div>
              </div>
            )}

            {!saving && saveResult && !saveResult.ok && (
              <div className="w-full">
                <div className="flex justify-center mb-6">
                  <div className="w-16 h-16 bg-[#0e0e0e] flex items-center justify-center" style={{ borderTop: '3px solid #FF4444' }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </div>
                </div>

                <h2 className="text-center text-xl font-black text-[#e5e2e1] mb-1 uppercase tracking-tight">Ошибка</h2>
                <p className="text-center text-[#FF4444] text-sm mb-6 break-words">{saveResult.error}</p>

                <div className="flex gap-2">
                  <button
                    onClick={() => setStep(STEP_CART)}
                    className="flex-1 py-3 bg-[#1c1b1b] text-[#ebbbb4] font-bold text-sm uppercase tracking-widest hover:bg-[#2a2a2a] transition-colors"
                  >
                    Назад
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex-1 py-3 bg-[#2a2a2a] text-[#e5e2e1] font-bold text-sm uppercase tracking-widest hover:bg-[#353534] transition-colors"
                  >
                    Заново
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function pluralRaces(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'заезд'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'заезда'
  return 'заездов'
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="bg-[#0e0e0e] p-4 flex flex-col gap-3" style={{ borderLeft: '3px solid #FF4444' }}>
      <div className="flex items-start gap-3">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="square" className="shrink-0 mt-0.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p className="text-[#FF4444] text-sm">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="self-start text-[9px] text-[#ebbbb4] uppercase tracking-widest">
          Повторить
        </button>
      )}
    </div>
  )
}

function EmptyState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="text-[#ff5540] text-4xl font-black">—</div>
      <p className="text-[#ebbbb4] text-[9px] uppercase tracking-widest">{message}</p>
    </div>
  )
}

function InfoRow({ label, value, highlight, mono }) {
  const valClass = [
    'text-sm font-bold tracking-tight',
    mono ? 'lap-time' : '',
    highlight === 'accent' ? 'text-[#ff5540]' :
    highlight === 'primary' ? 'text-[#ffb4a8]' :
    'text-[#e5e2e1]',
  ].join(' ')
  return (
    <div>
      <div className="text-[#454747] text-[9px] uppercase tracking-widest mb-0.5">{label}</div>
      <div className={valClass}>{value ?? '—'}</div>
    </div>
  )
}
