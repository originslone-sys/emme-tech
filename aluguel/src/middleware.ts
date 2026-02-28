import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token
    const path = req.nextUrl.pathname

    // Admin-only routes
    if (path.startsWith('/admin') && token?.role !== 'ADMIN') {
      return NextResponse.redirect(new URL('/dashboard', req.url))
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
  }
)

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/proprietarios/:path*',
    '/imoveis/:path*',
    '/inquilinos/:path*',
    '/contratos/:path*',
    '/cobrancas/:path*',
    '/carteira/:path*',
    '/configuracoes/:path*',
    '/admin/:path*',
  ],
}
