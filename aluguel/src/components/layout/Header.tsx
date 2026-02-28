'use client'

import { Bell, Search, User } from 'lucide-react'
import { useSession } from 'next-auth/react'

interface HeaderProps {
  title?: string
}

export default function Header({ title }: HeaderProps) {
  const { data: session } = useSession()

  return (
    <header className="bg-white border-b border-gray-200 px-4 lg:px-8 py-4">
      <div className="flex items-center justify-between">
        <div className="lg:pl-0 pl-12">
          {title && <h2 className="text-xl font-bold text-gray-900">{title}</h2>}
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="hidden md:flex items-center bg-gray-100 rounded-lg px-3 py-2 gap-2">
            <Search size={16} className="text-gray-400" />
            <input
              type="text"
              placeholder="Buscar..."
              className="bg-transparent border-none text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none w-48"
            />
          </div>

          {/* Notifications */}
          <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
            <Bell size={20} />
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
              3
            </span>
          </button>

          {/* User avatar */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
              <User size={16} className="text-primary-600" />
            </div>
            <span className="hidden md:block text-sm font-medium text-gray-700">
              {session?.user?.name?.split(' ')[0]}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
