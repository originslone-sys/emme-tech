import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcryptjs'

const prisma = new PrismaClient()

async function main() {
  // Create admin user
  const adminPassword = await bcrypt.hash('admin123', 12)
  const admin = await prisma.user.upsert({
    where: { email: 'admin@aluguelpro.com' },
    update: {},
    create: {
      name: 'Administrador',
      email: 'admin@aluguelpro.com',
      password: adminPassword,
      role: 'ADMIN',
      phone: '(11) 99999-0000',
      cpfCnpj: '00000000000',
      wallet: {
        create: { balance: 0, totalReceived: 0, totalWithdrawn: 0, totalFees: 0 },
      },
    },
  })

  // Create demo client user
  const clientPassword = await bcrypt.hash('demo123', 12)
  const client = await prisma.user.upsert({
    where: { email: 'demo@aluguelpro.com' },
    update: {},
    create: {
      name: 'João Silva (Demo)',
      email: 'demo@aluguelpro.com',
      password: clientPassword,
      role: 'CLIENT',
      phone: '(11) 98888-1234',
      cpfCnpj: '12345678901',
      wallet: {
        create: { balance: 0, totalReceived: 0, totalWithdrawn: 0, totalFees: 0 },
      },
    },
  })

  console.log('Seed completed!')
  console.log('Admin:', admin.email, '/ admin123')
  console.log('Demo:', client.email, '/ demo123')
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
