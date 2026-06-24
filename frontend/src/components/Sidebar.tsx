'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const nav = [
  { href: '/', label: 'Início', icon: '⚡' },
  { href: '/gerar', label: 'Gerar', icon: '✨' },
  { href: '/cortes', label: 'Cortes', icon: '🔥' },
  { href: '/repostar', label: 'Repostar', icon: '♻️' },
  { href: '/editar', label: 'Editar', icon: '🎬' },
  { href: '/juntar', label: 'Juntar', icon: '🎞️' },
  { href: '/biblioteca', label: 'Biblioteca', icon: '📁' },
  { href: '/arquivos', label: 'Arquivos', icon: '🗄️' },
]

// No mobile mostra só as 5 mais usadas no bottom nav; as demais ficam na sidebar desktop
const mobileNav = nav.filter((n) =>
  ['/', '/gerar', '/cortes', '/biblioteca', '/repostar'].includes(n.href)
)

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <>
      {/* ── Sidebar desktop (md+) ── */}
      <aside className="hidden md:flex w-56 bg-[#111111] border-r border-white/10 flex-col shrink-0">
        <div className="p-6 border-b border-white/10">
          <h1 className="text-xl font-bold tracking-tight text-white">emme</h1>
          <p className="text-xs text-white/40 mt-0.5">Editor de Vídeo</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((item) => {
            const active = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  active
                    ? 'bg-violet-600 text-white'
                    : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* ── Bottom nav mobile (< md) ── */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-[#111111] border-t border-white/10 flex">
        {mobileNav.map((item) => {
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors ${
                active ? 'text-violet-400' : 'text-white/40'
              }`}
            >
              <span className="text-lg leading-none">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>
    </>
  )
}
