'use client'

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''
const STORAGE_KEY = 'emme:jobs'
const POLL_MS = 3000
const MAX_AGE_MS = 60 * 60 * 1000 // 1h: jobs mais antigos param de ser monitorados

export type JobType = 'viral' | 'clips'
export type JobStatus = 'processing' | 'COMPLETED' | 'FAILED'

export type Job = {
  id: string
  type: JobType
  label: string
  startedAt: number
  status: JobStatus
  stage?: string
  percent?: number
  done?: number
  total?: number
  error?: string
  warnings?: string[]
  resultIds?: string[]
  seen?: boolean // o usuário já viu/concluiu este job
}

type Ctx = {
  jobs: Job[]
  addJob: (id: string, type: JobType, label: string) => void
  dismiss: (id: string) => void
  latest: (type: JobType) => Job | undefined
}

const JobsContext = createContext<Ctx | null>(null)

const ENDPOINT: Record<JobType, string> = {
  viral: '/api/viral/jobs',
  clips: '/api/clips/jobs',
}

function load(): Job[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function save(jobs: Job[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs))
  } catch { /* ignora */ }
}

export function JobsProvider({ children }: { children: React.ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const jobsRef = useRef<Job[]>([])

  // estado <-> ref <-> localStorage sempre sincronizados
  const commit = useCallback((next: Job[]) => {
    jobsRef.current = next
    setJobs(next)
    save(next)
  }, [])

  useEffect(() => {
    const loaded = load()
    jobsRef.current = loaded
    setJobs(loaded)
  }, [])

  const addJob = useCallback((id: string, type: JobType, label: string) => {
    const job: Job = { id, type, label, startedAt: Date.now(), status: 'processing' }
    commit([job, ...jobsRef.current.filter((j) => j.id !== id)].slice(0, 30))
  }, [commit])

  const dismiss = useCallback((id: string) => {
    commit(jobsRef.current.map((j) => (j.id === id ? { ...j, seen: true } : j)))
  }, [commit])

  const latest = useCallback(
    (type: JobType) => jobsRef.current.find((j) => j.type === type),
    [],
  )

  // poller global: roda enquanto houver jobs em processamento
  useEffect(() => {
    const tick = async () => {
      const active = jobsRef.current.filter((j) => j.status === 'processing')
      if (active.length === 0) return

      const updates = await Promise.all(active.map(async (j) => {
        // jobs muito antigos: para de monitorar
        if (Date.now() - j.startedAt > MAX_AGE_MS) {
          return { ...j, status: 'FAILED' as JobStatus, error: 'Tempo limite excedido' }
        }
        try {
          const res = await fetch(`${API}${ENDPOINT[j.type]}/${j.id}`)
          if (res.status === 404) {
            return { ...j, status: 'FAILED' as JobStatus, error: 'Tarefa não encontrada no servidor' }
          }
          if (!res.ok) return j
          const d = await res.json()
          const next: Job = {
            ...j,
            stage: d.stage,
            percent: d.percent ?? j.percent,
            done: d.done ?? j.done,
            total: d.total ?? j.total,
          }
          if (d.status === 'COMPLETED') {
            next.status = 'COMPLETED'
            next.warnings = d.warnings || []
            next.resultIds = j.type === 'viral'
              ? (d.video_id ? [d.video_id] : [])
              : (d.clip_ids || [])
          } else if (d.status === 'FAILED') {
            next.status = 'FAILED'
            next.error = d.error || 'Processamento falhou'
          }
          return next
        } catch {
          return j // erro de rede: tenta de novo no próximo tick
        }
      }))

      const map = new Map(updates.map((u) => [u.id, u]))
      commit(jobsRef.current.map((j) => map.get(j.id) || j))
    }

    const interval = setInterval(tick, POLL_MS)
    tick()
    return () => clearInterval(interval)
  }, [commit])

  return (
    <JobsContext.Provider value={{ jobs, addJob, dismiss, latest }}>
      {children}
    </JobsContext.Provider>
  )
}

export function useJobs() {
  const ctx = useContext(JobsContext)
  if (!ctx) throw new Error('useJobs precisa estar dentro de JobsProvider')
  return ctx
}

/** Retorna o job mais recente de um tipo (ativo ou concluído ainda não visto). */
export function useLatestJob(type: JobType): Job | undefined {
  const { jobs } = useJobs()
  return jobs.find((j) => j.type === type)
}
