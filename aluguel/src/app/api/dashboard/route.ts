import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { getSessionUser, unauthorized, serverError } from '@/lib/api-helpers'

export async function GET() {
  try {
    const user = await getSessionUser()
    if (!user) return unauthorized()

    const where = user.role === 'ADMIN' ? {} : { userId: user.id }
    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0)
    const next7Days = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

    // Parallel queries
    const [
      totalReceivedData,
      totalPendingData,
      overdueCount,
      totalProperties,
      rentedProperties,
      activeContracts,
      next7DaysCharges,
      monthlyCharges,
      last6MonthsRevenue,
    ] = await Promise.all([
      // Total received this month
      prisma.charge.aggregate({
        where: { ...where, status: 'CONFIRMED', paymentDate: { gte: startOfMonth, lte: endOfMonth } },
        _sum: { netValue: true },
      }),
      // Total pending
      prisma.charge.aggregate({
        where: { ...where, status: 'PENDING' },
        _sum: { value: true },
      }),
      // Overdue count
      prisma.charge.count({
        where: { ...where, status: 'OVERDUE' },
      }),
      // Total properties
      prisma.property.count({ where }),
      // Rented properties
      prisma.property.count({ where: { ...where, status: 'RENTED' } }),
      // Active contracts
      prisma.contract.count({ where: { ...where, status: 'ACTIVE' } }),
      // Next 7 days charges
      prisma.charge.count({
        where: { ...where, status: 'PENDING', dueDate: { gte: now, lte: next7Days } },
      }),
      // Monthly charges
      prisma.charge.findMany({
        where: { ...where, dueDate: { gte: startOfMonth, lte: endOfMonth } },
        include: {
          contract: {
            include: {
              property: { select: { name: true } },
              tenant: { select: { name: true } },
            },
          },
        },
        orderBy: { dueDate: 'asc' },
      }),
      // Last 6 months revenue
      Promise.all(
        Array.from({ length: 6 }, (_, i) => {
          const date = new Date(now.getFullYear(), now.getMonth() - (5 - i), 1)
          const end = new Date(date.getFullYear(), date.getMonth() + 1, 0)
          return prisma.charge.aggregate({
            where: { ...where, status: 'CONFIRMED', paymentDate: { gte: date, lte: end } },
            _sum: { netValue: true },
          }).then(r => ({
            month: date.toLocaleDateString('pt-BR', { month: 'short' }),
            value: r._sum.netValue || 0,
          }))
        })
      ),
    ])

    const totalReceived = totalReceivedData._sum.netValue || 0
    const totalPending = totalPendingData._sum.value || 0
    const occupancyRate = totalProperties > 0 ? Math.round((rentedProperties / totalProperties) * 100) : 0
    const receiptRate = activeContracts > 0 ? Math.round((totalReceived / (activeContracts * (totalReceived / Math.max(activeContracts, 1)))) * 100) : 0
    const averageTicket = activeContracts > 0 ? totalReceived / activeContracts : 0

    // Monthly status breakdown
    const monthStatus = {
      confirmed: monthlyCharges.filter(c => c.status === 'CONFIRMED').length,
      pending: monthlyCharges.filter(c => c.status === 'PENDING').length,
      overdue: monthlyCharges.filter(c => c.status === 'OVERDUE').length,
      cancelled: monthlyCharges.filter(c => c.status === 'CANCELLED').length,
    }

    return NextResponse.json({
      stats: {
        totalReceived,
        totalPending,
        totalOverdue: overdueCount,
        occupancyRate,
        receiptRate: Math.min(receiptRate, 100),
        activeContracts,
        averageTicket,
        next7Days: next7DaysCharges,
      },
      monthlyCharges,
      last6MonthsRevenue,
      monthStatus,
    })
  } catch (error) {
    return serverError(error)
  }
}
