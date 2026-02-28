import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { event, payment } = body

    if (!payment?.id) {
      return NextResponse.json({ received: true })
    }

    const charge = await prisma.charge.findFirst({
      where: { asaasPaymentId: payment.id },
    })

    if (!charge) {
      return NextResponse.json({ received: true })
    }

    let newStatus = charge.status

    switch (event) {
      case 'PAYMENT_CONFIRMED':
      case 'PAYMENT_RECEIVED':
        newStatus = 'CONFIRMED'
        break
      case 'PAYMENT_OVERDUE':
        newStatus = 'OVERDUE'
        break
      case 'PAYMENT_DELETED':
      case 'PAYMENT_REFUNDED':
        newStatus = 'REFUNDED'
        break
    }

    if (newStatus !== charge.status) {
      await prisma.charge.update({
        where: { id: charge.id },
        data: {
          status: newStatus,
          paymentDate: newStatus === 'CONFIRMED' ? new Date() : undefined,
        },
      })

      // If confirmed, credit wallet
      if (newStatus === 'CONFIRMED') {
        await prisma.wallet.upsert({
          where: { userId: charge.userId },
          create: {
            userId: charge.userId,
            balance: charge.netValue,
            totalReceived: charge.netValue,
            totalFees: charge.platformFee,
          },
          update: {
            balance: { increment: charge.netValue },
            totalReceived: { increment: charge.netValue },
            totalFees: { increment: charge.platformFee },
          },
        })
      }
    }

    return NextResponse.json({ received: true })
  } catch (error) {
    console.error('Webhook error:', error)
    return NextResponse.json({ error: 'Webhook processing failed' }, { status: 500 })
  }
}
