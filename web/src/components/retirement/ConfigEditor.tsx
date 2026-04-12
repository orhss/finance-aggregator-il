import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Divider from '@mui/material/Divider'
import FormControl from '@mui/material/FormControl'
import Grid from '@mui/material/Grid2'
import IconButton from '@mui/material/IconButton'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import type { SelectChangeEvent } from '@mui/material/Select'
import Slider from '@mui/material/Slider'
import Switch from '@mui/material/Switch'
import FormControlLabel from '@mui/material/FormControlLabel'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import FileUploadIcon from '@mui/icons-material/FileUpload'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import type {
  RetirementConfig,
  PersonConfig,
  CashFlowConfig,
  PortfolioConfig,
  PensionConfig,
  KerenConfig,
} from '@/types/retirement'

// ==================== Helpers ====================

function updateList<T>(list: T[], index: number, field: string, value: unknown): T[] {
  return list.map((item, i) => (i === index ? { ...item, [field]: value } : item))
}

function removeFromList<T>(list: T[], index: number): T[] {
  return list.filter((_, i) => i !== index)
}

const DEFAULT_PERSON: PersonConfig = { name: '', dob: '1990-01-01', gender: 'male' }
const DEFAULT_INCOME: CashFlowConfig = { amount: 0, rise: 0, description: '', start: 'now', end: 'fire' }
const DEFAULT_EXPENSE: CashFlowConfig = { amount: 0, rise: 0, description: '', start: 'now', end: 'forever' }
const DEFAULT_PORTFOLIO: PortfolioConfig = {
  designation: 'withdraw',
  type: 'portfolio',
  balance: 0,
  interest: 7,
  fee: 0.5,
  profit_fraction: 0,
  withdrawal_method: 'fifo',
}
const DEFAULT_PENSION: PensionConfig = {
  balance: 0,
  deposit: 0,
  fee1: 1.49,
  fee2: 1.3,
  interest: 5,
  tactics: '60-67',
  mukeret_pct: 30,
  end: 'fire',
  person: 0,
}
const DEFAULT_KEREN: KerenConfig = {
  balance: 0,
  deposit: 0,
  interest: 6,
  type: 'maslulit',
  fee: 0.5,
  end: 'fire',
}

const TIMING_OPTIONS = [
  { value: 'now', label: 'Now' },
  { value: 'fire', label: 'At FIRE' },
  { value: 'forever', label: 'Forever' },
]

// ==================== Sub-components ====================

function NumField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  size = 'small',
  fullWidth = true,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  size?: 'small' | 'medium'
  fullWidth?: boolean
}) {
  const [local, setLocal] = useState(String(value))
  const prev = useRef(value)

  // Sync from parent when value changes externally (scenario switch, JSON import)
  if (value !== prev.current) {
    prev.current = value
    setLocal(String(value))
  }

  return (
    <TextField
      label={label}
      type="number"
      size={size}
      fullWidth={fullWidth}
      value={local}
      onChange={(e) => {
        setLocal(e.target.value)
        const v = parseFloat(e.target.value)
        if (!isNaN(v)) onChange(v)
      }}
      onBlur={() => {
        const v = parseFloat(local)
        if (isNaN(v)) {
          setLocal(String(value))
        } else {
          onChange(v)
          setLocal(String(v))
        }
      }}
      slotProps={{ htmlInput: { min, max, step } }}
    />
  )
}

