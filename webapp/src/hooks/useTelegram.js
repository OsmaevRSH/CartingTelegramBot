import { useEffect, useState } from 'react'

export function useTelegram() {
  const [tg, setTg] = useState(null)
  const [user, setUser] = useState(null)
  const [userId, setUserId] = useState(null)
  const [userName, setUserName] = useState('Пользователь')
  const [userUsername, setUserUsername] = useState(null)
  const [userPhotoUrl, setUserPhotoUrl] = useState(null)
  const [isDevMode, setIsDevMode] = useState(false)

  useEffect(() => {
    const webapp = window.Telegram?.WebApp

    if (webapp && webapp.initData) {
      webapp.ready()
      webapp.expand()

      const tgUser = webapp.initDataUnsafe?.user
      setTg(webapp)
      setUser(tgUser || null)
      setUserId(tgUser?.id ?? null)
      setUserName(
        tgUser?.first_name || tgUser?.username || 'Пользователь'
      )
      setUserUsername(tgUser?.username ?? null)
      setUserPhotoUrl(tgUser?.photo_url ?? null)
      setIsDevMode(false)
    } else {
      // Dev mode: no real Telegram context
      setTg(null)
      setUser(null)
      setUserId(0)
      setUserName('Dev User')
      setUserUsername(null)
      setUserPhotoUrl(null)
      setIsDevMode(true)
    }
  }, [])

  return { tg, user, userId, userName, userUsername, userPhotoUrl, isDevMode }
}
