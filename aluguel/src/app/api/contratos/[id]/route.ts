import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, notFound, serverError } from '@/lib/api-helpers'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const contract = await prisma.contract.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
      include: {
        property: true,
        tenant: true,
        charges: { orderBy: { dueDate: 'desc' } },
      },
    })

    if (!contract) return notFound('Contrato')
    return NextResponse.json(contract)
  } catch (error) {
    return serverError(error)
  }
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.contract.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Contrato')

    const body = await request.json()

    // If cancelling/finishing, set property back to AVAILABLE
    if (body.status && body.status !== 'ACTIVE' && existing.status === 'ACTIVE') {
      await prisma.property.update({
        where: { id: existing.propertyId },
        data: { status: 'AVAILABLE' },
      })
    }

    const contract = await prisma.contract.update({
      where: { id: params.id },
      data: {
        startDate: body.startDate ? new Date(body.startDate) : undefined,
        endDate: body.endDate ? new Date(body.endDate) : undefined,
        rentValue: body.rentValue ? parseFloat(body.rentValue) : undefined,
        dueDay: body.dueDay ? parseInt(body.dueDay) : undefined,
        deposit: body.deposit !== undefined ? parseFloat(body.deposit) : undefined,
        adjustmentIndex: body.adjustmentIndex,
        status: body.status,
        notes: body.notes,
      },
    })

    return NextResponse.json(contract)
  } catch (error) {
    return serverError(error)
  }
}

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.contract.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Contrato')

    await prisma.property.update({
      where: { id: existing.propertyId },
      data: { status: 'AVAILABLE' },
    })

    await prisma.contract.delete({ where: { id: params.id } })
    return NextResponse.json({ message: 'Contrato removido com sucesso' })
  } catch (error) {
    return serverError(error)
  }
}
