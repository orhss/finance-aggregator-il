import React from 'react'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Skeleton from '@mui/material/Skeleton'

interface MetricCardProps {
  title: string
  value: string | number | React.ReactNode
  subtitle?: string
  icon?: React.ReactNode
  loading?: boolean
  color?: string
}

export function MetricCard({ title, value, subtitle, icon, loading, color }: MetricCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" height={40} width="80%" />
          {subtitle && <Skeleton variant="text" width="40%" />}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={500} textTransform="uppercase" letterSpacing={0.5}>
              {title}
            </Typography>
            <Typography component="div" variant="h5" fontWeight={700} color={color || 'text.primary'} sx={{ mt: 0.5 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          {icon && (
            <Box sx={{ color: color || 'primary.main', fontSize: 28 }}>
              {icon}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  )
}
