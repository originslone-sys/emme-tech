import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, notFound, serverError } from '@/lib/api-helpers'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const tenant = await prisma.tenant.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
      include: { contracts: { include: { property: true } } },
    })

    if (!tenant) return notFound('Inquilino')
    return NextResponse.json(tenant)
  } catch (error) {
    return serverError(error)
  }
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.tenant.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Inquilino')

    const body = await request.json()
    const tenant = await prisma.tenant.update({
      where: { id: params.id },
      data: {
        name: body.name,
        email: body.email,
        phone: body.phone,
        cpfCnpj: body.cpfCnpj,
        birthDate: body.birthDate ? new Date(body.birthDate) : undefined,
        address: body.address,
        profession: body.profession,
        monthlyIncome: body.monthlyIncome ? parseFloat(body.monthlyIncome) : undefined,
        notes: body.notes,
      },
    })

    return NextResponse.json(tenant)
  } catch (error) {
    return serverError(error)
  }
}

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const existing = await prisma.tenant.findFirst({
      where: { id: params.id, ...(user.role !== 'ADMIN' ? { userId: user.id } : {}) },
    })
    if (!existing) return notFound('Inquilino')

    await prisma.tenant.delete({ where: { id: params.id } })
    return NextResponse.json({ message: 'Inquilino removido com sucesso' })
  } catch (error) {
    return serverError(error)
  }
}
