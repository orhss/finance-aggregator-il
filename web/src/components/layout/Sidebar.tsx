import React from 'react'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import DashboardIcon from '@mui/icons-material/Dashboard'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import BarChartIcon from '@mui/icons-material/BarChart'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import TuneIcon from '@mui/icons-material/Tune'
import SettingsIcon from '@mui/icons-material/Settings'
import { useLocation, useNavigate } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { label: 'Transactions', icon: <ReceiptLongIcon />, path: '/transactions' },
  { label: 'Analytics', icon: <BarChartIcon />, path: '/analytics' },
  { label: 'Accounts', icon: <AccountBalanceIcon />, path: '/accounts' },
  { label: 'Organize', icon: <TuneIcon />, path: '/organize' },
  { label: 'Settings', icon: <SettingsIcon />, path: '/settings' },
]

interface SidebarProps {
  open: boolean
  variant: 'permanent' | 'temporary'
  width: number
  onClose: () => void
}

export function Sidebar({ open, variant, width, onClose }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()

  const content = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 3, py: 2.5 }}>
        <Typography variant="h5" fontWeight={800} color="primary">
          Fin
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Financial Dashboard
        </Typography>
      </Box>

      <Divider />

      <List sx={{ px: 1, pt: 1, flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const active =
            item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
          return (
            <ListItemButton
              key={item.path}
              selected={active}
              onClick={() => {
                navigate(item.path)
                onClose()
              }}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                '&.Mui-selected': { bgcolor: 'primary.main', color: 'white', '& svg': { color: 'white' } },
                '&.Mui-selected:hover': { bgcolor: 'primary.dark' },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: 'inherit' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} primaryTypographyProps={{ fontWeight: active ? 600 : 400 }} />
            </ListItemButton>
          )
        })}
      </List>

      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary">
          v0.1.0
        </Typography>
      </Box>
    </Box>
  )

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      sx={{
        width,
        flexShrink: 0,
        '& .MuiDrawer-paper': { width, boxSizing: 'border-box', borderRight: 1, borderColor: 'divider' },
      }}
    >
      {content}
    </Drawer>
  )
}
