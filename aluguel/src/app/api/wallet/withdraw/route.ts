import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, badRequest, serverError } from '@/lib/api-helpers'

export async function POST(request: Request) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const body = await request.json()
    const { amount, pixKey, bankName, bankAgency, bankAccount } = body

    if (!amount || amount <= 0) {
      return badRequest('Valor inválido')
    }

    if (!pixKey && (!bankName || !bankAgency || !bankAccount)) {
      return badRequest('Informe uma chave PIX ou dados bancários')
    }

    const wallet = await prisma.wallet.findUnique({ where: { userId: user.id } })

    if (!wallet || wallet.balance < amount) {
      return badRequest('Saldo insuficiente')
    }

    // Create withdrawal and debit wallet in a transaction
    const [withdrawal] = await prisma.$transaction([
      prisma.withdrawal.create({
        data: {
          userId: user.id,
          amount: parseFloat(amount),
          pixKey,
          bankName,
          bankAgency,
          bankAccount,
          status: 'PENDING',
        },
      }),
      prisma.wallet.update({
        where: { userId: user.id },
        data: {
          balance: { decrement: parseFloat(amount) },
          totalWithdrawn: { increment: parseFloat(amount) },
        },
      }),
    ])

    return NextResponse.json(withdrawal, { status: 201 })
  } catch (error) {
    return serverError(error)
  }
}
