import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, badRequest, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const where = user.role === 'ADMIN' ? {} : { userId: user.id }
    const tenants = await prisma.tenant.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      include: { contracts: { where: { status: 'ACTIVE' }, select: { id: true, property: { select: { name: true } } } } },
    })

    return NextResponse.json(tenants)
  } catch (error) {
    return serverError(error)
  }
}

export async function POST(request: Request) {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const body = await request.json()
    const { name, email, phone, cpfCnpj, birthDate, address, profession, monthlyIncome, notes } = body

    if (!name || !email || !phone || !cpfCnpj) {
      return badRequest('Nome, e-mail, telefone e CPF/CNPJ são obrigatórios')
    }

    const tenant = await prisma.tenant.create({
      data: {
        userId: user.id,
        name, email, phone, cpfCnpj,
        birthDate: birthDate ? new Date(birthDate) : undefined,
        address, profession,
        monthlyIncome: monthlyIncome ? parseFloat(monthlyIncome) : undefined,
        notes,
      },
    })

    return NextResponse.json(tenant, { status: 201 })
  } catch (error) {
    return serverError(error)
  }
}
