'use client'

import { useState, useEffect, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface LibraryItem {
  id: string
  filename: string
  prompt?: string
  created_at: string
}

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

export default function BibliotecaPage() {
  const [tab, setTab] = useState<'images' | 'videos'>('images')
  const [images, setImages] = useState<LibraryItem[]>([])
  const [videos, setVideos] = useState<LibraryItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchLibrary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/library/`)
      const data = await res.json()
      setImages(data.images?.reverse() || [])
      setVideos(data.videos?.reverse() || [])
    } catch {
      // falha silenciosa
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchLibrary() }, [fetchLibrary])

  const deleteImage = async (id: string) => {
    if (!confirm('Excluir esta imagem permanentemente?')) return
    await fetch(`${API}/api/library/images/${id}`, { method: 'DELETE' })
    fetchLibrary()
  }

  const deleteVideo = async (id: string) => {
    if (!confirm('Excluir este vídeo permanentemente?')) return
    await fetch(`${API}/api/library/videos/${id}`, { method: 'DELETE' })
    fetchLibrary()
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Biblioteca</h1>
        <p className="text-white/40 mt-1">Seus arquivos gerados</p>
      </div>

      <div className="flex gap-2 mb-6">
        {(['images', 'videos'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-violet-600 text-white'
                : 'text-white/40 hover:text-white hover:bg-white/5'
            }`}
          >
            {t === 'images' ? `Imagens (${images.length})` : `Vídeos (${videos.length})`}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-white/30 text-center py-20 text-sm">Carregando...</div>
      ) : tab === 'images' ? (
        images.length === 0 ? (
          <div className="text-white/20 text-center py-20 text-sm">
            Nenhuma imagem gerada ainda
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {images.map((img) => (
              <div
                key={img.id}
                className="bg-[#111] border border-white/10 rounded-xl overflow-hidden"
              >
                <img
                  src={`${API}/api/library/images/${img.id}/download`}
                  className="w-full aspect-square object-cover"
                  alt=""
                />
                <div className="p-3">
                  <p className="text-white/30 text-xs">{formatDate(img.created_at)}</p>
                  {img.prompt && (
                    <p className="text-white/50 text-xs mt-1 truncate" title={img.prompt}>
                      {img.prompt}
                    </p>
                  )}
                  <div className="flex gap-2 mt-3">
                    <a
                      href={`${API}/api/library/images/${img.id}/download`}
                      download
                      className="flex-1 bg-white/5 hover:bg-white/10 text-white/60 text-xs py-1.5 rounded-lg text-center transition-colors"
                    >
                      Baixar
                    </a>
                    <button
                      onClick={() => deleteImage(img.id)}
                      className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs py-1.5 rounded-lg transition-colors"
                    >
                      Excluir
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : videos.length === 0 ? (
        <div className="text-white/20 text-center py-20 text-sm">Nenhum vídeo gerado ainda</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map((vid) => (
            <div
              key={vid.id}
              className="bg-[#111] border border-white/10 rounded-xl overflow-hidden"
            >
              <video
                src={`${API}/api/library/videos/${vid.id}/download`}
                className="w-full aspect-video object-cover"
                controls
                muted
              />
              <div className="p-3">
                <p className="text-white/30 text-xs">{formatDate(vid.created_at)}</p>
                <div className="flex gap-2 mt-3">
                  <a
                    href={`${API}/api/library/videos/${vid.id}/download`}
                    download
                    className="flex-1 bg-white/5 hover:bg-white/10 text-white/60 text-xs py-1.5 rounded-lg text-center transition-colors"
                  >
                    Baixar
                  </a>
                  <button
                    onClick={() => deleteVideo(vid.id)}
                    className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs py-1.5 rounded-lg transition-colors"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
