import { createContext, useContext, useEffect, useState } from 'react'
import { t as translate } from './translations'

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('safepass_lang') || 'en')

  useEffect(() => {
    localStorage.setItem('safepass_lang', lang)
    document.documentElement.lang = lang
  }, [lang])

  const t = (key) => translate(key, lang)

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
