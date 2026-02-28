'use client'

import { getStatusColor, getStatusLabel } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`badge ${getStatusColor(status)}`}>
      {getStatusLabel(status)}
    </span>
  )
}
