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

  // Step 0: dates
  const [archive, setArchive] = useState([])
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState(null)

  // Step 1: races
  const [selectedDay, setSelectedDay] = useState(null)
  const [selectedRace, setSelectedRace] = useState(null)

  // Step 2: carts
  const [carts, setCarts] = useState([])
  const [cartsLoading, setCartsLoading] = useState(false)
  const [cartsError, setCartsError] = useState(null)
  const [selectedCart, setSelectedCart] = useState(null)

  // Step 3: result
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)

  const today = todayDDMMYYYY()

  // Who are we adding for
  const forUserId = targetUserId ?? userId
  const forUserName = targetUserName ?? userName ?? 'Я'
  const isForSelf = String(forUserId) === String(userId)

  // Load archive on mount
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

  // Sort archive so today comes first, then descending
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

      if (!competitor) {
        throw new Error('Участник не найден в заезде')
      }

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
      <div className="px-4 pt-5 pb-3">
        {/* Step breadcrumb */}
        <div className="flex items-center gap-2 mb-3">
          {ALL_STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  s === step
                    ? 'bg-[#00FF7F] text-black'
                    : stepIndex > i
                    ? 'bg-[#004d26] text-[#00FF7F] text-[10px]'
                    : 'bg-[#1e1e1e] text-[#555]'
                }`}
              >
                {stepIndex > i ? '✓' : i + 1}
              </div>
              {i < ALL_STEPS.length - 1 && (
                <div className={`w-4 h-px ${stepIndex > i ? 'bg-[#004d26]' : 'bg-[#1e1e1e]'}`} />
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            disabled={saving}
            className="p-2 rounded-lg bg-[#1e1e1e] text-[#888] disabled:opacity-50"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div>
            <h1 className="text-lg font-bold text-white">Добавить заезд</h1>
            <p className="text-[#888888] text-xs mt-0.5">
              {!isForSelf && <span className="text-[#00FF7F]">для {forUserName} · </span>}
              {step === STEP_DATE && 'Выберите дату'}
              {step === STEP_RACE && `${selectedDay?.date} — выберите заезд`}
              {step === STEP_CART && `${selectedRace?.number} — выберите карт`}
              {step === STEP_RESULT && 'Результат'}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 tab-content">

        {/* Step 0: Date list */}
        {step === STEP_DATE && (
          <div className="space-y-2">
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
                  className={`w-full text-left px-4 py-3.5 rounded-xl border transition-all duration-150 active:scale-[0.98] ${
                    isToday
                      ? 'border-[#00FF7F33] bg-[#001a0d]'
                      : 'border-[#222222] bg-[#141414]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`font-semibold text-sm ${isToday ? 'text-[#00FF7F]' : 'text-white'}`}>
                          {day.date}
                        </span>
                        {isToday && (
                          <span className="text-[10px] font-bold uppercase tracking-wider bg-[#00FF7F20] text-[#00FF7F] px-2 py-0.5 rounded-full">
                            Сегодня
                          </span>
                        )}
                      </div>
                      <div className="text-[#888888] text-xs mt-0.5">
                        {day.races?.length || 0} {pluralRaces(day.races?.length || 0)}
                      </div>
                    </div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
          <div className="space-y-2">
            {(selectedDay.races || []).map((race) => (
              <button
                key={race.href}
                onClick={() => handleSelectRace(race)}
                className="w-full text-left px-4 py-3.5 rounded-xl border border-[#222222] bg-[#141414] transition-all duration-150 active:scale-[0.98]"
              >
                <div className="flex items-center justify-between">
                  <div className="text-white font-medium text-sm">{race.number}</div>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
          <div className="space-y-2">
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
                  className={`w-full text-left px-4 py-3.5 rounded-xl border transition-all duration-150 active:scale-[0.98] ${
                    isBest
                      ? 'border-[#00FF7F33] bg-[#001a0d]'
                      : 'border-[#222222] bg-[#141414]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-semibold text-sm">
                          Карт #{cart.id || cart.number}
                        </span>
                        {isBest && (
                          <span className="text-[10px] font-bold uppercase tracking-wider bg-[#00FF7F20] text-[#00FF7F] px-2 py-0.5 rounded-full">
                            Лучший
                          </span>
                        )}
                      </div>
                      {cart.position && (
                        <div className="text-[#888888] text-xs mt-0.5">
                          Позиция {cart.position}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className={`lap-time text-sm font-medium ${isBest ? 'text-[#00FF7F]' : 'text-[#ccc]'}`}>
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
                <p className="text-[#888888]">Сохранение результата...</p>
              </div>
            )}

            {!saving && saveResult?.ok && (
              <div className="w-full">
                <div className="flex justify-center mb-6">
                  <div className="w-20 h-20 rounded-full bg-[#001a0d] border-2 border-[#00FF7F] flex items-center justify-center">
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#00FF7F" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </div>
                </div>

                <h2 className="text-center text-xl font-bold text-white mb-1">Сохранено!</h2>
                <p className="text-center text-[#888888] text-sm mb-1">Результат успешно добавлен</p>
                {!isForSelf && (
                  <p className="text-center text-[#00FF7F] text-xs mb-5">для {forUserName}</p>
                )}
                {isForSelf && <div className="mb-5" />}

                {saveResult.data && (
                  <div className="bg-[#141414] border border-[#222222] rounded-xl p-4 mb-6">
                    <div className="grid grid-cols-2 gap-3">
                      <InfoRow label="Дата" value={saveResult.data.date} />
                      <InfoRow label="Заезд" value={saveResult.data.race_number} />
                      <InfoRow label="Карт" value={`#${saveResult.data.num}`} />
                      <InfoRow label="Позиция" value={`P${saveResult.data.pos}`} highlight="orange" />
                      <InfoRow label="Лучший круг" value={saveResult.data.best_lap} highlight="accent" mono />
                      <InfoRow label="Кругов" value={saveResult.data.laps} />
                    </div>
                  </div>
                )}

                <div className="flex flex-col gap-2">
                  <button
                    onClick={handleReset}
                    className="w-full py-3.5 rounded-xl bg-[#00FF7F] text-black font-bold text-sm"
                  >
                    Добавить ещё
                  </button>
                  {onDone && (
                    <button
                      onClick={onDone}
                      className="w-full py-3.5 rounded-xl border border-[#333] text-[#888] font-medium text-sm"
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
                  <div className="w-20 h-20 rounded-full bg-[#1a0000] border-2 border-[#FF4444] flex items-center justify-center">
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </div>
                </div>

                <h2 className="text-center text-xl font-bold text-white mb-1">Ошибка</h2>
                <p className="text-center text-[#FF4444] text-sm mb-6 break-words">
                  {saveResult.error}
                </p>

                <div className="flex gap-3">
                  <button
                    onClick={() => setStep(STEP_CART)}
                    className="flex-1 py-3.5 rounded-xl border border-[#333] text-[#888] font-medium text-sm"
                  >
                    Назад
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex-1 py-3.5 rounded-xl bg-[#1e1e1e] text-white font-medium text-sm"
                  >
                    Начать заново
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
    <div className="bg-[#1a0000] border border-[#FF444433] rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p className="text-[#FF4444] text-sm">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="self-start text-xs text-[#888] underline">
          Повторить
        </button>
      )}
    </div>
  )
}

function EmptyState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="text-4xl">🏎️</div>
      <p className="text-[#888888] text-sm">{message}</p>
    </div>
  )
}

function InfoRow({ label, value, highlight, mono }) {
  const valClass = [
    'text-sm font-medium',
    mono ? 'lap-time' : '',
    highlight === 'accent' ? 'text-[#00FF7F]' :
    highlight === 'orange' ? 'text-[#FF6B00]' :
    'text-white',
  ].join(' ')
  return (
    <div>
      <div className="text-[#666] text-xs mb-0.5">{label}</div>
      <div className={valClass}>{value ?? '—'}</div>
    </div>
  )
}
