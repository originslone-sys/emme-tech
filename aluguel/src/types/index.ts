export type UserRole = 'ADMIN' | 'CLIENT'
export type PropertyStatus = 'AVAILABLE' | 'RENTED' | 'MAINTENANCE'
export type ContractStatus = 'ACTIVE' | 'FINISHED' | 'CANCELLED'
export type ChargeStatus = 'PENDING' | 'CONFIRMED' | 'OVERDUE' | 'REFUNDED' | 'CANCELLED'
export type WithdrawalStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'REJECTED'

export interface User {
  id: string
  name: string
  email: string
  phone?: string
  cpfCnpj?: string
  role: UserRole
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface Property {
  id: string
  userId: string
  name: string
  type: string
  address: string
  number?: string
  complement?: string
  neighborhood: string
  city: string
  state: string
  zipCode: string
  rentValue: number
  condoFee?: number
  iptuValue?: number
  status: PropertyStatus
  description?: string
  createdAt: string
}

export interface Tenant {
  id: string
  userId: string
  name: string
  email: string
  phone: string
  cpfCnpj: string
  birthDate?: string
  address?: string
  profession?: string
  monthlyIncome?: number
  notes?: string
  createdAt: string
}

export interface Contract {
  id: string
  userId: string
  propertyId: string
  tenantId: string
  startDate: string
  endDate: string
  rentValue: number
  dueDay: number
  deposit?: number
  adjustmentIndex?: string
  status: ContractStatus
  property?: Property
  tenant?: Tenant
  createdAt: string
}

export interface Charge {
  id: string
  userId: string
  contractId: string
  description: string
  value: number
  netValue: number
  platformFee: number
  dueDate: string
  paymentDate?: string
  status: ChargeStatus
  asaasPaymentId?: string
  invoiceUrl?: string
  bankSlipUrl?: string
  pixCode?: string
  contract?: Contract
  createdAt: string
}

export interface Wallet {
  id: string
  userId: string
  balance: number
  totalReceived: number
  totalWithdrawn: number
  totalFees: number
}

export interface Withdrawal {
  id: string
  userId: string
  amount: number
  bankName?: string
  bankAgency?: string
  bankAccount?: string
  pixKey?: string
  status: WithdrawalStatus
  processedAt?: string
  notes?: string
  createdAt: string
}

export interface DashboardStats {
  totalReceived: number
  totalPending: number
  totalOverdue: number
  occupancyRate: number
  receiptRate: number
  activeContracts: number
  averageTicket: number
  next7Days: number
}
