import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useTags, useTagStats, useDeleteTag } from '@/api/tags'
import type { TagStats } from '@/types/tag'
import { useCategoryMappings, useUnmappedCategories, useAddCategoryMapping, useMerchantSuggestions, useBulkAssignCategory } from '@/api/categories'
import { useRules, useCreateRule, useDeleteRule, useApplyRules } from '@/api/rules'
import { UnifiedCategory } from '@/utils/constants'
import { formatCurrency } from '@/utils/format'

function TabPanel({ value, index, children }: { value: number; index: number; children: React.ReactNode }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null
}

// ── Categories Tab ──────────────────────────────────────────────────────────

function CategoriesTab() {
  const { data: unmapped } = useUnmappedCategories()
  const { data: mappings } = useCategoryMappings()
  const { data: suggestions } = useMerchantSuggestions()
  const { mutate: addMapping } = useAddCategoryMapping()
  const { mutate: bulkAssign } = useBulkAssignCategory()
  const [pendingMaps, setPendingMaps] = useState<Record<string, string>>({})

  function saveMapping(provider: string, raw: string, unified: string) {
    addMapping({ provider, raw_category: raw, unified_category: unified })
  }

  function saveMerchant(pattern: string, category: string) {
    bulkAssign({ pattern, category, save_mapping: true })
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Unmapped */}
      {unmapped && unmapped.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Unmapped Categories ({unmapped.length})
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {unmapped.map((u) => (
                <Box key={`${u.provider}-${u.raw_category}`} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2">{u.raw_category}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {u.provider} · {u.count} txns
                    </Typography>
                  </Box>
                  <FormControl size="small" sx={{ minWidth: 140 }}>
                    <Select
                      displayEmpty
                      value={pendingMaps[`${u.provider}:${u.raw_category}`] ?? ''}
                      onChange={(e) => {
                        const val = e.target.value
                        setPendingMaps((p) => ({ ...p, [`${u.provider}:${u.raw_category}`]: val }))
                        if (val) saveMapping(u.provider, u.raw_category, val)
                      }}
                    >
                      <MenuItem value=""><em>Map to…</em></MenuItem>
                      {Object.values(UnifiedCategory).map((cat) => (
                        <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Merchant suggestions */}
      {suggestions && suggestions.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Merchant Patterns ({suggestions.length})
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {suggestions.map((s) => (
                <Box key={s.merchant_pattern} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2">{s.merchant_pattern}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {s.count} txns · {formatCurrency(s.total_amount)}
                    </Typography>
                  </Box>
                  <FormControl size="small" sx={{ minWidth: 140 }}>
                    <Select
                      displayEmpty
                      value=""
                      onChange={(e) => { if (e.target.value) saveMerchant(s.merchant_pattern, e.target.value) }}
                    >
                      <MenuItem value=""><em>Assign…</em></MenuItem>
                      {Object.values(UnifiedCategory).map((cat) => (
                        <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* All mappings */}
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            All Mappings ({mappings?.length ?? 0})
          </Typography>
          {mappings?.map((m) => (
            <Box key={`${m.provider}-${m.raw_category}`} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
              <Typography variant="body2" color="text.secondary">{m.raw_category}</Typography>
              <Typography variant="body2" fontWeight={500}>{m.unified_category}</Typography>
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  )
}

// ── Rules Tab ───────────────────────────────────────────────────────────────

function RulesTab() {
  const { data: rules } = useRules()
  const { mutate: createRule } = useCreateRule()
  const { mutate: deleteRule } = useDeleteRule()
  const { mutate: applyRules, data: applyResult } = useApplyRules()
  const [pattern, setPattern] = useState('')
  const [ruleCategory, setRuleCategory] = useState('')
  const [tags, setTags] = useState('')

  function handleCreate() {
    if (!pattern || !ruleCategory) return
    createRule({
      pattern,
      category: ruleCategory,
      tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
    })
    setPattern('')
    setRuleCategory('')
    setTags('')
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            New Rule
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <TextField
              size="small"
              label="Pattern (contains)"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              sx={{ flex: 1, minWidth: 160 }}
            />
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Category</InputLabel>
              <Select label="Category" value={ruleCategory} onChange={(e) => setRuleCategory(e.target.value)}>
                {Object.values(UnifiedCategory).map((cat) => (
                  <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Tags (comma-sep)"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              sx={{ flex: 1, minWidth: 120 }}
            />
            <Button variant="contained" onClick={handleCreate}>Add</Button>
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button variant="outlined" onClick={() => applyRules({ dry_run: true })}>Dry Run</Button>
        <Button variant="contained" onClick={() => applyRules({})}>Apply All Rules</Button>
      </Box>
      {applyResult && (
        <Typography variant="body2" color="success.main">
          Applied to {applyResult.modified} transactions
        </Typography>
      )}

      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>Rules</Typography>
          {!rules?.length && <Typography color="text.secondary" variant="body2">No rules yet.</Typography>}
          {rules?.map((r, i) => (
            <React.Fragment key={r.pattern}>
              {i > 0 && <Divider />}
              <Box sx={{ py: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2" fontWeight={500}>{r.pattern}</Typography>
                  <Typography variant="caption" color="text.secondary">→ {r.category}{r.tags?.length ? ` · ${r.tags.join(', ')}` : ''}</Typography>
                </Box>
                <Button size="small" color="error" onClick={() => deleteRule(r.pattern)}>Remove</Button>
              </Box>
            </React.Fragment>
          ))}
        </CardContent>
      </Card>
    </Box>
  )
}

// ── Tags Tab ────────────────────────────────────────────────────────────────

function TagsTab() {
  const { data: tagStats } = useTagStats()
  const { mutate: deleteTag } = useDeleteTag()
  const [pendingDeleteTag, setPendingDeleteTag] = useState<TagStats | null>(null)

  return (
    <Box>
      <Card>
        <CardContent>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            Tags ({tagStats?.length ?? 0})
          </Typography>
          {!tagStats?.length && (
            <Typography color="text.secondary" variant="body2">
              No tags yet. Edit a transaction to add tags.
            </Typography>
          )}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {tagStats?.map((t) => (
              <Chip
                key={t.name}
                label={`${t.name} (${t.count})`}
                onDelete={() => setPendingDeleteTag(t)}
                size="small"
              />
            ))}
          </Box>
        </CardContent>
      </Card>

      <Dialog open={!!pendingDeleteTag} onClose={() => setPendingDeleteTag(null)}>
        <DialogTitle>Delete tag "{pendingDeleteTag?.name}"?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will remove the tag from {pendingDeleteTag?.count} transaction{pendingDeleteTag?.count === 1 ? '' : 's'}. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDeleteTag(null)}>Cancel</Button>
          <Button
            color="error"
            onClick={() => {
              if (pendingDeleteTag) deleteTag(pendingDeleteTag.name)
              setPendingDeleteTag(null)
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function Organize() {
  const [tab, setTab] = useState(0)

  return (
    <Box>
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 1, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="Categories" />
        <Tab label="Rules" />
        <Tab label="Tags" />
      </Tabs>

      <TabPanel value={tab} index={0}><CategoriesTab /></TabPanel>
      <TabPanel value={tab} index={1}><RulesTab /></TabPanel>
      <TabPanel value={tab} index={2}><TagsTab /></TabPanel>
    </Box>
  )
}
