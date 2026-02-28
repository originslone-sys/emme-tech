import { NextResponse } from 'next/server'
import bcrypt from 'bcryptjs'
import prisma from '@/lib/prisma'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { name, email, password, phone, cpfCnpj } = body

    if (!name || !email || !password) {
      return NextResponse.json({ error: 'Nome, e-mail e senha são obrigatórios' }, { status: 400 })
    }

    const existingUser = await prisma.user.findUnique({ where: { email } })
    if (existingUser) {
      return NextResponse.json({ error: 'Este e-mail já está em uso' }, { status: 400 })
    }

    if (cpfCnpj) {
      const existingCpf = await prisma.user.findUnique({ where: { cpfCnpj } })
      if (existingCpf) {
        return NextResponse.json({ error: 'Este CPF/CNPJ já está cadastrado' }, { status: 400 })
      }
    }

    const hashedPassword = await bcrypt.hash(password, 12)

    const user = await prisma.user.create({
      data: {
        name,
        email,
        password: hashedPassword,
        phone,
        cpfCnpj: cpfCnpj || undefined,
        wallet: {
          create: {
            balance: 0,
            totalReceived: 0,
            totalWithdrawn: 0,
            totalFees: 0,
          },
        },
      },
    })

    return NextResponse.json({
      id: user.id,
      name: user.name,
      email: user.email,
    }, { status: 201 })
  } catch (error) {
    console.error('Register error:', error)
    return NextResponse.json({ error: 'Erro interno do servidor' }, { status: 500 })
  }
}
