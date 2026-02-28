'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Building2,
  Users,
  UserCheck,
  FileText,
  Receipt,
  Wallet,
  Settings,
  Shield,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Home,
  BarChart3,
  Menu,
  X,
} from 'lucide-react'
import { signOut, useSession } from 'next-auth/react'
import { cn } from '@/lib/utils'

const clientNavItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/proprietarios', label: 'Proprietários', icon: Users },
  { href: '/imoveis', label: 'Imóveis', icon: Building2 },
  { href: '/inquilinos', label: 'Inquilinos', icon: UserCheck },
  { href: '/contratos', label: 'Contratos', icon: FileText },
  { href: '/cobrancas', label: 'Cobranças', icon: Receipt },
  { href: '/carteira', label: 'Carteira', icon: Wallet },
  { href: '/configuracoes', label: 'Configurações', icon: Settings },
]

const adminNavItems = [
  { href: '/admin/dashboard', label: 'Painel Admin', icon: Shield },
  { href: '/admin/users', label: 'Usuários', icon: Users },
  { href: '/admin/config', label: 'Configurações', icon: Settings },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = usePathname()
  const { data: session } = useSession()

  const isAdmin = (session?.user as any)?.role === 'ADMIN'

  const NavLink = ({ item }: { item: typeof clientNavItems[0] }) => {
    const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
    const Icon = item.icon
    return (
      <Link
        href={item.href}
        className={cn(
          isActive ? 'sidebar-link-active' : 'sidebar-link'
        )}
        onClick={() => setMobileOpen(false)}
      >
        <Icon size={20} />
        {!collapsed && <span>{item.label}</span>}
      </Link>
    )
  }

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-700/50">
        <div className="w-9 h-9 bg-primary-500 rounded-lg flex items-center justify-center flex-shrink-0">
          <Home size={20} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <h1 className="text-white font-bold text-lg leading-tight">AluguelPro</h1>
            <p className="text-sidebar-text text-xs">Gestão de Aluguéis</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {!collapsed && (
          <p className="px-3 text-xs font-semibold text-sidebar-text/60 uppercase tracking-wider mb-2">
            Menu Principal
          </p>
        )}
        {clientNavItems.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}

        {isAdmin && (
          <>
            {!collapsed && (
              <p className="px-3 pt-4 text-xs font-semibold text-sidebar-text/60 uppercase tracking-wider mb-2">
                Administração
              </p>
            )}
            {adminNavItems.map((item) => (
              <NavLink key={item.href} item={item} />
            ))}
          </>
        )}
      </nav>

      {/* User & Logout */}
      <div className="px-3 py-4 border-t border-gray-700/50">
        {!collapsed && session?.user && (
          <div className="px-3 mb-3">
            <p className="text-white text-sm font-medium truncate">{session.user.name}</p>
            <p className="text-sidebar-text text-xs truncate">{session.user.email}</p>
          </div>
        )}
        <button
          onClick={() => signOut({ callbackUrl: '/login' })}
          className="sidebar-link w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
        >
          <LogOut size={20} />
          {!collapsed && <span>Sair</span>}
        </button>
      </div>

      {/* Collapse toggle (desktop) */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="hidden lg:flex items-center justify-center py-3 border-t border-gray-700/50
        text-sidebar-text hover:text-white transition-colors"
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </>
  )

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-sidebar-bg rounded-lg text-white shadow-lg"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          'lg:hidden fixed inset-y-0 left-0 z-40 w-64 bg-sidebar-bg flex flex-col transition-transform duration-300',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden lg:flex flex-col bg-sidebar-bg h-screen sticky top-0 transition-all duration-300',
          collapsed ? 'w-[72px]' : 'w-64'
        )}
      >
        {sidebarContent}
      </aside>
    </>
  )
}
