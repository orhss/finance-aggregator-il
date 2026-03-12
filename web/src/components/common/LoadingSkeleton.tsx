import React from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid2'
import Skeleton from '@mui/material/Skeleton'

export function MetricsSkeleton() {
  return (
    <Grid container spacing={2}>
      {[1, 2, 3, 4].map((i) => (
        <Grid key={i} size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" height={40} />
              <Skeleton variant="text" width="40%" />
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  )
}

export function TransactionListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Card key={i}>
          <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="50%" />
                <Skeleton variant="text" width="30%" />
              </Box>
              <Skeleton variant="text" width={80} />
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  )
}

export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return <Skeleton variant="rectangular" height={height} sx={{ borderRadius: 2 }} />
}
