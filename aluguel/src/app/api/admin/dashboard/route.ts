import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, forbidden, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()
    if (user.role !== 'ADMIN') return forbidden()

    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0)

    const [
      totalUsers,
      activeUsers,
      totalProperties,
      totalContracts,
      platformRevenue,
      totalCharges,
      pendingWithdrawals,
      recentUsers,
      recentWithdrawals,
    ] = await Promise.all([
      prisma.user.count(),
      prisma.user.count({ where: { isActive: true } }),
      prisma.property.count(),
      prisma.contract.count({ where: { status: 'ACTIVE' } }),
      prisma.charge.aggregate({
        where: { status: 'CONFIRMED', paymentDate: { gte: startOfMonth, lte: endOfMonth } },
        _sum: { platformFee: true },
      }),
      prisma.charge.count({ where: { status: 'CONFIRMED', paymentDate: { gte: startOfMonth, lte: endOfMonth } } }),
      prisma.withdrawal.findMany({
        where: { status: 'PENDING' },
        include: { user: { select: { name: true, email: true } } },
        orderBy: { createdAt: 'desc' },
      }),
      prisma.user.findMany({
        orderBy: { createdAt: 'desc' },
        take: 10,
        select: { id: true, name: true, email: true, role: true, createdAt: true },
      }),
      prisma.withdrawal.findMany({
        where: { status: 'PENDING' },
        include: { user: { select: { name: true, email: true } } },
        orderBy: { createdAt: 'desc' },
        take: 10,
      }),
    ])

    return NextResponse.json({
      totalUsers,
      activeUsers,
      totalProperties,
      totalContracts,
      platformRevenue: platformRevenue._sum.platformFee || 0,
      totalCharges,
      pendingWithdrawals,
      recentUsers,
      recentWithdrawals,
    })
  } catch (error) {
    return serverError(error)
  }
}