function TimingSelect({
  label,
  value,
  onChange,
  options = TIMING_OPTIONS,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options?: { value: string; label: string }[]
}) {
  return (
    <FormControl size="small" fullWidth>
      <InputLabel>{label}</InputLabel>
      <Select value={value} label={label} onChange={(e: SelectChangeEvent) => onChange(e.target.value)}>
        {options.map((o) => (
          <MenuItem key={o.value} value={o.value}>
            {o.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}

function SectionAccordion({
  title,
  count,
  enabledCount,
  children,
  defaultExpanded,
}: {
  title: string
  count: number
  enabledCount?: number
  children: React.ReactNode
  defaultExpanded?: boolean
}) {
  const chipLabel = enabledCount !== undefined && enabledCount < count
    ? `${enabledCount}/${count}`
    : String(count)

  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters variant="outlined">
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mr: 1 }}>
          {title}
        </Typography>
        <Chip label={chipLabel} size="small" variant="outlined" />
      </AccordionSummary>
      <AccordionDetails>{children}</AccordionDetails>
    </Accordion>
  )
}

function ItemCard({
  label,
  placeholder,
  onLabelChange,
  onRemove,
  enabled,
  onToggleEnabled,
  children,
}: {
  label: string
  placeholder: string
  onLabelChange: (value: string) => void
  onRemove: () => void
  enabled?: boolean
  onToggleEnabled?: () => void
  children: React.ReactNode
}) {
  const isEnabled = enabled !== false
  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        p: 2,
        mb: 1.5,
        position: 'relative',
        '&:last-child': { mb: 0 },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5, gap: 1 }}>
        <TextField
          size="small"
          variant="standard"
          placeholder={placeholder}
          value={label}
          onChange={(e) => onLabelChange(e.target.value)}
          slotProps={{
            input: {
              sx: {
                fontWeight: 600,
                fontSize: '0.875rem',
                textDecoration: isEnabled ? 'none' : 'line-through',
                color: isEnabled ? undefined : 'text.disabled',
              },
            },
          }}
          sx={{ flex: 1 }}
        />
        {onToggleEnabled && (
          <IconButton
            size="small"
            onClick={onToggleEnabled}
            color={isEnabled ? 'default' : 'warning'}
            title={isEnabled ? 'Disable' : 'Enable'}
          >
            {isEnabled ? <VisibilityIcon fontSize="small" /> : <VisibilityOffIcon fontSize="small" />}
          </IconButton>
        )}
        <IconButton size="small" onClick={onRemove} color="error">
          <DeleteOutlineIcon fontSize="small" />
        </IconButton>
      </Box>
      <Box sx={{ opacity: isEnabled ? 1 : 0.4, pointerEvents: isEnabled ? 'auto' : 'none' }}>
        {children}
      </Box>
    </Box>
  )
}

// ==================== Main Component ====================

interface Props {
  config: Record<string, unknown>
  onConfigChange: (config: Record<string, unknown>) => void
  onRun: () => void
  isRunning: boolean
}

