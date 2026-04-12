import React from 'react'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import WorkOffIcon from '@mui/icons-material/WorkOff'
import SavingsIcon from '@mui/icons-material/Savings'
import ElderlyIcon from '@mui/icons-material/Elderly'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import EventIcon from '@mui/icons-material/Event'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import { formatCurrency } from '@/utils/format'
import type { Milestone } from '@/types/retirement'

interface Props {
  milestones: Milestone[]
}

function getMilestoneIcon(type: string) {
  switch (type) {
    case 'fire':
      return <WorkOffIcon color="success" />
    case 'pension_conversion':
      return <SavingsIcon color="info" />
    case 'old_age_start':
      return <ElderlyIcon />
    case 'portfolio_depleted':
      return <TrendingDownIcon color="error" />
    case 'kh_depleted':
      return <AccountBalanceIcon color="warning" />
    case 'one_time_expense':
      return <EventIcon color="action" />
    default:
      return <EventIcon />
  }
}

export function MilestonesList({ milestones }: Props) {
  // Deduplicate milestones by type+age (within 0.5 year tolerance for one_time_expense)
  const unique = milestones.filter(
    (m, i, arr) =>
      arr.findIndex((o) => o.type === m.type && o.label === m.label && Math.abs(o.age - m.age) < 0.5) === i
  )

  return (
    <List dense>
      {unique.map((m, i) => (
        <ListItem key={`${m.type}-${m.age}-${i}`}>
          <ListItemIcon sx={{ minWidth: 36 }}>{getMilestoneIcon(m.type)}</ListItemIcon>
          <ListItemText
            primary={m.label}
            secondary={`Age ${m.age.toFixed(1)} — ${m.date}${m.amount ? ` — ${formatCurrency(m.amount)}` : ''}`}
          />
        </ListItem>
      ))}
    </List>
  )
}
