import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { API, RecommendationResult, SimulationResult } from '../api'
import {
  Award,
  Download,
  TrendingUp,
  Sun,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Sparkles,
  Layers,
  ThermometerSnowflake,
  RefreshCw,
  Flame,
  Trash2,
  Search,
} from 'lucide-react'
import Plot from 'react-plotly.js'

/* ─── Shared Dark Plotly Theme ─────────────────── */
const darkChartLayout: any = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: '#0D0F13',
  font: { color: '#94A3B8', size: 11, family: 'Inter, system-ui, sans-serif' },
  xaxis: {
    gridcolor: '#1A1D24',
    tickcolor: '#282C36',
    linecolor: '#282C36',
    zerolinecolor: '#1A1D24'
  },
  yaxis: {
    gridcolor: '#1A1D24',
    tickcolor: '#282C36',
    linecolor: '#282C36',
    zerolinecolor: '#1A1D24'
  },
  legend: {
    bgcolor: 'rgba(13, 21, 34, 0.85)',
    bordercolor: '#20242C',
    borderwidth: 1,
    font: { color: '#CBD5E1', size: 10 }
  }
}

/* Clean high-contrast engineering trace palette (Blue & White theme) */
const colorfulTraces = [
  { color: '#38BDF8', width: 2.8 }, // Sky Blue (Optimal)
  { color: '#FFFFFF', width: 2.4 }, // Crisp Pure White
  { color: '#60A5FA', width: 2.2 }, // Soft Blue
  { color: '#93C5FD', width: 2.2 }, // Ice Blue
  { color: '#34D399', width: 2.2 }, // Emerald/Mint
  { color: '#06B6D4', width: 2.0 }, // Cyan
  { color: '#E2E8F0', width: 2.0 }, // Platinum White
  { color: '#3B82F6', width: 2.0 }, // Cobalt Blue
]

