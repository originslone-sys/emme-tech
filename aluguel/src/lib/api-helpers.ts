import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from './auth'

export async function getSessionUser() {
  const session = await getServerSession(authOptions)
  if (!session?.user) return null
  return session.user as { id: string; name: string; email: string; role: string }
}

export function unauthorized() {
  return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })
}

export function forbidden() {
  return NextResponse.json({ error: 'Acesso negado' }, { status: 403 })
}

export function notFound(entity = 'Registro') {
  return NextResponse.json({ error: `${entity} não encontrado` }, { status: 404 })
}

export function badRequest(message: string) {
  return NextResponse.json({ error: message }, { status: 400 })
}

export function serverError(error: unknown) {
  console.error('Server error:', error)
  return NextResponse.json({ error: 'Erro interno do servidor' }, { status: 500 })
}
