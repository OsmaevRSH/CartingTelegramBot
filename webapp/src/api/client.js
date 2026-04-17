const BASE_URL = (import.meta.env.VITE_API_URL || '') + '/api'

let _userId = null

export function setUserId(id) {
  _userId = id
}

function getHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  if (_userId !== null && _userId !== undefined) {
    headers['X-User-ID'] = String(_userId)
  }
  return headers
}

async function request(path, options = {}) {
  const url = BASE_URL + path
  const res = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...(options.headers || {}),
    },
  })

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      errMsg = body.detail || body.message || errMsg
    } catch (_) {}
    throw new Error(errMsg)
  }

  return res.json()
}

// Archive
export function fetchArchive() {
  return request('/archive')
}

// Race carts (lightweight)
export function fetchRaceCarts(href) {
  return request(`/races?href=${encodeURIComponent(href)}`)
}

// Full race info
export function fetchFullRace(href) {
  return request(`/races/full?href=${encodeURIComponent(href)}`)
}

// User stats
export function fetchStats(userId) {
  return request(`/stats/${userId}`)
}

// Save race result
export function saveStats(payload) {
  return request('/stats', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// Delete race result
export function deleteStats(userId, date, raceNumber, num) {
  return request(
    `/stats/${userId}/${encodeURIComponent(date)}/${encodeURIComponent(raceNumber)}/${encodeURIComponent(num)}`,
    { method: 'DELETE' }
  )
}

// Leaderboard (all time)
export function fetchLeaderboard() {
  return request('/leaderboard')
}

// Leaderboard (today)
export function fetchLeaderboardToday(date) {
  return request(`/leaderboard/today?date=${encodeURIComponent(date)}`)
}
