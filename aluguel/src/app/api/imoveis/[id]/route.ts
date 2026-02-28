import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, notFound, serverError } from '@/lib/api-helpers'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const property = await prisma.property.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
      include: { contracts: { include: { tenant: true } } },
    })

    if (!property) return notFound('Imóvel')
    return NextResponse.json(property)
  } catch (error) {
    return serverError(error)
  }
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.property.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Imóvel')

    const body = await request.json()
    const property = await prisma.property.update({
      where: { id: params.id },
      data: {
        name: body.name,
        type: body.type,
        address: body.address,
        number: body.number,
        complement: body.complement,
        neighborhood: body.neighborhood,
        city: body.city,
        state: body.state,
        zipCode: body.zipCode,
        rentValue: body.rentValue ? parseFloat(body.rentValue) : undefined,
        condoFee: body.condoFee !== undefined ? parseFloat(body.condoFee) : undefined,
        iptuValue: body.iptuValue !== undefined ? parseFloat(body.iptuValue) : undefined,
        status: body.status,
        description: body.description,
      },
    })

    return NextResponse.json(property)
  } catch (error) {
    return serverError(error)
  }
}

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.property.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Imóvel')

    await prisma.property.delete({ where: { id: params.id } })
    return NextResponse.json({ message: 'Imóvel removido com sucesso' })
  } catch (error) {
    return serverError(error)
  }
}
