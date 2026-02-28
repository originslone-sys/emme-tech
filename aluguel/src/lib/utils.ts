import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(date))
}

export function formatPhone(phone: string): string {
  const cleaned = phone.replace(/\D/g, '')
  if (cleaned.length === 11) {
    return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`
  }
  return phone
}

export function formatCpfCnpj(value: string): string {
  const cleaned = value.replace(/\D/g, '')
  if (cleaned.length === 11) {
    return `${cleaned.slice(0, 3)}.${cleaned.slice(3, 6)}.${cleaned.slice(6, 9)}-${cleaned.slice(9)}`
  }
  if (cleaned.length === 14) {
    return `${cleaned.slice(0, 2)}.${cleaned.slice(2, 5)}.${cleaned.slice(5, 8)}/${cleaned.slice(8, 12)}-${cleaned.slice(12)}`
  }
  return value
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    AVAILABLE: 'bg-green-100 text-green-800',
    RENTED: 'bg-blue-100 text-blue-800',
    MAINTENANCE: 'bg-yellow-100 text-yellow-800',
    ACTIVE: 'bg-green-100 text-green-800',
    FINISHED: 'bg-gray-100 text-gray-800',
    CANCELLED: 'bg-red-100 text-red-800',
    PENDING: 'bg-yellow-100 text-yellow-800',
    CONFIRMED: 'bg-green-100 text-green-800',
    OVERDUE: 'bg-red-100 text-red-800',
    REFUNDED: 'bg-purple-100 text-purple-800',
    PROCESSING: 'bg-blue-100 text-blue-800',
    COMPLETED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    AVAILABLE: 'Disponível',
    RENTED: 'Alugado',
    MAINTENANCE: 'Manutenção',
    ACTIVE: 'Ativo',
    FINISHED: 'Finalizado',
    CANCELLED: 'Cancelado',
    PENDING: 'Pendente',
    CONFIRMED: 'Confirmado',
    OVERDUE: 'Atrasado',
    REFUNDED: 'Reembolsado',
    PROCESSING: 'Processando',
    COMPLETED: 'Concluído',
    REJECTED: 'Rejeitado',
  }
  return labels[status] || status
}

export const PLATFORM_FEE = parseFloat(process.env.PLATFORM_FEE || '20')

export const PROPERTY_TYPES = [
  'Apartamento',
  'Casa',
  'Sala Comercial',
  'Galpão',
  'Terreno',
  'Kitnet',
  'Loft',
  'Cobertura',
  'Sobrado',
  'Loja',
]

export const BRAZILIAN_STATES = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]
