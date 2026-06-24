'use client'

import { useState, useEffect, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface VideoItem {
  id: string
  filename: string
  label?: string
  created_at: string
  kind?: string
  title?: string
  description?: string
  tags?: string[]
  score?: number
}

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })

export default function BibliotecaPage() {
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)

  const fetchLibrary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/library/`)
      const data = await res.json()
      setVideos((data.videos || []).reverse())
    } catch { /* falha silenciosa */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchLibrary() }, [fetchLibrary])

  const copy = (text: string) => navigator.clipboard?.writeText(text)

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const allSelected = videos.length > 0 && selected.size === videos.length
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(videos.map((v) => v.id)))

  const deleteVideo = async (id: string) => {
    if (!confirm('Excluir este vídeo permanentemente?')) return
    await fetch(`${API}/api/library/videos/${id}`, { method: 'DELETE' })
    setSelected((prev) => { const n = new Set(prev); n.delete(id); return n })
    fetchLibrary()
  }

  const deleteSelected = async () => {
    if (selected.size === 0) return
    if (!confirm(`Excluir ${selected.size} vídeo${selected.size > 1 ? 's' : ''} permanentemente?`)) return
    setDeleting(true)
    await Promise.all(
      Array.from(selected).map((id) => fetch(`${API}/api/library/videos/${id}`, { method: 'DELETE' }))
    )
    setSelected(new Set())
    setDeleting(false)
    fetchLibrary()
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Biblioteca</h1>
          <p className="text-white/40 mt-1">Seus vídeos processados</p>
        </div>
        {videos.length > 0 && (
          <div className="flex items-center gap-2 pt-1 shrink-0">
            <button
              onClick={toggleAll}
              className="text-xs text-white/50 hover:text-white/80 transition-colors whitespace-nowrap"
            >
              {allSelected ? 'Desmarcar todos' : 'Selecionar todos'}
            </button>
            {selected.size > 0 && (
              <button
                onClick={deleteSelected}
                disabled={deleting}
                className="bg-red-500/15 hover:bg-red-500/25 disabled:opacity-40 text-red-400 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap"
              >
                {deleting ? 'Excluindo...' : `Excluir ${selected.size} selecionado${selected.size > 1 ? 's' : ''}`}
              </button>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="text-white/30 text-center py-20 text-sm">Carregando...</div>
      ) : videos.length === 0 ? (
        <div className="text-white/20 text-center py-20 text-sm">Nenhum vídeo processado ainda</div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {videos.map((vid) => {
            const isSelected = selected.has(vid.id)
            return (
              <div
                key={vid.id}
                className={`bg-[#111] border rounded-xl overflow-hidden transition-colors ${
                  isSelected ? 'border-violet-500/60' : 'border-white/10'
                }`}
              >
                <div className="relative">
                  <video
                    src={`${API}/files/videos/${vid.filename}`}
                    className={`w-full bg-black ${vid.kind === 'clip' || vid.kind === 'viral' ? 'aspect-[9/16] object-contain' : 'aspect-video object-cover'}`}
                    controls
                    preload="none"
                  />
                  <button
                    onClick={() => toggleSelect(vid.id)}
                    className={`absolute top-2 left-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                      isSelected
                        ? 'bg-violet-600 border-violet-600 text-white'
                        : 'bg-black/50 border-white/30 hover:border-violet-400'
                    }`}
                    aria-label="Selecionar"
                  >
                    {isSelected && <span className="text-[10px] font-bold">✓</span>}
                  </button>
                </div>
                <div className="p-2 sm:p-3">
                  {vid.kind === 'clip' || vid.kind === 'viral' ? (
                    <>
                      <div className="flex items-start justify-between gap-1">
                        <p className="text-white/80 text-xs sm:text-sm font-semibold line-clamp-2">{vid.title}</p>
                        {typeof vid.score === 'number' && vid.score > 0 && (
                          <span className="shrink-0 bg-violet-500/20 text-violet-300 text-[10px] px-1.5 py-0.5 rounded-full">🔥 {vid.score}</span>
                        )}
                      </div>
                      {vid.description && (
                        <div className="mt-1.5">
                          <p className="text-white/50 text-[10px] sm:text-xs whitespace-pre-wrap line-clamp-3">{vid.description}</p>
                          <button onClick={() => copy(vid.description!)} className="text-violet-400 hover:text-violet-300 text-[10px] sm:text-xs mt-1">
                            copiar legenda
                          </button>
                        </div>
                      )}
                      {vid.tags && vid.tags.length > 0 && (
                        <div className="hidden sm:flex flex-wrap gap-1 mt-1.5">
                          {vid.tags.map((t, i) => (
                            <span key={i} className="bg-white/5 text-white/40 text-[10px] px-1.5 py-0.5 rounded">#{t.replace(/^#/, '')}</span>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    vid.label && <p className="text-white/70 text-xs sm:text-sm font-medium truncate">{vid.label}</p>
                  )}
                  <p className="text-white/30 text-[10px] sm:text-xs mt-1.5">{formatDate(vid.created_at)}</p>
                  <div className="flex gap-1.5 mt-2">
                    <a
                      href={`${API}/api/library/videos/${vid.id}/download`}
                      download
                      className="flex-1 bg-white/5 hover:bg-white/10 text-white/60 text-[10px] sm:text-xs py-1.5 rounded-lg text-center transition-colors"
                    >
                      Baixar
                    </a>
                    <button
                      onClick={() => deleteVideo(vid.id)}
                      className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-[10px] sm:text-xs py-1.5 rounded-lg transition-colors"
                    >
                      Excluir
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
