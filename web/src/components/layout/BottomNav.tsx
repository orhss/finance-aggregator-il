import React from 'react'
import BottomNavigation from '@mui/material/BottomNavigation'
import BottomNavigationAction from '@mui/material/BottomNavigationAction'
import Paper from '@mui/material/Paper'
import DashboardIcon from '@mui/icons-material/Dashboard'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import BarChartIcon from '@mui/icons-material/BarChart'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import TuneIcon from '@mui/icons-material/Tune'
import { useLocation, useNavigate } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { label: 'Transactions', icon: <ReceiptLongIcon />, path: '/transactions' },
  { label: 'Analytics', icon: <BarChartIcon />, path: '/analytics' },
  { label: 'Accounts', icon: <AccountBalanceIcon />, path: '/accounts' },
  { label: 'Organize', icon: <TuneIcon />, path: '/organize' },
]

export function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()

  const currentIndex = NAV_ITEMS.findIndex((item) =>
    item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
  )

  return (
    <Paper
      elevation={3}
      sx={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 1200, borderRadius: 0 }}
    >
      <BottomNavigation
        value={currentIndex}
        onChange={(_, idx) => navigate(NAV_ITEMS[idx].path)}
        showLabels
        sx={{ height: 64 }}
      >
        {NAV_ITEMS.map((item) => (
          <BottomNavigationAction
            key={item.path}
            label={item.label}
            icon={item.icon}
            sx={{ minWidth: 0 }}
          />
        ))}
      </BottomNavigation>
    </Paper>
  )
}
