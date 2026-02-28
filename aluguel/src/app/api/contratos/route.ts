import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, badRequest, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const where = user.role === 'ADMIN' ? {} : { userId: user.id }
    const contracts = await prisma.contract.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      include: {
        property: { select: { name: true, address: true, city: true } },
        tenant: { select: { name: true, email: true, phone: true } },
      },
    })

    return NextResponse.json(contracts)
  } catch (error) {
    return serverError(error)
  }
}

export async function POST(request: Request) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const body = await request.json()
    const { propertyId, tenantId, startDate, endDate, rentValue, dueDay, deposit, adjustmentIndex, notes } = body

    if (!propertyId || !tenantId || !startDate || !endDate || !rentValue || !dueDay) {
      return badRequest('Campos obrigatórios não preenchidos')
    }

    // Update property status to RENTED
    await prisma.property.update({
      where: { id: propertyId },
      data: { status: 'RENTED' },
    })

    const contract = await prisma.contract.create({
      data: {
        userId: user.id,
        propertyId, tenantId,
        startDate: new Date(startDate),
        endDate: new Date(endDate),
        rentValue: parseFloat(rentValue),
        dueDay: parseInt(dueDay),
        deposit: deposit ? parseFloat(deposit) : 0,
        adjustmentIndex: adjustmentIndex || 'IGPM',
        notes,
      },
      include: {
        property: { select: { name: true } },
        tenant: { select: { name: true } },
      },
    })

    return NextResponse.json(contract, { status: 201 })
  } catch (error) {
    return serverError(error)
  }
}
