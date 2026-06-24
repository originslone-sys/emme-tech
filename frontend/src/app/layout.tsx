import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import JobsWidget from '@/components/JobsWidget'
import { JobsProvider } from '@/lib/jobs'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Emme — Editor de Vídeo',
  description: 'Melhore a qualidade, corte e junte seus vídeos',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={inter.className}>
        <JobsProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-4 pb-24 md:p-8 md:pb-8">
              {children}
            </main>
          </div>
          <JobsWidget />
        </JobsProvider>
      </body>
    </html>
  )
}
