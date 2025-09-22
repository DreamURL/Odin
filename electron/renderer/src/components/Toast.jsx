import React, { createContext, useContext, useMemo, useState } from 'react'

const ToastCtx = createContext(null)

export function useToasts() {
  const ctx = useContext(ToastCtx)
  return ctx
}

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const pushToast = (msg, type='info', actions=[]) => {
    const id = Math.random().toString(36).slice(2)
    setToasts(prev => [...prev, { id, msg, type, actions }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4500)
  }
  const ToastWrap = useMemo(() => () => (
    <div className="toast-wrap">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type==='error'?'error':''}`}>
          <span>{t.msg}</span>
          {t.actions?.map((a,i) => (
            <button key={i} onClick={() => { a.onClick && a.onClick(); setToasts(prev => prev.filter(x => x.id !== t.id)) }}>{a.label}</button>
          ))}
        </div>
      ))}
    </div>
  ), [toasts])
  const value = { pushToast, ToastWrap }
  return (
    <ToastCtx.Provider value={value}>
      {children}
    </ToastCtx.Provider>
  )
}
