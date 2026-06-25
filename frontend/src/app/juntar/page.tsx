'use client'

import { useState, useEffect, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface GeneratedImage {
  id: string
  url: string
}

interface Character {
  name: string
  display_summary: string
  reference_url: string
  pending_selection: boolean
  generated_image_ids: string[]
}

const FIELD_LABELS: Record<string, string> = {
  scenario: 'Cenário',
  outfit: 'Roupa',
  pose: 'Pose',
  expression: 'Expressão',
  lighting: 'Iluminação',
}

const SCENE_PLACEHOLDERS: Record<string, string> = {
  scenario: 'ex: escritório moderno, praia ao pôr do sol, estúdio de podcast',
  outfit: 'ex: blazer azul marinho, camiseta branca casual, vestido vermelho',
  pose: 'ex: sentada olhando para câmera, em pé com braços cruzados',
  expression: 'ex: sorriso confiante, expressão séria, rindo',
  lighting: 'ex: luz natural de janela, iluminação de estúdio, luz dourada',
}

export default function GenerativaPage() {
  const [character, setCharacter] = useState<Character | null>(null)
  const [loadingChar, setLoadingChar] = useState(true)

  // Estado: criação do personagem
  const [creating, setCreating] = useState(false)
  const [pendingImages, setPendingImages] = useState<GeneratedImage[]>([])
  const [fields, setFields] = useState({
    name: '', sex: 'feminino', age: '', ethnicity: '',
    hair: '', eyes: '', traits: '', tone: '',
  })

  // Estado: geração de cenas
  const [sceneFields, setSceneFields] = useState({
    scenario: '', outfit: '', pose: '', expression: '', lighting: '',
  })
  const [generatingScene, setGeneratingScene] = useState(false)
  const [sceneImages, setSceneImages] = useState<GeneratedImage[]>([])
  const [error, setError] = useState('')

  const fetchCharacter = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/generative/character`)
      const data = await res.json()
      setCharacter(data.character || null)
      if (data.character?.pending_selection) {
        // Busca as imagens de seleção pendentes
        const db = await fetch(`${API}/api/library/`).then(r => r.json())
        const ids = data.character.generated_image_ids || []
        const imgs = (db.images || [])
          .filter((i: {id: string; filename: string}) => ids.includes(i.id))
          .map((i: {id: string; filename: string}) => ({
            id: i.id,
            url: `${API}/files/images/${i.filename}`,
          }))
        setPendingImages(imgs)
      }
    } catch { /* silencioso */ } finally {
      setLoadingChar(false)
    }
  }, [])

  useEffect(() => { fetchCharacter() }, [fetchCharacter])

  const createCharacter = async () => {
    if (!fields.name || !fields.age || !fields.ethnicity || !fields.hair || !fields.eyes) {
      return setError('Preencha pelo menos: nome, idade, etnia, cabelo e olhos.')
    }
    setError('')
    setCreating(true)
    try {
      const res = await fetch(`${API}/api/generative/character`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || `Erro ${res.status}`)
      }
      const data = await res.json()
      setPendingImages(data.images.map((img: GeneratedImage) => ({
        id: img.id,
        url: `${API}${img.url}`,
      })))
      fetchCharacter()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao criar personagem')
    } finally {
      setCreating(false)
    }
  }

  const confirmImage = async (imageId: string) => {
    try {
      await fetch(`${API}/api/generative/character/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: imageId }),
      })
      setPendingImages([])
      fetchCharacter()
    } catch {
      setError('Erro ao confirmar imagem.')
    }
  }

  const resetCharacter = async () => {
    if (!confirm('Excluir o personagem e todas as imagens geradas?')) return
    await fetch(`${API}/api/generative/character/reset`, { method: 'POST' })
    setCharacter(null)
    setPendingImages([])
    setSceneImages([])
  }

  const generateScene = async () => {
    if (!sceneFields.scenario && !sceneFields.outfit && !sceneFields.pose) {
      return setError('Descreva pelo menos o cenário, roupa ou pose.')
    }
    setError('')
    setGeneratingScene(true)
    try {
      const res = await fetch(`${API}/api/generative/scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneFields),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || `Erro ${res.status}`)
      }
      const data = await res.json()
      setSceneImages(prev => [
        ...data.images.map((img: GeneratedImage) => ({
          id: img.id,
          url: `${API}${img.url}`,
        })),
        ...prev,
      ])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao gerar cena')
    } finally {
      setGeneratingScene(false)
    }
  }

  const setAsReference = async (imageId: string) => {
    await fetch(`${API}/api/generative/character/reference`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_id: imageId }),
    })
    fetchCharacter()
  }

  if (loadingChar) {
    return <div className="text-white/30 text-center py-20 text-sm">Carregando...</div>
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">IA Generativa</h1>
        <p className="text-white/40 mt-1">Crie imagens com um personagem consistente gerado por IA</p>
      </div>

      {error && (
        <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* ── Sem personagem: formulário de criação ── */}
      {!character && pendingImages.length === 0 && (
        <div className="bg-[#111] border border-white/10 rounded-xl p-6 space-y-4">
          <h2 className="text-white font-semibold text-lg">Criar personagem</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-white/50 text-xs mb-1 block">Nome do personagem</label>
              <input
                value={fields.name}
                onChange={e => setFields(f => ({ ...f, name: e.target.value }))}
                placeholder="ex: Ana Souza"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50"
              />
            </div>

            <div>
              <label className="text-white/50 text-xs mb-1 block">Sexo</label>
              <div className="flex gap-2">
                {['feminino', 'masculino'].map(s => (
                  <button key={s} onClick={() => setFields(f => ({ ...f, sex: s }))}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                      fields.sex === s ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'
                    }`}>{s}</button>
                ))}
              </div>
            </div>

            {[
              { key: 'age', label: 'Idade', placeholder: 'ex: 30 anos' },
              { key: 'ethnicity', label: 'Etnia / tom de pele', placeholder: 'ex: brasileira, pele morena clara' },
              { key: 'hair', label: 'Cabelo (cor + estilo)', placeholder: 'ex: cabelo preto liso na altura dos ombros' },
              { key: 'eyes', label: 'Olhos (cor + formato)', placeholder: 'ex: olhos castanhos amendoados' },
              { key: 'traits', label: 'Características marcantes (opcional)', placeholder: 'ex: sorriso discreto, sardas leves' },
              { key: 'tone', label: 'Tom visual (opcional)', placeholder: 'ex: elegante e profissional, jovem e descontraído' },
            ].map(({ key, label, placeholder }) => (
              <div key={key} className="sm:col-span-1">
                <label className="text-white/50 text-xs mb-1 block">{label}</label>
                <input
                  value={fields[key as keyof typeof fields]}
                  onChange={e => setFields(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50"
                />
              </div>
            ))}
          </div>

          <button
            onClick={createCharacter}
            disabled={creating}
            className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors"
          >
            {creating ? 'Gerando personagem... (pode levar ~30s)' : 'Criar personagem'}
          </button>
        </div>
      )}

      {/* ── Seleção da imagem de referência (após criação) ── */}
      {pendingImages.length > 0 && (
        <div className="space-y-4">
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3 text-amber-300 text-sm">
            Escolha a melhor imagem — ela será a referência mestre para manter o rosto consistente nas cenas.
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {pendingImages.map(img => (
              <div key={img.id} className="group relative rounded-xl overflow-hidden border border-white/10 bg-[#111]">
                <img src={img.url} alt="" className="w-full aspect-square object-cover" />
                <button
                  onClick={() => confirmImage(img.id)}
                  className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white font-semibold text-sm"
                >
                  Usar esta
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Personagem confirmado: geração de cenas ── */}
      {character && !character.pending_selection && (
        <div className="space-y-6">
          {/* Card do personagem */}
          <div className="bg-[#111] border border-white/10 rounded-xl p-4 flex items-center gap-4">
            {character.reference_url && (
              <img
                src={`${API}${character.reference_url}`}
                alt={character.name}
                className="w-16 h-16 rounded-full object-cover border-2 border-violet-500/40 shrink-0"
              />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white font-semibold">{character.name}</p>
              <p className="text-white/40 text-xs mt-0.5 line-clamp-2">{character.display_summary}</p>
            </div>
            <button
              onClick={resetCharacter}
              className="text-xs text-red-400 hover:text-red-300 transition-colors shrink-0"
            >
              Resetar
            </button>
          </div>

          {/* Campos da cena */}
          <div className="bg-[#111] border border-white/10 rounded-xl p-5 space-y-4">
            <h2 className="text-white font-semibold">Nova cena</h2>
            {(Object.keys(sceneFields) as Array<keyof typeof sceneFields>).map(key => (
              <div key={key}>
                <label className="text-white/50 text-xs mb-1 block">{FIELD_LABELS[key]}</label>
                <input
                  value={sceneFields[key]}
                  onChange={e => setSceneFields(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={SCENE_PLACEHOLDERS[key]}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-violet-500/50"
                />
              </div>
            ))}
            <button
              onClick={generateScene}
              disabled={generatingScene}
              className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors"
            >
              {generatingScene ? 'Gerando imagens... (~30s)' : 'Gerar imagens da cena'}
            </button>
          </div>

          {/* Grade de imagens geradas */}
          {sceneImages.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-white font-semibold">Imagens geradas</h2>
              <div className="grid grid-cols-2 gap-3">
                {sceneImages.map(img => (
                  <div key={img.id} className="group relative rounded-xl overflow-hidden border border-white/10 bg-[#111]">
                    <img src={img.url} alt="" className="w-full aspect-[9/16] object-cover" />
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                      <a
                        href={img.url}
                        download
                        className="flex-1 bg-white/10 hover:bg-white/20 text-white text-xs py-1.5 rounded-lg text-center transition-colors"
                      >
                        Baixar
                      </a>
                      <button
                        onClick={() => setAsReference(img.id)}
                        className="flex-1 bg-violet-600/80 hover:bg-violet-600 text-white text-xs py-1.5 rounded-lg transition-colors"
                      >
                        Usar como referência
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
