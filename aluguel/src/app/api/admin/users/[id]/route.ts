import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, forbidden, notFound, serverError } from '@/lib/api-helpers'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()
    if (user.role !== 'ADMIN') return forbidden()

    const targetUser = await prisma.user.findUnique({
      where: { id: params.id },
      select: {
        id: true, name: true, email: true, phone: true, cpfCnpj: true,
        role: true, isActive: true, createdAt: true,
        properties: true,
        contracts: { include: { property: true, tenant: true } },
        wallet: true,
        withdrawals: { orderBy: { createdAt: 'desc' } },
      },
    })

    if (!targetUser) return notFound('Usuário')
    return NextResponse.json(targetUser)
  } catch (error) {
    return serverError(error)
  }
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()
    if (user.role !== 'ADMIN') return forbidden()

    const body = await request.json()
    const updatedUser = await prisma.user.update({
      where: { id: params.id },
      data: {
        name: body.name,
        email: body.email,
        phone: body.phone,
        role: body.role,
        isActive: body.isActive,
      },
      select: { id: true, name: true, email: true, role: true, isActive: true },
    })

    return NextResponse.json(updatedUser)
  } catch (error) {
    return serverError(error)
  }
}
