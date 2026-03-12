import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Divider from '@mui/material/Divider'
import FormControlLabel from '@mui/material/FormControlLabel'
import Switch from '@mui/material/Switch'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useCurrentBudget, useSetBudget } from '@/api/budget'
import { usePrivacy } from '@/contexts/PrivacyContext'
import { useThemeMode } from '@/contexts/ThemeContext'
import { useAuth } from '@/contexts/AuthContext'
import { formatCurrency } from '@/utils/format'

export default function Settings() {
  const { mode, toggleMode } = useThemeMode()
  const { maskBalances, toggleMask } = usePrivacy()
  const { username, logout } = useAuth()

  const { data: currentBudget } = useCurrentBudget()
  const { mutate: setBudget, isPending } = useSetBudget()
  const [budgetInput, setBudgetInput] = useState('')

  function handleSaveBudget() {
    const amount = parseFloat(budgetInput)
    if (!isNaN(amount) && amount > 0) {
      setBudget({ amount })
      setBudgetInput('')
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 480 }}>
      {/* Account */}
      {username && (
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Account
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Signed in as <strong>{username}</strong>
            </Typography>
            <Button variant="outlined" color="error" size="small" onClick={logout}>
              Sign Out
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Appearance */}
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            Appearance
          </Typography>
          <FormControlLabel
            control={<Switch checked={mode === 'dark'} onChange={toggleMode} />}
            label="Dark mode"
          />
          <Divider sx={{ my: 1.5 }} />
          <FormControlLabel
            control={<Switch checked={maskBalances} onChange={toggleMask} />}
            label="Privacy mode (hide amounts)"
          />
        </CardContent>
      </Card>

      {/* Budget */}
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            Monthly Budget
          </Typography>
          {currentBudget?.amount != null && (
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Current: {formatCurrency(currentBudget.amount)}
            </Typography>
          )}
          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
            <TextField
              size="small"
              label="Budget amount (₪)"
              type="number"
              value={budgetInput}
              onChange={(e) => setBudgetInput(e.target.value)}
              sx={{ flex: 1 }}
            />
            <Button variant="contained" onClick={handleSaveBudget} disabled={isPending}>
              Save
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* About */}
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            About
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Fin — Personal Finance Dashboard
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            React SPA · FastAPI · SQLite
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}
