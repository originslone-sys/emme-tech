import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, badRequest, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const where = user.role === 'ADMIN' ? {} : { userId: user.id }
    const properties = await prisma.property.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      include: { contracts: { where: { status: 'ACTIVE' }, select: { id: true } } },
    })

    return NextResponse.json(properties)
  } catch (error) {
    return serverError(error)
  }
}

export async function POST(request: Request) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const body = await request.json()
    const { name, type, address, number, complement, neighborhood, city, state, zipCode, rentValue, condoFee, iptuValue, description } = body

    if (!name || !type || !address || !neighborhood || !city || !state || !zipCode || !rentValue) {
      return badRequest('Campos obrigatórios não preenchidos')
    }

    const property = await prisma.property.create({
      data: {
        userId: user.id,
        name, type, address, number, complement, neighborhood, city, state, zipCode,
        rentValue: parseFloat(rentValue),
        condoFee: condoFee ? parseFloat(condoFee) : 0,
        iptuValue: iptuValue ? parseFloat(iptuValue) : 0,
        description,
      },
    })

    return NextResponse.json(property, { status: 201 })
  } catch (error) {
    return serverError(error)
  }
}
