import React from 'react'
import AppBar from '@mui/material/AppBar'
import IconButton from '@mui/material/IconButton'
import Toolbar from '@mui/material/Toolbar'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import MenuIcon from '@mui/icons-material/Menu'
import Brightness4Icon from '@mui/icons-material/Brightness4'
import Brightness7Icon from '@mui/icons-material/Brightness7'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import SyncIcon from '@mui/icons-material/Sync'
import { useThemeMode } from '@/contexts/ThemeContext'
import { usePrivacy } from '@/contexts/PrivacyContext'

interface TopBarProps {
  onMenuClick?: () => void
  isMobile?: boolean
}

export function TopBar({ onMenuClick, isMobile }: TopBarProps) {
  const { mode, toggleMode } = useThemeMode()
  const { maskBalances, toggleMask } = usePrivacy()

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: 'background.paper',
        borderBottom: 1,
        borderColor: 'divider',
        color: 'text.primary',
      }}
    >
      <Toolbar sx={{ gap: 1 }}>
        {isMobile && (
          <IconButton edge="start" onClick={onMenuClick} size="small">
            <MenuIcon />
          </IconButton>
        )}

        <Typography variant="h6" sx={{ flex: 1, fontWeight: 700, color: 'primary.main' }}>
          Fin
        </Typography>

        <Tooltip title={maskBalances ? 'Show balances' : 'Hide balances'}>
          <IconButton size="small" onClick={toggleMask}>
            {maskBalances ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
          </IconButton>
        </Tooltip>

        <Tooltip title={mode === 'light' ? 'Dark mode' : 'Light mode'}>
          <IconButton size="small" onClick={toggleMode}>
            {mode === 'light' ? <Brightness4Icon fontSize="small" /> : <Brightness7Icon fontSize="small" />}
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  )
}
