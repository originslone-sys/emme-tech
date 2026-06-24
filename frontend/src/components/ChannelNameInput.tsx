'use client'

import { useEffect, useState } from 'react'

const STORAGE_KEY = 'emme:channel_names'
const MAX_NAMES = 20
const DATALIST_ID = 'channel-names-list'

function readNames(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr.filter((n) => typeof n === 'string') : []
  } catch {
    return []
  }
}

/** Guarda um nome de canal usado (mais recente primeiro, sem duplicar). */
export function rememberChannelName(name: string) {
  const trimmed = name.trim()
  if (!trimmed) return
  const existing = readNames().filter((n) => n.toLowerCase() !== trimmed.toLowerCase())
  const next = [trimmed, ...existing].slice(0, MAX_NAMES)
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch { /* ignora cota cheia */ }
}

type Props = {
  value: string
  onChange: (v: string) => void
}

export default function ChannelNameInput({ value, onChange }: Props) {
  const [names, setNames] = useState<string[]>([])

  useEffect(() => { setNames(readNames()) }, [])

  const clearNames = () => {
    try { window.localStorage.removeItem(STORAGE_KEY) } catch { /* noop */ }
    setNames([])
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-white/60">
          Nome do canal
          <span className="text-white/30 font-normal ml-1">(marca d&apos;água no centro)</span>
        </label>
        {names.length > 0 && (
          <button type="button" onClick={clearNames}
            className="text-white/30 hover:text-red-400 text-xs transition-colors">
            limpar salvos ({names.length})
          </button>
        )}
      </div>
      <input
        type="text"
        list={DATALIST_ID}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={40}
        placeholder="Ex: @seucanal · deixe vazio para não exibir"
        className="w-full bg-[#111] border border-white/15 rounded-xl px-4 py-2.5 text-white text-sm focus:border-violet-500/50 outline-none"
      />
      <datalist id={DATALIST_ID}>
        {names.map((n) => <option key={n} value={n} />)}
      </datalist>
    </div>
  )
}
