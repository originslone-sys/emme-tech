'use client'

import { useState, useEffect, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface FileItem {
  name: string
  size: number
}

interface StorageData {
  dirs: Record<string, FileItem[]>
  total: number
}

const DIR_LABELS: Record<string, string> = {
  uploads: 'Uploads (temporários: vídeos de origem, áudio, chunks)',
  videos: 'Vídeos (cortes e vídeos processados)',
  images: 'Imagens',
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

export default function ArquivosPage() {
  const [data, setData] = useState<StorageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)

  const fetchStorage = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/library/storage`)
      setData(await res.json())
    } catch { /* falha silenciosa */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchStorage() }, [fetchStorage])

  const deleteFile = async (category: string, name: string) => {
    if (!confirm(`Excluir "${name}" permanentemente?`)) return
    const key = `${category}/${name}`
    setBusy(key)
    await fetch(`${API}/api/library/storage/${category}/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    })
    setBusy(null)
    fetchStorage()
  }

  const deleteDir = async (category: string, files: FileItem[]) => {
    if (files.length === 0) return
    if (!confirm(`Excluir TODOS os ${files.length} arquivos de "${category}" permanentemente?`)) return
    setBusy(category)
    await Promise.all(
      files.map((f) =>
        fetch(`${API}/api/library/storage/${category}/${encodeURIComponent(f.name)}`, {
          method: 'DELETE',
        })
      )
    )
    setBusy(null)
    fetchStorage()
  }

  const dirSize = (files: FileItem[]) => files.reduce((s, f) => s + f.size, 0)

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Arquivos</h1>
          <p className="text-white/40 mt-1">
            Gerencie o disco do servidor manualmente
            {data && <span className="ml-2 text-white/60">· Total: {formatSize(data.total)}</span>}
          </p>
        </div>
        <button
          onClick={fetchStorage}
          className="text-xs text-white/50 hover:text-white/80 transition-colors pt-1 shrink-0"
        >
          Atualizar
        </button>
      </div>

      {loading ? (
        <div className="text-white/30 text-center py-20 text-sm">Carregando...</div>
      ) : !data ? (
        <div className="text-white/20 text-center py-20 text-sm">Não foi possível carregar</div>
      ) : (
        <div className="space-y-6">
          {Object.entries(data.dirs).map(([category, files]) => (
            <div key={category} className="bg-[#111] border border-white/10 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between gap-3 p-3 border-b border-white/10">
                <div className="min-w-0">
                  <p className="text-white/80 text-sm font-semibold">{DIR_LABELS[category] || category}</p>
                  <p className="text-white/30 text-xs mt-0.5">
                    {files.length} arquivo{files.length !== 1 ? 's' : ''} · {formatSize(dirSize(files))}
                  </p>
                </div>
                {files.length > 0 && (
                  <button
                    onClick={() => deleteDir(category, files)}
                    disabled={busy === category}
                    className="bg-red-500/15 hover:bg-red-500/25 disabled:opacity-40 text-red-400 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    {busy === category ? 'Excluindo...' : 'Limpar tudo'}
                  </button>
                )}
              </div>

              {files.length === 0 ? (
                <p className="text-white/20 text-xs text-center py-6">Vazio</p>
              ) : (
                <ul className="divide-y divide-white/5">
                  {files.map((f) => {
                    const key = `${category}/${f.name}`
                    return (
                      <li key={f.name} className="flex items-center justify-between gap-3 px-3 py-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-white/70 text-xs font-mono truncate">{f.name}</p>
                        </div>
                        <span className="text-white/40 text-xs shrink-0 tabular-nums">{formatSize(f.size)}</span>
                        <button
                          onClick={() => deleteFile(category, f.name)}
                          disabled={busy === key}
                          className="bg-red-500/10 hover:bg-red-500/20 disabled:opacity-40 text-red-400 text-xs px-2.5 py-1 rounded-lg transition-colors shrink-0"
                        >
                          {busy === key ? '...' : 'Excluir'}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
