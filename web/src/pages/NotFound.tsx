import React from 'react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'

export default function NotFound() {
  const navigate = useNavigate()
  return (
    <EmptyState
      icon="🔍"
      title="Page not found"
      description="The page you're looking for doesn't exist."
      action={{ label: 'Go to Dashboard', onClick: () => navigate('/dashboard') }}
    />
  )
}
