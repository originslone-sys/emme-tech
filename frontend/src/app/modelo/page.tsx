'use client'

import { useState, useRef } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function ModeloPage() {
  const [references, setReferences] = useState<File[]>([])
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  const handleFiles = (files: FileList | null) => {
    if (!files) return
    const imgs = Array.from(files).filter((f) => f.type.startsWith('image/'))
    setReferences((prev) => [...prev, ...imgs].slice(0, 5))
  }

  const removeReference = (index: number) => {
    setReferences((prev) => prev.filter((_, i) => i !== index))
  }

  const submit = async () => {
    if (references.length === 0) return setError('Adicione pelo menos uma foto de referência')
    if (!prompt.trim()) return setError('Digite um prompt descrevendo a imagem desejada')

    setError('')
    setLoading(true)
    setStatus('Enviando arquivos...')

    const form = new FormData()
    references.forEach((f) => form.append('references', f))
    form.append('prompt', prompt)

    try {
      const res = await fetch(`${API}/api/generate/`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setStatus('Gerando imagem...')
      pollStatus(data.job_id)
    } catch {
      setError('Erro ao enviar. Verifique a conexão e tente novamente.')
      setLoading(false)
    }
  }

  const pollStatus = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/generate/jobs/${id}`)
        const data = await res.json()

        if (data.status === 'COMPLETED') {
          clearInterval(interval)
          setLoading(false)
          setStatus('Imagem gerada! Acesse a Biblioteca para visualizar.')
          setReferences([])
          setPrompt('')
        } else if (data.status === 'FAILED') {
          clearInterval(interval)
          setLoading(false)
          setError(data.error || 'Processamento falhou. Tente novamente.')
          setStatus('')
        }
      } catch {
        // continua tentando
      }
    }, 3000)
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Criar Modelo</h1>
        <p className="text-white/40 mt-1">Gere imagens consistentes a partir de fotos de referência</p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">
            Fotos de referência <span className="text-white/30">(1 a 5 fotos)</span>
          </label>
          <div
            className="border-2 border-dashed border-white/15 rounded-xl p-8 text-center cursor-pointer hover:border-violet-500/40 transition-colors"
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files) }}
          >
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            {references.length > 0 ? (
              <div className="flex flex-wrap gap-3 justify-center">
                {references.map((f, i) => (
                  <div key={i} className="relative group">
                    <img
                      src={URL.createObjectURL(f)}
                      className="w-20 h-20 object-cover rounded-lg"
                      alt=""
                    />
                    <button
                      className="absolute -top-1.5 -right-1.5 bg-red-500 hover:bg-red-600 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => { e.stopPropagation(); removeReference(i) }}
                    >
                      ×
                    </button>
                  </div>
                ))}
                {references.length < 5 && (
                  <div className="w-20 h-20 border-2 border-dashed border-white/15 rounded-lg flex items-center justify-center text-white/30 text-2xl">
                    +
                  </div>
                )}
              </div>
            ) : (
              <>
                <div className="text-5xl mb-3 text-white/15">📸</div>
                <p className="text-white/40 text-sm">Arraste fotos aqui ou clique para selecionar</p>
                <p className="text-white/20 text-xs mt-1">JPG, PNG — até 5 fotos</p>
              </>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/60 mb-2">
            Descrição da imagem desejada
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full bg-[#1a1a1a] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 resize-none focus:outline-none focus:border-violet-500/40 h-28 text-sm"
            placeholder="Ex: foto profissional, vestido vermelho, fundo branco, iluminação suave, alta qualidade..."
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 text-violet-400 text-sm flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
            {status}
          </div>
        )}

        {!loading && status && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-400 text-sm">
            {status}
          </div>
        )}

        <button
          onClick={submit}
          disabled={loading}
          className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-sm"
        >
          {loading ? 'Processando...' : 'Gerar Imagem'}
        </button>
      </div>
    </div>
  )
}
