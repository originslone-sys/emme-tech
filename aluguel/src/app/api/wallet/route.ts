import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    let wallet = await prisma.wallet.findUnique({ where: { userId: user.id } })

    if (!wallet) {
      wallet = await prisma.wallet.create({
        data: { userId: user.id, balance: 0, totalReceived: 0, totalWithdrawn: 0, totalFees: 0 },
      })
    }

    const withdrawals = await prisma.withdrawal.findMany({
      where: { userId: user.id },
      orderBy: { createdAt: 'desc' },
      take: 20,
    })

    const recentCharges = await prisma.charge.findMany({
      where: { userId: user.id, status: 'CONFIRMED' },
      orderBy: { paymentDate: 'desc' },
      take: 10,
      include: {
        contract: {
          include: {
            property: { select: { name: true } },
            tenant: { select: { name: true } },
          },
        },
      },
    })

    return NextResponse.json({ wallet, withdrawals, recentCharges })
  } catch (error) {
    return serverError(error)
  }
}
