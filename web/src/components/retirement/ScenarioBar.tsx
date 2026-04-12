import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import FormControl from '@mui/material/FormControl'
import IconButton from '@mui/material/IconButton'
import InputLabel from '@mui/material/InputLabel'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import type { SelectChangeEvent } from '@mui/material/Select'
import TextField from '@mui/material/TextField'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import Button from '@mui/material/Button'
import AddIcon from '@mui/icons-material/Add'
import type { Scenario } from '@/types/retirement'

interface Props {
  scenarios: Scenario[]
  activeId: number
  onSelect: (id: number) => void
  onCreate: (name: string, sourceId: number | null) => void
  onClone: (id: number) => void
  onRename: (id: number, name: string) => void
  onDelete: (id: number) => void
}

export function ScenarioBar({ scenarios, activeId, onSelect, onCreate, onClone, onRename, onDelete }: Props) {
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null)
  const [menuScenarioId, setMenuScenarioId] = useState<number | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'create' | 'rename'>('create')
  const [dialogValue, setDialogValue] = useState('')
  const [sourceId, setSourceId] = useState<number | null>(null)

  const handleContextMenu = (e: React.MouseEvent<HTMLDivElement>, id: number) => {
    e.preventDefault()
    setMenuAnchor(e.currentTarget)
    setMenuScenarioId(id)
  }

  const handleClone = () => {
    if (menuScenarioId) onClone(menuScenarioId)
    setMenuAnchor(null)
  }

  const handleRenameOpen = () => {
    const s = scenarios.find((s) => s.id === menuScenarioId)
    if (s) {
      setDialogMode('rename')
      setDialogValue(s.name)
      setDialogOpen(true)
    }
    setMenuAnchor(null)
  }

  const handleDelete = () => {
    if (menuScenarioId) onDelete(menuScenarioId)
    setMenuAnchor(null)
  }

  const handleDialogConfirm = () => {
    const name = dialogValue.trim()
    if (!name) return
    if (dialogMode === 'create') {
      onCreate(name, sourceId)
    } else if (menuScenarioId) {
      onRename(menuScenarioId, name)
    }
    setDialogOpen(false)
    setDialogValue('')
  }

  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
      {scenarios.map((s) => (
        <Chip
          key={s.id}
          label={s.name}
          color={s.id === activeId ? 'primary' : 'default'}
          variant={s.id === activeId ? 'filled' : 'outlined'}
          onClick={() => onSelect(s.id)}
          onContextMenu={(e) => handleContextMenu(e, s.id)}
        />
      ))}
      <IconButton
        size="small"
        onClick={() => {
          setDialogMode('create')
          setDialogValue('')
          setSourceId(activeId)
          setDialogOpen(true)
        }}
      >
        <AddIcon fontSize="small" />
      </IconButton>

      <Menu anchorEl={menuAnchor} open={!!menuAnchor} onClose={() => setMenuAnchor(null)}>
        <MenuItem onClick={handleClone}>Clone</MenuItem>
        <MenuItem onClick={handleRenameOpen}>Rename</MenuItem>
        <MenuItem onClick={handleDelete} disabled={scenarios.length <= 1}>
          Delete
        </MenuItem>
      </Menu>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{dialogMode === 'create' ? 'New Scenario' : 'Rename Scenario'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Name"
            value={dialogValue}
            onChange={(e) => setDialogValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleDialogConfirm()}
            sx={{ mt: 1 }}
          />
          {dialogMode === 'create' && (
            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>Copy from</InputLabel>
              <Select
                value={sourceId != null ? String(sourceId) : '_blank'}
                label="Copy from"
                onChange={(e: SelectChangeEvent) => {
                  const v = e.target.value
                  setSourceId(v === '_blank' ? null : Number(v))
                }}
              >
                <MenuItem value="_blank"><em>Blank (defaults)</em></MenuItem>
                {scenarios.map((s) => (
                  <MenuItem key={s.id} value={String(s.id)}>{s.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleDialogConfirm} disabled={!dialogValue.trim()}>
            {dialogMode === 'create' ? 'Create' : 'Rename'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
