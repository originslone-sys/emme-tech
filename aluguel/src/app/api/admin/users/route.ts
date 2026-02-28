import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, forbidden, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()
    if (user.role !== 'ADMIN') return forbidden()

    const users = await prisma.user.findMany({
      orderBy: { createdAt: 'desc' },
      select: {
        id: true, name: true, email: true, phone: true, cpfCnpj: true,
        role: true, isActive: true, createdAt: true,
        _count: { select: { properties: true, contracts: true, charges: true } },
        wallet: { select: { balance: true, totalReceived: true, totalFees: true } },
      },
    })

    return NextResponse.json(users)
  } catch (error) {
    return serverError(error)
  }
}
