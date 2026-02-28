import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, notFound, badRequest, serverError } from '@/lib/api-helpers'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const charge = await prisma.charge.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
      include: {
        contract: {
          include: { property: true, tenant: true },
        },
      },
    })

    if (!charge) return notFound('Cobrança')
    return NextResponse.json(charge)
  } catch (error) {
    return serverError(error)
  }
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.charge.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Cobrança')

    const body = await request.json()

    // If confirming payment, add to wallet
    if (body.status === 'CONFIRMED' && existing.status !== 'CONFIRMED') {
      await prisma.wallet.upsert({
        where: { userId: existing.userId },
        create: {
          userId: existing.userId,
          balance: existing.netValue,
          totalReceived: existing.netValue,
          totalFees: existing.platformFee,
        },
        update: {
          balance: { increment: existing.netValue },
          totalReceived: { increment: existing.netValue },
          totalFees: { increment: existing.platformFee },
        },
      })
    }

    const charge = await prisma.charge.update({
      where: { id: params.id },
      data: {
        status: body.status,
        paymentDate: body.status === 'CONFIRMED' ? new Date() : undefined,
      },
    })

    return NextResponse.json(charge)
  } catch (error) {
    return serverError(error)
  }
}

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.charge.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Cobrança')

    if (existing.status === 'CONFIRMED') {
      return badRequest('Não é possível excluir uma cobrança já confirmada')
    }

    await prisma.charge.delete({ where: { id: params.id } })
    return NextResponse.json({ message: 'Cobrança removida com sucesso' })
  } catch (error) {
    return serverError(error)
  }
}
