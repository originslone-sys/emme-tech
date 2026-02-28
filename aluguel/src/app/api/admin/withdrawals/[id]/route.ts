import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, forbidden, notFound, badRequest, serverError } from '@/lib/api-helpers'

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()
    if (user.role !== 'ADMIN') return forbidden()

    const body = await request.json()
    const { status, notes } = body

    const withdrawal = await prisma.withdrawal.findUnique({ where: { id: params.id } })
    if (!withdrawal) return notFound('Saque')

    if (withdrawal.status !== 'PENDING') {
      return badRequest('Apenas saques pendentes podem ser atualizados')
    }

    // If rejecting, refund the balance
    if (status === 'REJECTED') {
      await prisma.wallet.update({
        where: { userId: withdrawal.userId },
        data: {
          balance: { increment: withdrawal.amount },
          totalWithdrawn: { decrement: withdrawal.amount },
        },
      })
    }

    const updated = await prisma.withdrawal.update({
      where: { id: params.id },
      data: {
        status,
        notes,
        processedAt: status === 'COMPLETED' || status === 'REJECTED' ? new Date() : undefined,
      },
    })

    return NextResponse.json(updated)
  } catch (error) {
    return serverError(error)
  }
}
