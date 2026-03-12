import React, { useState } from 'react'
import Box from '@mui/material/Box'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { Outlet } from 'react-router-dom'
import { TopBar } from './TopBar'
import { Sidebar } from './Sidebar'
import { BottomNav } from './BottomNav'

const SIDEBAR_WIDTH = 240

export function AppShell() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <Box sx={{ display: 'flex', height: '100dvh', overflow: 'hidden' }}>
      {/* Sidebar (desktop only permanent, mobile temporary) */}
      <Sidebar
        open={isMobile ? drawerOpen : true}
        variant={isMobile ? 'temporary' : 'permanent'}
        width={SIDEBAR_WIDTH}
        onClose={() => setDrawerOpen(false)}
      />

      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          minWidth: 0,
        }}
      >
        <TopBar onMenuClick={() => setDrawerOpen(true)} isMobile={isMobile} />

        <Box
          sx={{
            flex: 1,
            overflowY: 'auto',
            px: { xs: 2, md: 3 },
            py: { xs: 2, md: 3 },
            pb: { xs: 10, md: 3 }, // Extra bottom padding for mobile nav
          }}
        >
          <Outlet />
        </Box>

        {/* Bottom navigation (mobile only) */}
        {isMobile && <BottomNav />}
      </Box>
    </Box>
  )
}
