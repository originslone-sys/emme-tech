'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const nav = [
  { href: '/', label: 'Início', icon: '⚡' },
  { href: '/melhorar', label: 'Melhorar Qualidade', icon: '✨' },
  { href: '/cortar', label: 'Cortar', icon: '✂️' },
  { href: '/juntar', label: 'Juntar Vídeos', icon: '🎞️' },
  { href: '/ajustar', label: 'Iluminação', icon: '💡' },
  { href: '/biblioteca', label: 'Biblioteca', icon: '📁' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-56 bg-[#111111] border-r border-white/10 flex flex-col shrink-0">
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
  )
}
