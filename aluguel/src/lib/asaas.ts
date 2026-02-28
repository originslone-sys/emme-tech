import axios from 'axios'

const asaasApi = axios.create({
  baseURL: process.env.ASAAS_API_URL || 'https://api.asaas.com/v3',
  headers: {
    'Content-Type': 'application/json',
    'access_token': process.env.ASAAS_API_KEY || '',
  },
})

export interface AsaasCustomer {
  name: string
  cpfCnpj: string
  email?: string
  phone?: string
  address?: string
  addressNumber?: string
  province?: string
  postalCode?: string
}

export interface AsaasPayment {
  customer: string
  billingType: 'BOLETO' | 'CREDIT_CARD' | 'PIX' | 'UNDEFINED'
  value: number
  dueDate: string
  description?: string
  externalReference?: string
}

export const asaas = {
  async createCustomer(data: AsaasCustomer) {
    const response = await asaasApi.post('/customers', data)
    return response.data
  },

  async getCustomer(id: string) {
    const response = await asaasApi.get(`/customers/${id}`)
    return response.data
  },

  async createPayment(data: AsaasPayment) {
    const response = await asaasApi.post('/payments', data)
    return response.data
  },

  async getPayment(id: string) {
    const response = await asaasApi.get(`/payments/${id}`)
    return response.data
  },

  async getPaymentPixQrCode(id: string) {
    const response = await asaasApi.get(`/payments/${id}/pixQrCode`)
    return response.data
  },

  async getPaymentBankSlip(id: string) {
    const response = await asaasApi.get(`/payments/${id}/identificationField`)
    return response.data
  },

  async deletePayment(id: string) {
    const response = await asaasApi.delete(`/payments/${id}`)
    return response.data
  },

  async getBalance() {
    const response = await asaasApi.get('/finance/balance')
    return response.data
  },

  async createTransfer(data: {
    value: number
    bankAccount?: {
      bank: { code: string }
      accountName: string
      ownerName: string
      cpfCnpj: string
      agency: string
      account: string
      accountDigit: string
    }
    pixAddressKey?: string
    pixAddressKeyType?: 'CPF' | 'CNPJ' | 'EMAIL' | 'PHONE' | 'EVP'
  }) {
    const response = await asaasApi.post('/transfers', data)
    return response.data
  },
}

export default asaas