export function ConfigEditor({ config, onConfigChange, onRun, isRunning }: Props) {
  const [showJson, setShowJson] = useState(false)
  const [jsonText, setJsonText] = useState('')
  const [jsonError, setJsonError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const c = config as unknown as RetirementConfig

  // Helper: update a top-level field
  const set = useCallback(
    (field: string, value: unknown) => {
      onConfigChange({ ...config, [field]: value })
    },
    [config, onConfigChange]
  )

  // Helper: update a list field
  const setList = useCallback(
    <T,>(field: string, list: T[]) => {
      onConfigChange({ ...config, [field]: list })
    },
    [config, onConfigChange]
  )

  // Sync JSON text when toggling to JSON view or when config changes while JSON is shown
  useEffect(() => {
    if (showJson) {
      setJsonText(JSON.stringify(config, null, 2))
      setJsonError(null)
    }
  }, [showJson, config])

  const handleJsonBlur = useCallback(() => {
    try {
      const parsed = JSON.parse(jsonText)
      setJsonError(null)
      onConfigChange(parsed)
    } catch (e: unknown) {
      setJsonError(e instanceof Error ? e.message : 'Invalid JSON')
    }
  }, [jsonText, onConfigChange])

  const handleImport = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileLoad = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = (ev) => {
        const text = ev.target?.result as string
        try {
          const parsed = JSON.parse(text)
          onConfigChange(parsed)
        } catch (err: unknown) {
          setJsonError(err instanceof Error ? err.message : 'Invalid JSON file')
        }
      }
      reader.readAsText(file)
      e.target.value = ''
    },
    [onConfigChange]
  )

  const handleExport = useCallback(() => {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'retirement-config.json'
    a.click()
    URL.revokeObjectURL(url)
  }, [config])

  // Person names for pension person select
  const personNames = useMemo(
    () => (c.persons ?? []).map((p, i) => ({ value: i, label: p.name || `Person ${i + 1}` })),
    [c.persons]
  )

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, opacity: isRunning ? 0.6 : 1 }}>
      {/* ==================== Simulation Settings ==================== */}
      <Box
        sx={{
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          p: 2,
        }}
      >
        <Typography variant="subtitle2" fontWeight={600} gutterBottom>
          Simulation Settings
        </Typography>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="caption" color="text.secondary">
              Retire Rule: {c.retire_rule ?? 80}
            </Typography>
            <Slider
              value={c.retire_rule ?? 80}
              min={80}
              max={99}
              step={1}
              onChange={(_, v) => set('retire_rule', v as number)}
              valueLabelDisplay="auto"
              size="small"
            />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <NumField
              label="Max Retire Age"
              value={c.max_retire_age ?? 50}
              onChange={(v) => set('max_retire_age', v)}
              min={40}
              max={70}
            />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <NumField
              label="End Age"
              value={c.end_age ?? 84}
              onChange={(v) => set('end_age', v)}
              min={60}
              max={120}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Withdrawal Order
            </Typography>
            <ToggleButtonGroup
              value={c.withdrawal_order ?? 'prati'}
              exclusive
              size="small"
              fullWidth
              onChange={(_, v) => v && set('withdrawal_order', v)}
            >
              <ToggleButton value="prati">Prati</ToggleButton>
              <ToggleButton value="hishtalmut">Hishtalmut</ToggleButton>
            </ToggleButtonGroup>
          </Grid>
          <Grid size={{ xs: 6, sm: 4 }}>
            <NumField
              label="Cash Buffer"
              value={c.cash_buffer ?? 1000}
              onChange={(v) => set('cash_buffer', v)}
              min={0}
            />
          </Grid>
          <Grid size={{ xs: 6, sm: 4 }}>
            <NumField
              label="Checking Balance"
              value={c.balance ?? 0}
              onChange={(v) => set('balance', v)}
              min={0}
            />
          </Grid>
        </Grid>
      </Box>

      {/* ==================== Persons ==================== */}
      <SectionAccordion title="Persons" count={(c.persons ?? []).length} defaultExpanded>
        {(c.persons ?? []).map((person, i) => (
          <ItemCard
            key={i}
            label={person.name}
            placeholder={`Person ${i + 1}`}
            onLabelChange={(v) => setList('persons', updateList(c.persons, i, 'name', v))}
            onRemove={() => setList('persons', removeFromList(c.persons, i))}
          >
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 4 }}>
                <TextField
                  label="Date of Birth"
                  type="date"
                  size="small"
                  fullWidth
                  value={person.dob}
                  onChange={(e) => setList('persons', updateList(c.persons, i, 'dob', e.target.value))}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Gender
                </Typography>
                <ToggleButtonGroup
                  value={person.gender}
                  exclusive
                  size="small"
                  fullWidth
                  onChange={(_, v) => v && setList('persons', updateList(c.persons, i, 'gender', v))}
                >
                  <ToggleButton value="male">Male</ToggleButton>
                  <ToggleButton value="female">Female</ToggleButton>
                </ToggleButtonGroup>
              </Grid>
            </Grid>
          </ItemCard>
        ))}
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setList('persons', [...(c.persons ?? []), { ...DEFAULT_PERSON }])}
        >
          Add Person
        </Button>
      </SectionAccordion>

      {/* ==================== Incomes ==================== */}
      <SectionAccordion title="Incomes" count={(c.incomes ?? []).length} enabledCount={(c.incomes ?? []).filter(x => x.enabled !== false).length}>
        {(c.incomes ?? []).map((income, i) => (
          <ItemCard
            key={i}
            label={income.description}
            placeholder={`Income ${i + 1}`}
            onLabelChange={(v) => setList('incomes', updateList(c.incomes, i, 'description', v))}
            onRemove={() => setList('incomes', removeFromList(c.incomes, i))}
            enabled={income.enabled}
            onToggleEnabled={() => setList('incomes', updateList(c.incomes, i, 'enabled', income.enabled === false ? undefined : false))}
          >
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Amount"
                  value={income.amount}
                  onChange={(v) => setList('incomes', updateList(c.incomes, i, 'amount', v))}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Rise %"
                  value={income.rise}
                  onChange={(v) => setList('incomes', updateList(c.incomes, i, 'rise', v))}
                  step={0.5}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <TimingSelect
                  label="Start"
                  value={income.start_date ? 'from' : income.start}
                  onChange={(v) => {
                    if (v === 'from') {
                      setList('incomes', updateList(c.incomes, i, 'start_date', ''))
                    } else {
                      const updated = { ...income, start: v }
                      delete (updated as Record<string, unknown>).start_date
                      setList('incomes', (c.incomes ?? []).map((e, j) => (j === i ? updated : e)))
                    }
                  }}
                  options={[
                    { value: 'now', label: 'Now' },
                    { value: 'fire', label: 'At FIRE' },
                    { value: 'forever', label: 'Forever' },
                    { value: 'from', label: 'From date' },
                  ]}
                />
              </Grid>
              {income.start_date !== undefined && (
                <Grid size={{ xs: 6, sm: 3 }}>
                  <TextField
                    label="Start Date"
                    type="date"
                    size="small"
                    fullWidth
                    value={income.start_date ?? ''}
                    onChange={(e) =>
                      setList('incomes', updateList(c.incomes, i, 'start_date', e.target.value))
                    }
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                </Grid>
              )}
              <Grid size={{ xs: 6, sm: 3 }}>
                <TimingSelect
                  label="End"
                  value={income.end}
                  onChange={(v) => setList('incomes', updateList(c.incomes, i, 'end', v))}
                />
              </Grid>
            </Grid>
          </ItemCard>
        ))}
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setList('incomes', [...(c.incomes ?? []), { ...DEFAULT_INCOME }])}
        >
          Add Income
        </Button>
      </SectionAccordion>

      {/* ==================== Expenses ==================== */}
      <SectionAccordion title="Expenses" count={(c.expenses ?? []).length} enabledCount={(c.expenses ?? []).filter(x => x.enabled !== false).length}>
        {(c.expenses ?? []).map((expense, i) => (
          <ItemCard
            key={i}
            label={expense.description}
            placeholder={`Expense ${i + 1}`}
            onLabelChange={(v) => setList('expenses', updateList(c.expenses, i, 'description', v))}
            onRemove={() => setList('expenses', removeFromList(c.expenses, i))}
            enabled={expense.enabled}
            onToggleEnabled={() => setList('expenses', updateList(c.expenses, i, 'enabled', expense.enabled === false ? undefined : false))}
          >
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Amount"
                  value={expense.amount}
                  onChange={(v) => setList('expenses', updateList(c.expenses, i, 'amount', v))}
                />
              </Grid>
              {expense.type !== 'one_time' && (
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Rise %"
                    value={expense.rise}
                    onChange={(v) => setList('expenses', updateList(c.expenses, i, 'rise', v))}
                    step={0.5}
                  />
                </Grid>
              )}
              <Grid size={{ xs: 6, sm: 3 }}>
                <ToggleButtonGroup
                  value={expense.type ?? 'recurring'}
                  exclusive
                  size="small"
                  fullWidth
                  onChange={(_, v) => {
                    if (!v) return
                    const isOneTime = v === 'one_time'
                    const updated = { ...expense, type: isOneTime ? ('one_time' as const) : undefined }
                    if (!isOneTime) {
                      delete (updated as Record<string, unknown>).start_date
                    }
                    if (isOneTime) {
                      delete (updated as Record<string, unknown>).end_date
                    }
                    setList('expenses', (c.expenses ?? []).map((e, j) => (j === i ? updated : e)))
                  }}
                >
                  <ToggleButton value="recurring">Monthly</ToggleButton>
                  <ToggleButton value="one_time">One-Time</ToggleButton>
                </ToggleButtonGroup>
              </Grid>
              {expense.type === 'one_time' ? (
                <Grid size={{ xs: 6, sm: 3 }}>
                  <TextField
                    label="Date"
                    type="date"
                    size="small"
                    fullWidth
                    value={expense.start_date ?? ''}
                    onChange={(e) =>
                      setList('expenses', updateList(c.expenses, i, 'start_date', e.target.value))
                    }
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                </Grid>
              ) : (
                <>
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <TimingSelect
                      label="Start"
                      value={expense.start_date ? 'from' : expense.start}
                      onChange={(v) => {
                        if (v === 'from') {
                          setList('expenses', updateList(c.expenses, i, 'start_date', ''))
                        } else {
                          const updated = { ...expense, start: v }
                          delete (updated as Record<string, unknown>).start_date
                          setList('expenses', (c.expenses ?? []).map((e, j) => (j === i ? updated : e)))
                        }
                      }}
                      options={[
                        { value: 'now', label: 'Now' },
                        { value: 'fire', label: 'At FIRE' },
                        { value: 'forever', label: 'Forever' },
                        { value: 'from', label: 'From date' },
                      ]}
                    />
                  </Grid>
                  {expense.start_date !== undefined && (
                    <Grid size={{ xs: 6, sm: 3 }}>
                      <TextField
                        label="Start Date"
                        type="date"
                        size="small"
                        fullWidth
                        value={expense.start_date ?? ''}
                        onChange={(e) =>
                          setList('expenses', updateList(c.expenses, i, 'start_date', e.target.value))
                        }
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                    </Grid>
                  )}
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <TimingSelect
                      label="End"
                      value={expense.end_date ? 'until' : expense.end}
                      onChange={(v) => {
                        if (v === 'until') {
                          setList('expenses', updateList(c.expenses, i, 'end_date', ''))
                        } else {
                          // Clear end_date when switching away from "until"
                          const updated = { ...expense, end: v }
                          delete (updated as Record<string, unknown>).end_date
                          setList('expenses', (c.expenses ?? []).map((e, j) => (j === i ? updated : e)))
                        }
                      }}
                      options={[
                        { value: 'now', label: 'Now' },
                        { value: 'fire', label: 'At FIRE' },
                        { value: 'forever', label: 'Forever' },
                        { value: 'until', label: 'Until date' },
                      ]}
                    />
                  </Grid>
                  {expense.end_date !== undefined && (
                    <Grid size={{ xs: 6, sm: 3 }}>
                      <TextField
                        label="End Date"
                        type="date"
                        size="small"
                        fullWidth
                        value={expense.end_date ?? ''}
                        onChange={(e) =>
                          setList('expenses', updateList(c.expenses, i, 'end_date', e.target.value))
                        }
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                    </Grid>
                  )}
                </>
              )}
            </Grid>
          </ItemCard>
        ))}
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setList('expenses', [...(c.expenses ?? []), { ...DEFAULT_EXPENSE }])}
        >
          Add Expense
        </Button>
      </SectionAccordion>

      {/* ==================== Portfolios ==================== */}
      <SectionAccordion title="Portfolios" count={(c.portfolios ?? []).length} enabledCount={(c.portfolios ?? []).filter(x => x.enabled !== false).length}>
        {(c.portfolios ?? []).map((portfolio, i) => (
          <ItemCard
            key={i}
            label={portfolio.description ?? ''}
            placeholder={`${portfolio.type === 'kaspit' ? 'Kaspit' : 'Portfolio'} ${i + 1}${portfolio.designation === 'goal' ? ' (Goal)' : ''}`}
            onLabelChange={(v) => setList('portfolios', updateList(c.portfolios, i, 'description', v))}
            onRemove={() => setList('portfolios', removeFromList(c.portfolios, i))}
            enabled={portfolio.enabled}
            onToggleEnabled={() => setList('portfolios', updateList(c.portfolios, i, 'enabled', portfolio.enabled === false ? undefined : false))}
          >
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Designation
                </Typography>
                <ToggleButtonGroup
                  value={portfolio.designation}
                  exclusive
                  size="small"
                  fullWidth
                  onChange={(_, v) =>
                    v && setList('portfolios', updateList(c.portfolios, i, 'designation', v))
                  }
                >
                  <ToggleButton value="withdraw">Withdraw</ToggleButton>
                  <ToggleButton value="goal">Goal</ToggleButton>
                </ToggleButtonGroup>
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Type
                </Typography>
                <ToggleButtonGroup
                  value={portfolio.type}
                  exclusive
                  size="small"
                  fullWidth
                  onChange={(_, v) =>
                    v && setList('portfolios', updateList(c.portfolios, i, 'type', v))
                  }
                >
                  <ToggleButton value="portfolio">Portfolio</ToggleButton>
                  <ToggleButton value="kaspit">Kaspit</ToggleButton>
                </ToggleButtonGroup>
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <NumField
                  label="Balance"
                  value={portfolio.balance}
                  onChange={(v) => setList('portfolios', updateList(c.portfolios, i, 'balance', v))}
                  min={0}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Interest %"
                  value={portfolio.interest}
                  onChange={(v) => setList('portfolios', updateList(c.portfolios, i, 'interest', v))}
                  step={0.5}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Fee %"
                  value={portfolio.fee}
                  onChange={(v) => setList('portfolios', updateList(c.portfolios, i, 'fee', v))}
                  step={0.1}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Profit %"
                  value={portfolio.profit_fraction}
                  onChange={(v) =>
                    setList('portfolios', updateList(c.portfolios, i, 'profit_fraction', v))
                  }
                  min={0}
                  max={100}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Withdrawal</InputLabel>
                  <Select
                    value={portfolio.withdrawal_method ?? 'fifo'}
                    label="Withdrawal"
                    onChange={(e: SelectChangeEvent) =>
                      setList('portfolios', updateList(c.portfolios, i, 'withdrawal_method', e.target.value))
                    }
                  >
                    <MenuItem value="fifo">FIFO</MenuItem>
                    <MenuItem value="flat">Flat</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              {portfolio.designation === 'goal' && (
                <Grid size={{ xs: 6, sm: 4 }}>
                  <NumField
                    label="Goal Amount"
                    value={portfolio.goal ?? 0}
                    onChange={(v) => setList('portfolios', updateList(c.portfolios, i, 'goal', v))}
                    min={0}
                  />
                </Grid>
              )}
            </Grid>
          </ItemCard>
        ))}
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setList('portfolios', [...(c.portfolios ?? []), { ...DEFAULT_PORTFOLIO }])}
        >
          Add Portfolio
        </Button>
      </SectionAccordion>

      {/* ==================== Pensions ==================== */}
      <SectionAccordion title="Pensions" count={(c.pensions ?? []).length} enabledCount={(c.pensions ?? []).filter(x => x.enabled !== false).length}>
        {(c.pensions ?? []).map((pension, i) => {
          const personLabel = personNames[pension.person]?.label ?? `Person ${pension.person}`
          return (
            <ItemCard
              key={i}
              label={pension.description ?? ''}
              placeholder={`Pension ${i + 1} (${personLabel})`}
              onLabelChange={(v) => setList('pensions', updateList(c.pensions, i, 'description', v))}
              onRemove={() => setList('pensions', removeFromList(c.pensions, i))}
              enabled={pension.enabled}
              onToggleEnabled={() => setList('pensions', updateList(c.pensions, i, 'enabled', pension.enabled === false ? undefined : false))}
            >
              <Grid container spacing={2}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Balance"
                    value={pension.balance}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'balance', v))}
                    min={0}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Monthly Deposit"
                    value={pension.deposit}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'deposit', v))}
                    min={0}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Fee on Deposits %"
                    value={pension.fee1}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'fee1', v))}
                    step={0.01}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Mgmt Fee %"
                    value={pension.fee2}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'fee2', v))}
                    step={0.01}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Interest %"
                    value={pension.interest}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'interest', v))}
                    step={0.5}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <FormControl size="small" fullWidth>
                    <InputLabel>Tactics</InputLabel>
                    <Select
                      value={pension.tactics}
                      label="Tactics"
                      onChange={(e: SelectChangeEvent) =>
                        setList('pensions', updateList(c.pensions, i, 'tactics', e.target.value))
                      }
                    >
                      <MenuItem value="60">60 — Early, lower payout</MenuItem>
                      <MenuItem value="67">67 — Full payout</MenuItem>
                      <MenuItem value="60-67">60-67 — Mukeret early, Mazka at 67</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <NumField
                    label="Mukeret %"
                    value={pension.mukeret_pct}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'mukeret_pct', v))}
                    min={0}
                    max={100}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <FormControl size="small" fullWidth>
                    <InputLabel>Person</InputLabel>
                    <Select
                      value={String(pension.person)}
                      label="Person"
                      onChange={(e: SelectChangeEvent) =>
                        setList('pensions', updateList(c.pensions, i, 'person', parseInt(e.target.value, 10)))
                      }
                    >
                      {personNames.map((p) => (
                        <MenuItem key={p.value} value={String(p.value)}>
                          {p.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <TimingSelect
                    label="Deposits End"
                    value={pension.end}
                    onChange={(v) => setList('pensions', updateList(c.pensions, i, 'end', v))}
                    options={[
                      { value: 'fire', label: 'At FIRE' },
                      { value: 'forever', label: 'Forever' },
                    ]}
                  />
                </Grid>
              </Grid>
            </ItemCard>
          )
        })}
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setList('pensions', [...(c.pensions ?? []), { ...DEFAULT_PENSION }])}
        >
          Add Pension
        </Button>
      </SectionAccordion>

      {/* ==================== Kerens ==================== */}
      <SectionAccordion title="Kerens (Hishtalmut)" count={(c.kerens ?? []).length} enabledCount={(c.kerens ?? []).filter(x => x.enabled !== false).length}>
        {(c.kerens ?? []).map((keren, i) => (
          <ItemCard
            key={i}
            label={keren.description ?? ''}
            placeholder={`Keren ${i + 1}`}
            onLabelChange={(v) => setList('kerens', updateList(c.kerens, i, 'description', v))}
            onRemove={() => setList('kerens', removeFromList(c.kerens, i))}
            enabled={keren.enabled}
            onToggleEnabled={() => setList('kerens', updateList(c.kerens, i, 'enabled', keren.enabled === false ? undefined : false))}
          >
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Balance"
                  value={keren.balance}
                  onChange={(v) => setList('kerens', updateList(c.kerens, i, 'balance', v))}
                  min={0}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Monthly Deposit"
                  value={keren.deposit}
                  onChange={(v) => setList('kerens', updateList(c.kerens, i, 'deposit', v))}
                  min={0}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Interest %"
                  value={keren.interest}
                  onChange={(v) => setList('kerens', updateList(c.kerens, i, 'interest', v))}
                  step={0.5}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <NumField
                  label="Fee %"
                  value={keren.fee}
                  onChange={(v) => setList('kerens', updateList(c.kerens, i, 'fee', v))}
                  step={0.1}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <TimingSelect
                  label="Deposits End"
                  value={keren.end}
                  onChange={(v) => setList('kerens', updateList(c.kerens, i, 'end', v))}
                  options={[
                    { value: 'fire', label: 'At FIRE' },
                    { value: 'forever', label: 'Forever' },
                  ]}
                />
              </Grid>
            </Grid>
          </ItemCard>
        ))}
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setList('kerens', [...(c.kerens ?? []), { ...DEFAULT_KEREN }])}
        >
          Add Keren
        </Button>
      </SectionAccordion>

      {/* ==================== Actions & JSON ==================== */}
      <Divider />

      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          size="large"
          onClick={onRun}
          disabled={isRunning}
          startIcon={isRunning ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
        >
          {isRunning ? 'Running...' : 'Run Simulation'}
        </Button>

        <Box sx={{ flex: 1 }} />

        <input ref={fileInputRef} type="file" accept=".json" hidden onChange={handleFileLoad} />
        <Button size="small" startIcon={<FileUploadIcon />} onClick={handleImport}>
          Import
        </Button>
        <Button size="small" startIcon={<FileDownloadIcon />} onClick={handleExport}>
          Export
        </Button>
        <FormControlLabel
          control={<Switch size="small" checked={showJson} onChange={(_, v) => setShowJson(v)} />}
          label={<Typography variant="caption">Raw JSON</Typography>}
        />
      </Box>

      {showJson && (
        <>
          <Box
            component="textarea"
            value={jsonText}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setJsonText(e.target.value)}
            onBlur={handleJsonBlur}
            spellCheck={false}
            sx={{
              fontFamily: 'monospace',
              fontSize: 12,
              lineHeight: 1.5,
              p: 2,
              border: 1,
              borderColor: jsonError ? 'error.main' : 'divider',
              borderRadius: 1,
              bgcolor: 'background.paper',
              color: 'text.primary',
              resize: 'vertical',
              minHeight: 300,
              width: '100%',
              outline: 'none',
              '&:focus': {
                borderColor: jsonError ? 'error.main' : 'primary.main',
              },
            }}
          />
          {jsonError && (
            <Typography variant="caption" color="error">
              {jsonError}
            </Typography>
          )}
        </>
      )}
    </Box>
  )
}
