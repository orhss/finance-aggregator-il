import React from 'react'
import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Button from '@mui/material/Button'

interface AlertCardProps {
  severity: 'error' | 'warning' | 'info' | 'success'
  title: string
  message: string
  action?: { label: string; onClick: () => void }
}

export function AlertCard({ severity, title, message, action }: AlertCardProps) {
  return (
    <Alert
      severity={severity}
      sx={{ mb: 1 }}
      action={
        action && (
          <Button color="inherit" size="small" onClick={action.onClick}>
            {action.label}
          </Button>
        )
      }
    >
      <AlertTitle>{title}</AlertTitle>
      {message}
    </Alert>
  )
}
