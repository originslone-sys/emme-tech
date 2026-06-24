'use client'

import Link from 'next/link'
import { useJobs, type Job } from '@/lib/jobs'

const STAGE_LABEL: Record<string, string> = {
  starting: 'Iniciando',
  scripting: 'Roteiro',
  narrating: 'Narração',
  music: 'Trilha sonora',
  fetching: 'Buscando cenas',
  downloading: 'Baixando',
  transcribing: 'Transcrevendo',
  analyzing: 'Analisando',
  rendering: 'Renderizando',
}

function statusLine(j: Job): string {
  if (j.status === 'COMPLETED') return 'Concluído'
  if (j.status === 'FAILED') return j.error || 'Falhou'
  const base = STAGE_LABEL[j.stage || ''] || 'Processando'
  if (j.stage === 'rendering' && j.percent) return `${base} ${j.percent}%`
  if (j.total) return `${base} (${j.done || 0}/${j.total})`
  return `${base}...`
}

export default function JobsWidget() {
  const { jobs, dismiss } = useJobs()

  // mostra os que estão processando + os concluídos/falhados ainda não dispensados
  const visible = jobs.filter((j) => j.status === 'processing' || !j.seen)
  if (visible.length === 0) return null

  return (
    <div className="fixed right-3 bottom-20 md:bottom-4 z-[60] w-[min(20rem,calc(100vw-1.5rem))] space-y-2">
      {visible.map((j) => {
        const processing = j.status === 'processing'
        const failed = j.status === 'FAILED'
        return (
          <div key={j.id}
            className={`rounded-xl border px-4 py-3 shadow-lg backdrop-blur bg-[#111]/95 ${
              failed ? 'border-red-500/30' : processing ? 'border-violet-500/30' : 'border-green-500/30'
            }`}>
            <div className="flex items-start gap-3">
              {processing ? (
                <div className="w-4 h-4 mt-0.5 border-2 border-violet-400 border-t-transparent rounded-full animate-spin shrink-0" />
              ) : (
                <span className={`mt-0.5 shrink-0 ${failed ? 'text-red-400' : 'text-green-400'}`}>
                  {failed ? '✕' : '✓'}
                </span>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-medium truncate">{j.label || 'Tarefa'}</p>
                <p className={`text-xs mt-0.5 ${failed ? 'text-red-300/80' : 'text-white/50'}`}>
                  {statusLine(j)}
                </p>
                {j.status === 'COMPLETED' && (
                  <Link href="/biblioteca" onClick={() => dismiss(j.id)}
                    className="inline-block mt-1.5 text-violet-400 hover:text-violet-300 text-xs font-medium">
                    Ver na Biblioteca →
                  </Link>
                )}
              </div>
              {!processing && (
                <button onClick={() => dismiss(j.id)}
                  className="text-white/30 hover:text-white/70 text-sm shrink-0 leading-none">✕</button>
              )}
            </div>
            {processing && j.stage === 'rendering' && (j.percent || 0) > 0 && (
              <div className="w-full bg-white/10 rounded-full h-1 mt-2 overflow-hidden">
                <div className="bg-violet-500 h-full transition-all duration-500" style={{ width: `${j.percent}%` }} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
