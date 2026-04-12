import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CircularProgress from '@mui/material/CircularProgress'
import Skeleton from '@mui/material/Skeleton'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import Typography from '@mui/material/Typography'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import { AlertCard } from '@/components/cards/AlertCard'
import { ScenarioBar } from '@/components/retirement/ScenarioBar'
import { ConfigEditor } from '@/components/retirement/ConfigEditor'
import { ResultsOverview } from '@/components/retirement/ResultsOverview'
import { NetWorthChart } from '@/components/retirement/NetWorthChart'
import { AssetCompositionChart } from '@/components/retirement/AssetCompositionChart'
import { IncomeSourcesChart } from '@/components/retirement/IncomeSourcesChart'
import { MilestonesList } from '@/components/retirement/MilestonesList'
import { CashflowTable } from '@/components/retirement/CashflowTable'
import { ScenarioCompare } from '@/components/retirement/ScenarioCompare'
import {
  useSimulate,
  useScenarios,
  useCreateScenario,
  useUpdateScenario,
  useDeleteScenario,
} from '@/api/retirement'
import { apiClient } from '@/api/client'
import type {
  Scenario,
  ScenarioResult,
  SimulationResponse,
  CashFlowConfig,
  PortfolioConfig,
  PensionConfig,
  KerenConfig,
} from '@/types/retirement'

const EXAMPLE_CONFIG = {
  mode: 'retire_asap',
  max_retire_age: 55,
  retire_rule: 80,
  withdrawal_order: 'prati',
  cash_buffer: 1000,
  balance: 10000,
  end_age: 84,
  persons: [
    { name: 'Dad', dob: '1988-06-15', gender: 'male' },
    { name: 'Mom', dob: '1990-03-20', gender: 'female' },
  ],
  incomes: [
    { amount: 30000, rise: 3, description: 'Salary', start: 'now', end: 'fire' },
  ],
  expenses: [
    { amount: 15000, rise: 2, description: 'Living expenses', start: 'now', end: 'fire' },
    { amount: 12000, rise: 2, description: 'Post-FIRE expenses', start: 'fire', end: 'forever' },
  ],
  portfolios: [
    {
      designation: 'withdraw',
      type: 'portfolio',
      balance: 1200000,
      interest: 7,
      fee: 0.5,
      profit_fraction: 25,
    },
    {
      designation: 'goal',
      type: 'kaspit',
      balance: 80000,
      interest: 4.5,
      fee: 0.3,
      profit_fraction: 0,
    },
  ],
  pensions: [
    {
      balance: 500000,
      deposit: 3500,
      fee1: 1.49,
      fee2: 1.3,
      interest: 5,
      tactics: '60-67',
      mukeret_pct: 30,
      end: 'fire',
      person: 0,
    },
    {
      balance: 300000,
      deposit: 3000,
      fee1: 1.49,
      fee2: 2.0,
      interest: 5,
      tactics: '60-67',
      mukeret_pct: 30,
      end: 'fire',
      person: 1,
    },
  ],
  kerens: [
    {
      balance: 200000,
      deposit: 3000,
      interest: 6,
      type: 'maslulit',
      fee: 0.5,
      end: 'fire',
    },
  ],
}

const DEBOUNCE_MS = 1000

function TabPanel({ value, index, children }: { value: number; index: number; children: React.ReactNode }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null
}

/** Strip disabled items before sending config to the API. */
function prepareConfigForSimulation(config: Record<string, unknown>) {
  const strip = <T extends { enabled?: boolean }>(items: T[] | undefined) =>
    (items ?? []).filter((i) => i.enabled !== false).map(({ enabled: _, ...rest }) => rest as T)
  return {
    ...config,
    expenses: strip(config.expenses as CashFlowConfig[]),
    incomes: strip(config.incomes as CashFlowConfig[]),
    portfolios: strip(config.portfolios as PortfolioConfig[]),
    pensions: strip(config.pensions as PensionConfig[]),
    kerens: strip(config.kerens as KerenConfig[]),
  }
}

