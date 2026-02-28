import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, badRequest, serverError } from '@/lib/api-helpers'
import { asaas } from '@/lib/asaas'

const PLATFORM_FEE = parseFloat(process.env.PLATFORM_FEE || '20')

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const where = user.role === 'ADMIN' ? {} : { userId: user.id }
    const charges = await prisma.charge.findMany({
      where,
      orderBy: { dueDate: 'desc' },
      include: {
        contract: {
          include: {
            property: { select: { name: true } },
            tenant: { select: { name: true } },
          },
        },
      },
    })

    return NextResponse.json(charges)
  } catch (error) {
    return serverError(error)
  }
}

export async function POST(request: Request) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const body = await request.json()
    const { contractId, description, value, dueDate, billingType } = body

    if (!contractId || !value || !dueDate) {
      return badRequest('Contrato, valor e data de vencimento são obrigatórios')
    }

    const contract = await prisma.contract.findFirst({
      where: { id: contractId, userId: user.id },
      include: { tenant: true },
    })

    if (!contract) return badRequest('Contrato não encontrado')

    const chargeValue = parseFloat(value)
    const netValue = chargeValue - PLATFORM_FEE

    // Create charge in Asaas if tenant has Asaas customer ID
    let asaasPaymentId = null
    let invoiceUrl = null
    let bankSlipUrl = null
    let pixCode = null

    if (contract.tenant.asaasCustomerId) {
      try {
        const payment = await asaas.createPayment({
          customer: contract.tenant.asaasCustomerId,
          billingType: billingType || 'UNDEFINED',
          value: chargeValue,
          dueDate,
          description: description || `Aluguel - ${contract.tenant.name}`,
          externalReference: contractId,
        })

        asaasPaymentId = payment.id
        invoiceUrl = payment.invoiceUrl
        bankSlipUrl = payment.bankSlipUrl

        if (payment.billingType === 'PIX' || billingType === 'PIX') {
          try {
            const pixData = await asaas.getPaymentPixQrCode(payment.id)
            pixCode = pixData.payload
          } catch {}
        }
      } catch (err) {
        console.error('Asaas payment creation failed:', err)
      }
    }

    const charge = await prisma.charge.create({
      data: {
        userId: user.id,
        contractId,
        description: description || 'Aluguel mensal',
        value: chargeValue,
        netValue,
        platformFee: PLATFORM_FEE,
        dueDate: new Date(dueDate),
        asaasPaymentId,
        asaasBillingType: billingType || 'BOLETO',
        invoiceUrl,
        bankSlipUrl,
        pixCode,
      },
      include: {
        contract: {
          include: {
            property: { select: { name: true } },
            tenant: { select: { name: true } },
          },
        },
      },
    })

    return NextResponse.json(charge, { status: 201 })
  } catch (error) {
    return serverError(error)
  }
}
