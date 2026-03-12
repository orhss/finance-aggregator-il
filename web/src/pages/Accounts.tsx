import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Divider from '@mui/material/Divider'
import Grid from '@mui/material/Grid2'
import LinearProgress from '@mui/material/LinearProgress'
import Typography from '@mui/material/Typography'
import SyncIcon from '@mui/icons-material/Sync'
import { useAccounts } from '@/api/accounts'
import { useSyncHistory, startSync, createSyncStream } from '@/api/sync'
import { AccountCard } from '@/components/cards/AccountCard'
import { EmptyState } from '@/components/common/EmptyState'
import { ChartSkeleton } from '@/components/common/LoadingSkeleton'
import { formatRelativeDate } from '@/utils/format'
import type { Account } from '@/types/account'
import type { SyncProgress } from '@/types/sync'

const INSTITUTIONS = ['cal', 'max', 'isracard', 'excellence', 'meitav', 'migdal', 'phoenix']
const INSTITUTION_LABELS: Record<string, string> = {
  cal: 'CAL', max: 'Max', isracard: 'Isracard',
  excellence: 'Excellence', meitav: 'Meitav', migdal: 'Migdal', phoenix: 'Phoenix',
}

export default function Accounts() {
  const { data: accounts, isLoading, refetch } = useAccounts()
  const { data: history } = useSyncHistory({ limit: 10 })

  const [syncing, setSyncing] = useState<string | null>(null)
  const [progress, setProgress] = useState<SyncProgress | null>(null)

  async function handleSync(institution: string) {
    setSyncing(institution)
    setProgress(null)
    try {
      const { job_id } = await startSync(institution)
      createSyncStream(
        job_id,
        (data) => setProgress(data),
        (success) => {
          setSyncing(null)
          if (success) refetch()
        },
      )
    } catch {
      setSyncing(null)
    }
  }

  const byInstitution = accounts?.reduce<Record<string, Account[]>>((acc, a) => {
    acc[a.institution] = [...(acc[a.institution] ?? []), a]
    return acc
  }, {})

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Sync Panel */}
      <Card>
        <CardContent>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Sync
          </Typography>

          {syncing && progress && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {progress.message}
              </Typography>
              <LinearProgress />
            </Box>
          )}

          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              startIcon={syncing === 'all' ? <CircularProgress size={16} color="inherit" /> : <SyncIcon />}
              disabled={!!syncing}
              onClick={() => handleSync('all')}
            >
              Sync All
            </Button>
            {INSTITUTIONS.map((inst) => (
              <Button
                key={inst}
                variant="outlined"
                size="small"
                disabled={!!syncing}
                onClick={() => handleSync(inst)}
              >
                {INSTITUTION_LABELS[inst]}
              </Button>
            ))}
          </Box>
        </CardContent>
      </Card>

      {/* Accounts by institution */}
      {isLoading ? (
        <ChartSkeleton height={200} />
      ) : !accounts?.length ? (
        <EmptyState
          icon="🏦"
          title="No accounts yet"
          description="Sync your financial institutions to see accounts here."
          action={{ label: 'Sync All', onClick: () => handleSync('all') }}
        />
      ) : (
        Object.entries(byInstitution ?? {}).map(([inst, accts]) => (
          <Box key={inst}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {INSTITUTION_LABELS[inst] ?? inst}
            </Typography>
            <Grid container spacing={2}>
              {accts.map((acc) => (
                <Grid key={acc.id} size={{ xs: 12, sm: 6, md: 4 }}>
                  <AccountCard account={acc} />
                </Grid>
              ))}
            </Grid>
          </Box>
        ))
      )}

      {/* Sync history */}
      {history && history.length > 0 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Sync History
          </Typography>
          <Card variant="outlined">
            {history.map((h, i) => (
              <React.Fragment key={h.id}>
                {i > 0 && <Divider />}
                <Box sx={{ px: 2, py: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="body2" fontWeight={500}>
                      {h.institution}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatRelativeDate(h.started_at)}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {h.records_added != null && (
                      <Typography variant="caption" color="text.secondary">
                        +{h.records_added} txns
                      </Typography>
                    )}
                    <Chip
                      label={h.status}
                      size="small"
                      color={h.status === 'success' ? 'success' : h.status === 'failed' ? 'error' : 'default'}
                      sx={{ height: 20, fontSize: '0.65rem' }}
                    />
                  </Box>
                </Box>
              </React.Fragment>
            ))}
          </Card>
        </Box>
      )}
    </Box>
  )
}