export default function Retirement() {
  // ----- server state -----
  const { data: serverScenarios, isLoading } = useScenarios()
  const createMutation = useCreateScenario()
  const updateMutation = useUpdateScenario()
  const deleteMutation = useDeleteScenario()

  // ----- local (optimistic) state -----
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [activeId, setActiveId] = useState<number>(0)
  const [tab, setTab] = useState(0)
  const [allResults, setAllResults] = useState<Record<number, ScenarioResult>>({})
  const [runAllRunning, setRunAllRunning] = useState(false)
  const [initialized, setInitialized] = useState(false)
  const creatingDefault = useRef(false)

  const simulate = useSimulate()

  // ----- debounce ref -----
  const configSaveRef = useRef<{
    timer: ReturnType<typeof setTimeout>
    scenarioId: number
    config: Record<string, unknown>
  } | null>(null)

  const flushPendingSave = useCallback(() => {
    const pending = configSaveRef.current
    if (pending) {
      clearTimeout(pending.timer)
      configSaveRef.current = null
      updateMutation.mutate({ id: pending.scenarioId, config: pending.config })
    }
  }, [updateMutation])

  // ----- sync server → local on first load -----
  useEffect(() => {
    if (!serverScenarios || initialized) return

    if (serverScenarios.length > 0) {
      setScenarios(serverScenarios)
      setActiveId(serverScenarios[0].id)
      setInitialized(true)
    } else if (!creatingDefault.current) {
      // Empty DB — create default "Baseline" scenario (guard against re-fires)
      creatingDefault.current = true
      createMutation.mutate(
        { name: 'Baseline', config: EXAMPLE_CONFIG },
        {
          onSuccess: (created) => {
            setScenarios([created])
            setActiveId(created.id)
            setInitialized(true)
          },
        }
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverScenarios, initialized])

  // ----- flush on beforeunload & unmount -----
  useEffect(() => {
    const onBeforeUnload = () => flushPendingSave()
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      flushPendingSave()
    }
  }, [flushPendingSave])

  // ----- derived -----
  const activeScenario = useMemo(() => scenarios.find((s) => s.id === activeId), [scenarios, activeId])
  const activeResult = allResults[activeId]
  const activeData = activeResult?.status === 'ok' ? activeResult.data : null

  const okCount = useMemo(
    () => Object.values(allResults).filter((r) => r.status === 'ok').length,
    [allResults]
  )

  // ----- handlers -----
  const handleConfigChange = useCallback(
    (config: Record<string, unknown>) => {
      // Optimistic local update
      setScenarios((prev) => prev.map((s) => (s.id === activeId ? { ...s, config } : s)))
      // Invalidate this scenario's result
      setAllResults((prev) => {
        const { [activeId]: _, ...rest } = prev
        return rest
      })

      // Debounced save
      if (configSaveRef.current) clearTimeout(configSaveRef.current.timer)
      configSaveRef.current = {
        scenarioId: activeId,
        config,
        timer: setTimeout(() => {
          configSaveRef.current = null
          updateMutation.mutate({ id: activeId, config })
        }, DEBOUNCE_MS),
      }
    },
    [activeId, updateMutation]
  )

  const handleSelectScenario = useCallback(
    (id: number) => {
      flushPendingSave()
      setActiveId(id)
      setTab((prev) => {
        if (prev === 1 && allResults[id]?.status !== 'ok') return 0
        return prev
      })
    },
    [allResults, flushPendingSave]
  )

  const handleCompareSelect = useCallback(
    (id: number) => {
      setActiveId(id)
      if (allResults[id]?.status === 'ok') setTab(1)
      else setTab(0)
    },
    [allResults]
  )

  const handleCreateScenario = useCallback(
    (name: string, sourceId: number | null) => {
      const source = sourceId != null ? scenarios.find((s) => s.id === sourceId) : activeScenario
      const sourceConfig = source
        ? JSON.parse(JSON.stringify(source.config))
        : { ...EXAMPLE_CONFIG }
      createMutation.mutate(
        { name, config: sourceConfig },
        {
          onSuccess: (created) => {
            setScenarios((prev) => [...prev, created])
            setActiveId(created.id)
            setTab(0)
          },
        }
      )
    },
    [scenarios, activeScenario, createMutation]
  )

  const handleCloneScenario = useCallback(
    (id: number) => {
      const source = scenarios.find((s) => s.id === id)
      if (!source) return
      createMutation.mutate(
        { name: `${source.name} (copy)`, config: JSON.parse(JSON.stringify(source.config)) },
        {
          onSuccess: (created) => {
            setScenarios((prev) => [...prev, created])
            setActiveId(created.id)
            setTab(0)
          },
        }
      )
    },
    [scenarios, createMutation]
  )

  const handleRenameScenario = useCallback(
    (id: number, name: string) => {
      setScenarios((prev) => prev.map((s) => (s.id === id ? { ...s, name } : s)))
      updateMutation.mutate({ id, name })
    },
    [updateMutation]
  )

  const handleDeleteScenario = useCallback(
    (id: number) => {
      setScenarios((prev) => {
        const next = prev.filter((s) => s.id !== id)
        if (next.length === 0) return prev
        if (activeId === id) {
          setActiveId(next[0].id)
          setTab(0)
        }
        return next
      })
      setAllResults((prev) => {
        const { [id]: _, ...rest } = prev
        return rest
      })
      deleteMutation.mutate(id)
    },
    [activeId, deleteMutation]
  )

  // Single scenario run
  const handleRun = useCallback(() => {
    if (!activeScenario) return
    flushPendingSave()
    simulate.mutate(prepareConfigForSimulation(activeScenario.config), {
      onSuccess: (data) => {
        setAllResults((prev) => ({
          ...prev,
          [activeId]: { status: 'ok', data },
        }))
        setTab(1)
      },
    })
  }, [activeScenario, simulate, activeId, flushPendingSave])

  // Run all scenarios in parallel
  const handleRunAll = useCallback(async () => {
    flushPendingSave()
    setRunAllRunning(true)

    const settled = await Promise.allSettled(
      scenarios.map((s) =>
        apiClient
          .post<SimulationResponse>('/retirement/simulate', prepareConfigForSimulation(s.config), {
            timeout: 45_000,
          })
          .then((r) => ({ id: s.id, data: r.data }))
      )
    )

    const newResults: Record<number, ScenarioResult> = {}
    for (let i = 0; i < settled.length; i++) {
      const entry = settled[i]
      const scenarioId = scenarios[i].id
      if (entry.status === 'fulfilled') {
        newResults[scenarioId] = { status: 'ok', data: entry.value.data }
      } else {
        newResults[scenarioId] = {
          status: 'error',
          message: entry.reason?.message ?? 'Simulation failed',
        }
      }
    }

    setAllResults(newResults)
    setRunAllRunning(false)

    const successes = Object.values(newResults).filter((r) => r.status === 'ok').length
    if (successes >= 2) setTab(2)
    else if (successes === 1) setTab(1)
  }, [scenarios, flushPendingSave])

  const errorMessage = simulate.error
    ? (simulate.error as Error).message?.includes('timeout')
      ? 'Simulation took too long. Try a smaller max retire age, or check the server logs.'
      : `Simulation failed: ${(simulate.error as Error).message}`
    : null

  const activeRunAllError = activeResult?.status === 'error' ? activeResult.message : null

  // ----- loading state -----
  if (isLoading || !initialized) {
    return (
      <Box>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
          Retirement Calculator
        </Typography>
        <Skeleton variant="rounded" height={40} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={400} />
      </Box>
    )
  }

  return (
    <Box>
      <Box
        sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}
      >
        <Typography variant="h5" fontWeight={700}>
          Retirement Calculator
        </Typography>
      </Box>

      <ScenarioBar
        scenarios={scenarios}
        activeId={activeId}
        onSelect={handleSelectScenario}
        onCreate={handleCreateScenario}
        onClone={handleCloneScenario}
        onRename={handleRenameScenario}
        onDelete={handleDeleteScenario}
      />

      {/* Run All button */}
      <Box sx={{ display: 'flex', alignItems: 'center', mt: 2, gap: 1 }}>
        <Button
          variant="outlined"
          size="small"
          onClick={handleRunAll}
          disabled={runAllRunning || simulate.isPending}
          startIcon={runAllRunning ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
        >
          {runAllRunning ? `Running ${scenarios.length} scenarios...` : `Run All (${scenarios.length})`}
        </Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mt: 2, mb: 1, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Config" />
        <Tab label="Results" disabled={!activeData} />
        <Tab label="Compare" disabled={okCount < 2} />
      </Tabs>

      {/* Config Tab */}
      <TabPanel value={tab} index={0}>
        {errorMessage && <AlertCard severity="error" title="Simulation Error" message={errorMessage} />}
        {activeRunAllError && !errorMessage && (
          <AlertCard severity="error" title="Simulation Error" message={activeRunAllError} />
        )}
        {activeScenario && (
          <ConfigEditor
            config={activeScenario.config}
            onConfigChange={handleConfigChange}
            onRun={handleRun}
            isRunning={simulate.isPending}
          />
        )}
      </TabPanel>

      {/* Results Tab */}
      <TabPanel value={tab} index={1}>
        {activeData && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {activeData.status === 'impossible' && (
              <AlertCard
                severity="warning"
                title="Cannot Retire"
                message={`Cannot retire before age ${activeData.summary.fire_age.toFixed(0)} with current parameters. Showing forced retirement scenario.`}
              />
            )}

            <ResultsOverview summary={activeData.summary} impossible={activeData.status === 'impossible'} />

            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Net Worth Trajectory
                </Typography>
                <NetWorthChart
                  monthly={activeData.monthly}
                  summary={activeData.summary}
                  milestones={activeData.milestones}
                />
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Asset Composition
                </Typography>
                <AssetCompositionChart monthly={activeData.monthly} persons={activeData.persons} />
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Monthly Income Sources
                </Typography>
                <IncomeSourcesChart monthly={activeData.monthly} persons={activeData.persons} />
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Post-FIRE Cashflow Breakdown
                </Typography>
                <CashflowTable monthly={activeData.monthly} summary={activeData.summary} persons={activeData.persons} />
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Milestones
                </Typography>
                <MilestonesList milestones={activeData.milestones} />
              </CardContent>
            </Card>
          </Box>
        )}
        {!activeData && (
          <Box sx={{ py: 8, textAlign: 'center' }}>
            <Typography color="text.secondary">Run simulation to see results</Typography>
          </Box>
        )}
      </TabPanel>

      {/* Compare Tab */}
      <TabPanel value={tab} index={2}>
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Scenario Comparison
            </Typography>
            <ScenarioCompare scenarios={scenarios} allResults={allResults} onSelectScenario={handleCompareSelect} />
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  )
}