export const RecommendationDashboard: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const configId = searchParams.get('config_id')
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(configId)
  const [configList, setConfigList] = useState<Array<{ id: string; name: string; created_at: string; completed_jobs: number }>>([])
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null)
  const [recResult, setRecResult] = useState<SimulationResult | null>(null)
  const [allResults, setAllResults] = useState<Record<string, SimulationResult>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'energy' | 'heatflow' | 'matrix'>('overview')
  const [comfortMin, setComfortMin] = useState<number>(18)
  const [comfortMax, setComfortMax] = useState<number>(27)
  const [savedSearch, setSavedSearch] = useState('')
  const [deletingConfigId, setDeletingConfigId] = useState<string | null>(null)

  const handleDeleteConfig = async (e: React.MouseEvent, targetId: string, targetName: string) => {
    e.stopPropagation()
    if (!window.confirm(`Are you sure you want to delete simulation "${targetName}"?\nThis will remove all associated solver jobs, thermal results, and reports.`)) {
      return
    }
    setDeletingConfigId(targetId)
    try {
      await API.deleteConfig(targetId)
      const res = await API.listConfigs()
      setConfigList(res.data)
      if (selectedConfigId === targetId) {
        if (res.data.length > 0) {
          const next = res.data[0]
          setSelectedConfigId(next.id)
          navigate(`/recommendations?config_id=${next.id}`)
          loadRecommendation(next.id)
        } else {
          setSelectedConfigId(null)
          setRecommendation(null)
          setRecResult(null)
          setAllResults({})
        }
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete simulation.')
    } finally {
      setDeletingConfigId(null)
    }
  }

  const filteredConfigList = configList.filter(c =>
    (c.name || '').toLowerCase().includes(savedSearch.toLowerCase()) ||
    (c.created_at || '').toLowerCase().includes(savedSearch.toLowerCase())
  )

  useEffect(() => {
    API.listConfigs().then(res => setConfigList(res.data)).catch(() => {})
    if (configId) {
      setSelectedConfigId(configId)
      loadRecommendation(configId)
    } else {
      API.getLatestConfig()
        .then(res => {
          if (res.data?.config_id) {
            setSelectedConfigId(res.data.config_id)
            loadRecommendation(res.data.config_id)
          } else {
            setLoading(false)
          }
        })
        .catch(() => setLoading(false))
    }
  }, [configId])

  const loadRecommendation = async (targetId: string) => {
    setLoading(true)
    setError(null)
    try {
      const recRes = await API.recommend(targetId)
      const recData = recRes.data
      setRecommendation(recData)
      if (recData.comfort_min_temp !== undefined && recData.comfort_min_temp !== null) {
        setComfortMin(recData.comfort_min_temp)
      }
      if (recData.comfort_max_temp !== undefined && recData.comfort_max_temp !== null) {
        setComfortMax(recData.comfort_max_temp)
      }
      if (recData.recommended_job_id) {
        const resultRes = await API.getResult(recData.recommended_job_id)
        setRecResult(resultRes.data)
      }
      const resultsMap: Record<string, SimulationResult> = {}
      for (const row of recData.comparison_table) {
        try {
          const r = await API.getResult(row.job_id)
          resultsMap[row.job_id] = r.data
        } catch { /* ignore */ }
      }
      setAllResults(resultsMap)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate recommendations. Ensure simulations have completed.')
    } finally {
      setLoading(false)
    }
  }

  const handleExportPdf = async () => {
    if (!recommendation) return
    setGeneratingReport(true)
    try {
      const res = await API.generateReport(recommendation.recommendation_id)
      const downloadUrl = API.downloadReport(res.data.report_id)
      window.open(downloadUrl, '_blank')
    } catch (err: any) {
      alert('Report generation failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setGeneratingReport(false)
    }
  }

  const formatDate = (isoString?: string) => {
    if (!isoString) return ''
    try {
      const d = new Date(isoString)
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    } catch {
      return isoString
    }
  }

  const breakdown = recommendation?.scores_breakdown || {}

  // Dynamically compute comfort compliance against the active comfort temperature envelope
  const calculateComfort = (temps?: number[] | null) => {
    if (!temps || temps.length === 0) return { hours: 0, percentage: 0 }
    const inComfort = temps.filter(t => t >= comfortMin && t <= comfortMax).length
    return {
      hours: inComfort,
      percentage: (inComfort / temps.length) * 100,
    }
  }

  const recComfort = calculateComfort(recResult?.temp_internal)

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 fade-in">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1A1D24] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-white mb-1">
            <span className="w-2 h-2 rounded-full bg-white"></span>
            ANSYS MAPDL Thermal Decision Support
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Results & Recommendation Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Comparative performance matrix, diurnal temperatures, and solar physics evaluation.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 flex-wrap">
          {recommendation && (
            <button
              onClick={handleExportPdf}
              disabled={generatingReport}
              className="btn btn-primary text-xs flex items-center gap-2"
            >
              {generatingReport ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Download size={14} />
              )}
              <span>Export Engineering PDF</span>
            </button>
          )}

          <button
            onClick={() => navigate('/')}
            className="btn btn-secondary text-xs flex items-center gap-1.5"
          >
            <span>+ Launch New Simulation</span>
          </button>
        </div>
      </div>

      {/* Prominent Saved Simulations Catalog Section */}
      <div className="mono-card p-5 space-y-4 bg-[#121418] border border-[#20242C]">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-white/10 border border-white/20 text-white">
              <Layers size={16} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-white tracking-wide">
                  Saved Simulations
                </h2>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#1A1D24] text-slate-300 border border-[#282C36]">
                  {configList.length} total
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Select any saved simulation batch below to load and view its complete analysis and recommendations.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={savedSearch}
                onChange={e => setSavedSearch(e.target.value)}
                placeholder="Search simulations by name or date..."
                className="input pl-8 py-1 text-xs w-full"
              />
            </div>
            <button
              onClick={() => {
                API.listConfigs().then(res => setConfigList(res.data)).catch(() => {})
              }}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 px-2.5 py-1.5 rounded bg-[#101216] border border-[#20242C] transition-colors shrink-0 cursor-pointer"
            >
              <RefreshCw size={12} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {configList.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400 bg-[#0D0F13] rounded-xl border border-[#1A1D24] space-y-2">
            <p>No saved simulations found yet.</p>
            <button
              onClick={() => navigate('/')}
              className="text-white hover:text-sky-300 hover:underline font-medium"
            >
              Configure and solve your first simulation batch in the Simulation Studio →
            </button>
          </div>
        ) : filteredConfigList.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400 bg-[#0D0F13] rounded-xl border border-[#1A1D24]">
            No simulations matching "{savedSearch}".
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 max-h-72 overflow-y-auto pr-1">
            {filteredConfigList.map((c) => {
              const isSelected = c.id === selectedConfigId
              return (
                <div
                  key={c.id}
                  onClick={() => {
                    if (c.id !== selectedConfigId) {
                      setSelectedConfigId(c.id)
                      navigate(`/recommendations?config_id=${c.id}`)
                      loadRecommendation(c.id)
                    }
                  }}
                  className={`flex flex-col text-left p-3.5 rounded-xl border transition-all cursor-pointer relative group ${
                    isSelected
                      ? 'bg-[#152238] border-white shadow-md ring-1 ring-white/30 text-white'
                      : 'bg-[#101216] border-[#20242C] hover:border-slate-500 hover:bg-[#181B21] text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <span
                      className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded-md border ${
                        c.completed_jobs > 0
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {c.completed_jobs} completed
                    </span>

                    <div className="flex items-center gap-1.5">
                      {isSelected ? (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-white bg-white/10 border border-white/20 px-2 py-0.5 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                          Selected
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500 group-hover:text-slate-400">
                          Click to view
                        </span>
                      )}
                      <button
                        type="button"
                        title="Delete simulation batch"
                        onClick={(e) => handleDeleteConfig(e, c.id, c.name)}
                        disabled={deletingConfigId === c.id}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/15 transition-colors cursor-pointer"
                      >
                        {deletingConfigId === c.id ? (
                          <RefreshCw size={12} className="animate-spin text-rose-400" />
                        ) : (
                          <Trash2 size={12} />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="font-semibold text-xs text-slate-100 group-hover:text-white line-clamp-2 leading-snug">
                    {c.name}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-3 pt-2 border-t border-[#1A1D24]/80 font-mono">
                    <span>{formatDate(c.created_at)}</span>
                    <span className="text-slate-500">MAPDL</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="mono-card p-16 text-center space-y-4 bg-[#121418] border border-[#20242C]">
          <RefreshCw className="animate-spin mx-auto text-white" size={32} />
          <h2 className="text-xl font-bold text-white">
            Synthesizing Thermal Simulation Results...
          </h2>
          <p className="text-sm text-slate-400">
            Running weighted decision-support ranking and diurnal analysis for the selected simulation.
          </p>
        </div>
      ) : error || !recommendation ? (
        <div className="p-12 max-w-xl mx-auto text-center space-y-5 mono-card my-6 bg-[#121418] border border-[#20242C]">
          <Award size={40} className="mx-auto text-slate-500" />
          <h2 className="text-xl font-bold text-white">
            Simulation Results Unavailable
          </h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            {error || 'No completed simulation jobs found for this batch. Please select another saved simulation above or launch a run from the Simulation Studio.'}
          </p>
          <button onClick={() => navigate('/')} className="btn btn-primary text-xs">
            Launch New Simulation
          </button>
        </div>
      ) : (
        <>

      {/* Recommended Configuration — Winner Card */}
      <div className="mono-card p-6 space-y-6 bg-[#121418] border border-[#20242C]">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              <Award size={13} />
              #1 OPTIMAL ARCHITECTURAL CONFIGURATION
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
              {recommendation.recommended_design}
              <span className="text-slate-400 mx-2 font-normal">+</span>
              <span className="text-white">{recommendation.recommended_material}</span>
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
              Validated through transient FEA solved in local ANSYS MAPDL across{' '}
              {recommendation.total_completed} evaluated design and envelope iterations.
            </p>
          </div>

          {/* Score Badge */}
          <div className="flex items-center gap-4 shrink-0 bg-[#0D0F13] border border-[#20242C] rounded-xl px-6 py-4 text-center">
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Thermal Performance Score
              </span>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-extrabold text-white leading-none">
                  {recommendation.overall_score.toFixed(1)}
                </span>
                <span className="text-xs text-slate-400 font-mono">/ 100</span>
              </div>
            </div>
          </div>
        </div>

        {/* Engineering Rationale Bullet Points */}
        <div className="border-t border-[#20242C] pt-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
            <Sparkles size={14} className="text-white" />
            Decision Rationale
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {recommendation.explanation.map((exp, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-3 rounded-lg bg-[#0D0F13] border border-[#20242C] text-xs text-slate-200"
              >
                <CheckCircle2 size={15} className="text-emerald-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{exp}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sub-Score Breakdown Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {[
          {
            key: 'comfort_compliance',
            label: 'Comfort Compliance',
            score: breakdown.comfort_compliance ?? 75.0,
            icon: ShieldCheck,
            color: 'bg-emerald-500',
            text: 'text-emerald-400',
            desc: '35% weight',
            raw: `${recResult?.temp_internal?.length ? recComfort.percentage.toFixed(1) : (recResult?.comfort_percentage?.toFixed(1) ?? '—')}% in ${comfortMin}–${comfortMax}°C`,
          },
          { key: 'nighttime_retention', label: 'Night Retention', score: breakdown.nighttime_retention ?? 70.0, icon: ThermometerSnowflake, color: 'bg-sky-500', text: 'text-white', desc: '25% weight', raw: recResult?.nighttime_avg_temp ? `Avg ${recResult.nighttime_avg_temp.toFixed(1)}°C` : 'Night cushion' },
          { key: 'heat_loss', label: 'Loss Minimization', score: breakdown.heat_loss ?? 80.0, icon: Zap, color: 'bg-teal-500', text: 'text-teal-400', desc: '20% weight', raw: recResult?.total_heat_loss_kwh ? `${recResult.total_heat_loss_kwh.toFixed(1)} kWh` : 'Insulation' },
          { key: 'solar_gain', label: 'Solar Heat Gain', score: breakdown.solar_gain ?? 65.0, icon: Sun, color: 'bg-white', text: 'text-white', desc: '15% weight', raw: recResult?.total_solar_gain_kwh ? `${recResult.total_solar_gain_kwh.toFixed(1)} kWh` : 'Solar mass' },
          { key: 'temperature_stability', label: 'Diurnal Stability', score: breakdown.temperature_stability ?? 85.0, icon: TrendingUp, color: 'bg-rose-500', text: 'text-rose-400', desc: '5% weight', raw: recResult?.temp_fluctuation_std ? `σ = ${recResult.temp_fluctuation_std.toFixed(1)}°C` : 'Thermal damping' },
        ].map(item => {
          const Icon = item.icon
          return (
            <div key={item.key} className="mono-card p-4 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <div className={`p-1.5 rounded-md bg-[#1A1D24] ${item.text}`}>
                  <Icon size={14} />
                </div>
                <span className="text-[11px] text-slate-400 font-mono">
                  {item.desc}
                </span>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-300 block">{item.label}</span>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-2xl font-bold text-white leading-none">
                    {item.score.toFixed(1)}
                  </span>
                  <span className="text-xs text-slate-500">/ 100</span>
                </div>
                <span className="text-[11px] text-slate-400 block mt-1">
                  {item.raw}
                </span>
              </div>
              <div className="w-full bg-[#1A1D24] h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${item.color}`}
                  style={{ width: `${Math.min(100, item.score)}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Tabs + Charts Section */}
      <div className="mono-card p-0 overflow-hidden">
        {/* Tab Navigation */}
        <div className="flex items-center gap-1 border-b border-[#20242C] px-4 pt-2 bg-[#101216] overflow-x-auto">
          {[
            { id: 'overview', label: 'Diurnal Curves', icon: TrendingUp },
            { id: 'energy', label: 'Solar Energy', icon: Sun },
            { id: 'heatflow', label: 'Heat Flow & Loss', icon: Flame },
            { id: 'matrix', label: 'Comparison Matrix', icon: Layers },
          ].map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'border-white text-white bg-white/10'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#181B21]'
                }`}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>

        <div className="p-6">
          {/* TAB 1: Diurnal Temperature Curves */}
          {activeTab === 'overview' && (
            <div className="space-y-6 fade-in">
              {/* Comfort Envelope Control Banner */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-[#0D0F13] border border-[#20242C]">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                    <ShieldCheck size={16} />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-white block">
                      Occupant Thermal Comfort Envelope
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Calculated from the comfort thresholds set for this simulation batch. You can also adjust limits below to re-evaluate compliance live.
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <div className="flex items-center gap-1.5 bg-[#161920] border border-[#282C36] rounded-lg px-2.5 py-1.5">
                    <span className="text-[11px] font-medium text-slate-400">Min:</span>
                    <input
                      type="number"
                      value={comfortMin}
                      onChange={e => setComfortMin(parseFloat(e.target.value) || 0)}
                      step="0.5"
                      className="w-14 bg-transparent text-white font-mono font-bold text-xs text-center outline-none"
                    />
                    <span className="text-[11px] font-medium text-slate-400">°C</span>
                  </div>
                  <span className="text-slate-500 font-bold">—</span>
                  <div className="flex items-center gap-1.5 bg-[#161920] border border-[#282C36] rounded-lg px-2.5 py-1.5">
                    <span className="text-[11px] font-medium text-slate-400">Max:</span>
                    <input
                      type="number"
                      value={comfortMax}
                      onChange={e => setComfortMax(parseFloat(e.target.value) || 0)}
                      step="0.5"
                      className="w-14 bg-transparent text-white font-mono font-bold text-xs text-center outline-none"
                    />
                    <span className="text-[11px] font-medium text-slate-400">°C</span>
                  </div>
                  {(recommendation.comfort_min_temp !== undefined && (comfortMin !== recommendation.comfort_min_temp || comfortMax !== recommendation.comfort_max_temp)) && (
                    <button
                      onClick={() => {
                        setComfortMin(recommendation.comfort_min_temp ?? 18)
                        setComfortMax(recommendation.comfort_max_temp ?? 27)
                      }}
                      className="text-[11px] text-white hover:underline px-2 py-1 cursor-pointer"
                      title="Reset to batch configured values"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {/* Summary stat cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: 'Lowest Indoor Temp', value: recResult?.min_internal_temp?.toFixed(1), unit: '°C', sub: 'Sub-zero night trough', color: 'text-white' },
                  { label: 'Average Indoor Temp', value: recResult?.avg_internal_temp?.toFixed(1), unit: '°C', sub: '48-hour diurnal mean', color: 'text-emerald-400' },
                  { label: 'Peak Daytime Temp', value: recResult?.max_internal_temp?.toFixed(1), unit: '°C', sub: 'Solar thermal uplift', color: 'text-white' },
                  { label: `Comfort Hours (${comfortMin}–${comfortMax}°C)`, value: (recResult?.temp_internal?.length ? recComfort.hours : (recResult?.comfort_hours ?? 0)).toFixed(0), unit: ' hrs', sub: `${(recResult?.temp_internal?.length ? recComfort.percentage : (recResult?.comfort_percentage ?? 0)).toFixed(1)}% in comfort band`, color: 'text-teal-400' },
                ].map(m => (
                  <div key={m.label} className="p-4 rounded-lg bg-[#0D0F13] border border-[#20242C]">
                    <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-medium">{m.label}</span>
                    <div className="mt-1 flex items-baseline gap-1">
                      <span className={`text-2xl font-bold ${m.color}`}>
                        {m.value ?? '—'}
                      </span>
                      <span className="text-xs text-slate-400">{m.unit}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 block mt-1">{m.sub}</span>
                  </div>
                ))}
              </div>

              {/* Colorful Overlaid Plot */}
              <div className="p-5 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-sm text-white">
                      Comparative Diurnal Temperature Trajectories — All Evaluated Configurations
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Transient internal temperatures modeled in ANSYS MAPDL compared against outdoor ambient conditions.
                    </p>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-white/10 border border-white/20 text-white text-xs font-mono font-medium">
                    {recommendation.comparison_table.length} configurations
                  </span>
                </div>

                <Plot
                  data={[
                    // Ambient line (slate, dashed)
                    {
                      x: recResult?.timestamps || [],
                      y: recResult?.temp_ambient || [],
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Outdoor Ambient (°C)',
                      line: { color: '#94A3B8', width: 2, dash: 'dash' },
                    },
                    // Each configuration with vibrant distinct colors
                    ...recommendation.comparison_table.map((row, idx) => {
                      const r = allResults[row.job_id] || (row.is_recommended ? recResult : null)
                      const t = colorfulTraces[idx % colorfulTraces.length]
                      return {
                        x: r?.timestamps || recResult?.timestamps || [],
                        y: r?.temp_internal || [],
                        type: 'scatter',
                        mode: 'lines',
                        name: `${row.design_name} + ${row.material_name}${row.is_recommended ? ' ★ [Winner]' : ''}`,
                        line: {
                          color: row.is_recommended ? '#38BDF8' : t.color,
                          width: row.is_recommended ? 3.2 : t.width,
                        },
                      }
                    }),
                    // Comfort boundaries
                    {
                      x: recResult?.timestamps || [],
                      y: Array((recResult?.timestamps || []).length).fill(comfortMin),
                      type: 'scatter',
                      mode: 'lines',
                      name: `Lower Comfort Limit (${comfortMin}°C)`,
                      line: { color: 'rgba(52, 211, 153, 0.75)', width: 1.5, dash: 'dot' },
                    },
                    {
                      x: recResult?.timestamps || [],
                      y: Array((recResult?.timestamps || []).length).fill(comfortMax),
                      type: 'scatter',
                      mode: 'lines',
                      name: `Upper Comfort Limit (${comfortMax}°C)`,
                      line: { color: 'rgba(251, 113, 133, 0.75)', width: 1.5, dash: 'dot' },
                    },
                  ]}
                  layout={{
                    ...darkChartLayout,
                    autosize: true,
                    height: 420,
                    margin: { l: 50, r: 20, t: 15, b: 65 },
                    showlegend: true,
                    legend: { orientation: 'h', y: -0.28 },
                    xaxis: { ...darkChartLayout.xaxis, tickformat: '%d %b %H:%M' },
                    yaxis: { ...darkChartLayout.yaxis, title: 'Temperature (°C)' },
                  }}
                  config={{ responsive: true, displayModeBar: true }}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          )}

          {/* TAB 2: Solar Energy */}
          {activeTab === 'energy' && (
            <div className="space-y-6 fade-in">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: 'Peak Solar Irradiance', value: recResult?.solar_radiation?.length ? `${Math.max(...recResult.solar_radiation).toFixed(0)} W/m²` : '—', sub: 'Incident horizontal flux' },
                  { label: 'Peak Thermal Power', value: recResult?.solar_heat_gain?.length ? `${(Math.max(...recResult.solar_heat_gain) / 1000).toFixed(2)} kW` : '—', sub: 'Total solar power entering' },
                  { label: 'Total Solar Harvested', value: recResult?.total_solar_gain_kwh ? `${recResult.total_solar_gain_kwh.toFixed(2)} kWh` : '—', sub: '48-hr absorbed thermal energy' },
                  { label: 'Avoided Auxiliary Heat', value: recResult?.total_solar_gain_kwh ? `${(recResult.total_solar_gain_kwh * 0.85).toFixed(2)} kWh` : '—', sub: 'Equivalent heating offset' },
                ].map(m => (
                  <div key={m.label} className="p-4 rounded-lg bg-[#0D0F13] border border-[#20242C]">
                    <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-medium">{m.label}</span>
                    <span className="text-xl font-bold text-white block mt-1">{m.value}</span>
                    <span className="text-[11px] text-slate-500 block mt-1">{m.sub}</span>
                  </div>
                ))}
              </div>

              {/* Solar Flux Graph */}
              <div className="p-5 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-3">
                <h3 className="font-semibold text-sm text-white">Solar Flux vs Absorbed Heat vs Power Delivery</h3>
                <Plot
                  data={[
                    {
                      x: recResult?.timestamps || [],
                      y: recResult?.solar_radiation || [],
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Incident Solar G (W/m²)',
                      line: { color: '#FFFFFF', width: 2.5 },
                      yaxis: 'y1'
                    },
                    {
                      x: recResult?.timestamps || [],
                      y: (recResult?.solar_radiation || []).map(g => g * 0.72),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Absorbed Flux q = α·G (W/m²)',
                      line: { color: '#93C5FD', width: 2, dash: 'dash' as any },
                      yaxis: 'y1'
                    },
                    {
                      x: recResult?.timestamps || [],
                      y: (recResult?.solar_heat_gain || []).map(w => w / 1000),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Gross Thermal Power (kW)',
                      line: { color: '#38BDF8', width: 2.5 },
                      yaxis: 'y2'
                    },
                  ]}
                  layout={{
                    ...darkChartLayout,
                    autosize: true,
                    height: 360,
                    margin: { l: 55, r: 55, t: 15, b: 65 },
                    showlegend: true,
                    legend: { orientation: 'h', y: -0.28 },
                    xaxis: { ...darkChartLayout.xaxis, tickformat: '%d %b %H:%M' },
                    yaxis: { ...darkChartLayout.yaxis, title: 'Solar Flux (W/m²)' },
                    yaxis2: {
                      title: 'Thermal Power (kW)',
                      overlaying: 'y',
                      side: 'right',
                      gridcolor: '#1A1D24',
                      tickcolor: '#282C36',
                      linecolor: '#282C36',
                      font: { color: '#38BDF8' }
                    },
                  }}
                  config={{ responsive: true, displayModeBar: true }}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Cumulative Solar Harvest Area Chart */}
              <div className="p-5 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-3">
                <h3 className="font-semibold text-sm text-white">Cumulative Solar Thermal Harvest (kWh)</h3>
                <Plot
                  data={[{
                    x: recResult?.timestamps || [],
                    y: (() => {
                      let acc = 0
                      return (recResult?.solar_heat_gain || []).map(w => {
                        acc += w / 1000
                        return parseFloat(acc.toFixed(2))
                      })
                    })(),
                    type: 'scatter',
                    mode: 'lines',
                    fill: 'tozeroy',
                    fillcolor: 'rgba(245, 158, 11, 0.15)',
                    name: 'Cumulative Energy (kWh)',
                    line: { color: '#F59E0B', width: 2.5 },
                  }]}
                  layout={{
                    ...darkChartLayout,
                    autosize: true,
                    height: 300,
                    margin: { l: 55, r: 20, t: 15, b: 50 },
                    showlegend: true,
                    legend: { orientation: 'h', y: -0.25 },
                    xaxis: { ...darkChartLayout.xaxis, tickformat: '%d %b %H:%M' },
                    yaxis: { ...darkChartLayout.yaxis, title: 'Cumulative Energy (kWh)' }
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          )}

          {/* TAB 3: Heat Flow & Loss */}
          {activeTab === 'heatflow' && (
            <div className="space-y-6 fade-in">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: 'Total Envelope Heat Loss', value: `${recResult?.total_heat_loss_kwh?.toFixed(2) ?? '—'} kWh`, sub: 'Conduction & boundary convection', color: 'text-rose-400' },
                  { label: 'Peak Thermal Uplift (ΔT)', value: recResult?.temp_internal && recResult?.temp_ambient ? `+${Math.max(...recResult.temp_internal.map((t, i) => t - (recResult.temp_ambient?.[i] ?? 0))).toFixed(1)} °C` : '—', sub: 'Max elevation above ambient', color: 'text-white' },
                  { label: 'Overnight ΔT Retention', value: recResult?.nighttime_min_temp && recResult?.temp_ambient ? `+${(recResult.nighttime_min_temp - Math.min(...recResult.temp_ambient)).toFixed(1)} °C` : '—', sub: 'Thermal mass retention', color: 'text-emerald-400' },
                ].map(m => (
                  <div key={m.label} className="p-4 rounded-lg bg-[#0D0F13] border border-[#20242C]">
                    <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-medium">{m.label}</span>
                    <span className={`text-2xl font-bold block mt-1 ${m.color}`}>{m.value}</span>
                    <span className="text-[11px] text-slate-500 block mt-1">{m.sub}</span>
                  </div>
                ))}
              </div>

              <div className="p-5 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-3">
                <h3 className="font-semibold text-sm text-white">Thermal Balance: Indoor Uplift vs Envelope Loss vs Solar Input</h3>
                <Plot
                  data={[
                    {
                      x: recResult?.timestamps || [],
                      y: recResult?.temp_internal && recResult?.temp_ambient
                        ? recResult.temp_internal.map((t, i) => parseFloat((t - (recResult.temp_ambient?.[i] ?? 0)).toFixed(2)))
                        : [],
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Indoor Uplift ΔT (°C)',
                      line: { color: '#38BDF8', width: 2.8 },
                      yaxis: 'y1'
                    },
                    {
                      x: recResult?.timestamps || [],
                      y: (() => {
                        if (recResult?.total_heat_flow?.length && Math.max(...recResult.total_heat_flow) > 0)
                          return recResult.total_heat_flow
                        return (recResult?.temp_internal || []).map((t, i) =>
                          parseFloat((Math.max(0, t - (recResult?.temp_ambient?.[i] ?? -15)) * 85).toFixed(1))
                        )
                      })(),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Envelope Heat Loss (W)',
                      line: { color: '#F87171', width: 2.2, dash: 'dash' as any },
                      yaxis: 'y2'
                    },
                    {
                      x: recResult?.timestamps || [],
                      y: recResult?.solar_heat_gain || [],
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Solar Heat Gain (W)',
                      line: { color: '#FBBF24', width: 2.2, dash: 'dot' as any },
                      yaxis: 'y2'
                    },
                  ]}
                  layout={{
                    ...darkChartLayout,
                    autosize: true,
                    height: 380,
                    margin: { l: 50, r: 55, t: 15, b: 70 },
                    showlegend: true,
                    legend: { orientation: 'h', y: -0.28 },
                    xaxis: { ...darkChartLayout.xaxis, tickformat: '%d %b %H:%M' },
                    yaxis: { ...darkChartLayout.yaxis, title: 'ΔT (°C)' },
                    yaxis2: {
                      title: 'Thermal Power (W)',
                      overlaying: 'y',
                      side: 'right',
                      gridcolor: '#1A1D24',
                      tickcolor: '#282C36',
                      linecolor: '#282C36'
                    }
                  }}
                  config={{ responsive: true, displayModeBar: true }}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          )}



          {/* TAB 5: Full Matrix Table */}
          {activeTab === 'matrix' && (
            <div className="overflow-x-auto fade-in rounded-xl border border-[#20242C]">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Design Geometry</th>
                    <th>Wall Material</th>
                    <th>Avg Indoor Temp</th>
                    <th>Min Indoor Temp</th>
                    <th>Comfort Compliance ({comfortMin}–${comfortMax}°C)</th>
                    <th>Solar Gain (kWh)</th>
                    <th>Performance Score</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendation.comparison_table.map((row, idx) => (
                    <tr key={row.job_id} className={row.is_recommended ? 'highlighted' : ''}>
                      <td>
                        {row.is_recommended ? (
                          <span className="badge badge-completed flex items-center gap-1">
                            <Award size={12} />
                            #1 Optimal
                          </span>
                        ) : (
                          <span className="font-mono text-xs text-slate-400">#{idx + 1}</span>
                        )}
                      </td>
                      <td className="font-semibold text-white">{row.design_name}</td>
                      <td className="font-mono text-xs text-slate-300">{row.material_name}</td>
                      <td className="font-mono text-slate-200">{row.avg_internal_temp?.toFixed(1) ?? '—'} °C</td>
                      <td className="font-mono text-slate-200">{row.min_internal_temp?.toFixed(1) ?? '—'} °C</td>
                      <td className="font-mono text-emerald-400 font-semibold">
                        {(() => {
                          const r = allResults[row.job_id] || (row.is_recommended ? recResult : null)
                          const pct = r?.temp_internal?.length
                            ? calculateComfort(r.temp_internal).percentage
                            : row.comfort_percentage
                          return pct != null ? `${pct.toFixed(1)}%` : '—'
                        })()}
                      </td>
                      <td className="font-mono text-white">{row.total_solar_gain_kwh ? `${row.total_solar_gain_kwh.toFixed(2)}` : '—'}</td>
                      <td>
                        <span className="text-base font-bold text-white">
                          {row.score?.toFixed(1) ?? '—'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
        </>
      )}
    </div>
  )
}
