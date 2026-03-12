import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import FormControl from '@mui/material/FormControl'
import InputAdornment from '@mui/material/InputAdornment'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import SearchIcon from '@mui/icons-material/Search'
import { useTransactions, useUpdateTransaction } from '@/api/transactions'
import { AmountDisplay } from '@/components/common/AmountDisplay'
import { EmptyState } from '@/components/common/EmptyState'
import { TransactionListSkeleton } from '@/components/common/LoadingSkeleton'
import { RtlText } from '@/components/common/RtlText'
import { TransactionItem } from '@/components/cards/TransactionItem'
import { useDebounce } from '@/hooks/useDebounce'
import { useDateRange } from '@/hooks/useDateRange'
import { formatDate } from '@/utils/format'
import { UnifiedCategory } from '@/utils/constants'
import type { Transaction } from '@/types/transaction'

const PAGE_SIZE = 25

export default function Transactions() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Transaction | null>(null)
  const [editCategory, setEditCategory] = useState('')
  const [editMemo, setEditMemo] = useState('')

  const debouncedSearch = useDebounce(search, 300)
  const { range } = useDateRange()

  const { data, isLoading } = useTransactions({
    search: debouncedSearch || undefined,
    category: category || undefined,
    from_date: range.from ?? undefined,
    to_date: range.to ?? undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  })

  const { mutate: updateTxn, isPending: updating } = useUpdateTransaction()

  function openDrawer(txn: Transaction) {
    setSelected(txn)
    setEditCategory(txn.user_category ?? txn.effective_category ?? '')
    setEditMemo(txn.memo ?? '')
  }

  function closeDrawer() {
    setSelected(null)
  }

  function saveChanges() {
    if (!selected) return
    updateTxn(
      {
        id: selected.id,
        body: {
          user_category: editCategory || null,
          memo: editMemo || null,
        },
      },
      { onSuccess: closeDrawer },
    )
  }

  const total = data?.total ?? 0
  const pageCount = Math.ceil(total / PAGE_SIZE)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <TextField
          size="small"
          placeholder="Search..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0) }}
          InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
          sx={{ flex: 1, minWidth: 200 }}
        />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Category</InputLabel>
          <Select
            label="Category"
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(0) }}
          >
            <MenuItem value="">All</MenuItem>
            {Object.values(UnifiedCategory).map((cat) => (
              <MenuItem key={cat} value={cat}>{cat}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Summary */}
      {data && (
        <Typography variant="caption" color="text.secondary">
          {total} transactions
        </Typography>
      )}

      {/* List */}
      {isLoading ? (
        <TransactionListSkeleton rows={PAGE_SIZE} />
      ) : !data?.items.length ? (
        <EmptyState icon="🔍" title="No transactions found" description="Try adjusting your filters." />
      ) : (
        data.items.map((txn) => (
          <TransactionItem key={txn.id} transaction={txn} onClick={openDrawer} />
        ))
      )}

      {/* Pagination */}
      {pageCount > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mt: 1 }}>
          <Button size="small" disabled={page === 0} onClick={() => setPage(page - 1)}>
            ‹ Prev
          </Button>
          <Typography variant="body2" sx={{ alignSelf: 'center' }}>
            {page + 1} / {pageCount}
          </Typography>
          <Button size="small" disabled={page >= pageCount - 1} onClick={() => setPage(page + 1)}>
            Next ›
          </Button>
        </Box>
      )}

      {/* Edit Drawer */}
      <Drawer anchor="bottom" open={!!selected} onClose={closeDrawer} PaperProps={{ sx: { borderRadius: '16px 16px 0 0', p: 3, maxHeight: '70vh' } }}>
        {selected && (
          <Box>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              <RtlText text={selected.description} />
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {formatDate(selected.transaction_date)}
            </Typography>
            <AmountDisplay
              amount={selected.charged_amount ?? selected.original_amount}
              variant="h5"
              sx={{ fontWeight: 700, mb: 2 }}
            />

            <Divider sx={{ mb: 2 }} />

            <Stack spacing={2}>
              <FormControl size="small" fullWidth>
                <InputLabel>Category override</InputLabel>
                <Select
                  label="Category override"
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                >
                  <MenuItem value="">
                    <em>Auto ({selected.effective_category ?? 'none'})</em>
                  </MenuItem>
                  {Object.values(UnifiedCategory).map((cat) => (
                    <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                size="small"
                label="Memo"
                fullWidth
                multiline
                rows={2}
                value={editMemo}
                onChange={(e) => setEditMemo(e.target.value)}
              />

              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="contained" onClick={saveChanges} disabled={updating} fullWidth>
                  Save
                </Button>
                <Button variant="outlined" onClick={closeDrawer} fullWidth>
                  Cancel
                </Button>
              </Box>
            </Stack>
          </Box>
        )}
      </Drawer>
    </Box>
  )
}
