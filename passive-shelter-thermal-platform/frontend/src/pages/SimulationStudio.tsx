import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  API,
  Location,
  WeatherDataset,
  Design,
  Material,
} from '../api'
import {
  MapPin,
  Calendar,
  CloudSun,
  Layers,
  Box,
  Sliders,
  Play,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Search,
  Sparkles,
  Zap,
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

export const SimulationStudio: React.FC = () => {
  const navigate = useNavigate()

  const [currentStep, setCurrentStep] = useState(1)

  // Step 1: Location
  const [searchQuery, setSearchQuery] = useState('Leh, Ladakh, India')
  const [location, setLocation] = useState<Location | null>(null)
  const [searchingLocation, setSearchingLocation] = useState(false)
  const [startDate, setStartDate] = useState('2025-01-15')
  const [endDate, setEndDate] = useState('2025-01-16')

  // Automatically calculate the next calendar day string (YYYY-MM-DD)
  const getNextDayString = (dateStr: string): string => {
    if (!dateStr) return ''
    try {
      const parts = dateStr.split('-').map(Number)
      if (parts.length === 3) {
        const d = new Date(parts[0], parts[1] - 1, parts[2])
        d.setDate(d.getDate() + 1)
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }
    } catch {
      // fallback
    }
    return dateStr
  }

  const handleStartDateChange = (newStart: string) => {
    setStartDate(newStart)
    if (newStart) {
      setEndDate(getNextDayString(newStart))
    }
  }

  // Step 2: Weather
  const [weatherDataset, setWeatherDataset] = useState<WeatherDataset | null>(null)
  const [fetchingWeather, setFetchingWeather] = useState(false)
  const [weatherError, setWeatherError] = useState<string | null>(null)

  // Step 3: Designs & Materials
  const [designs, setDesigns] = useState<Design[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [selectedDesignIds, setSelectedDesignIds] = useState<string[]>([])
  const [selectedMaterialIds, setSelectedMaterialIds] = useState<string[]>([])
  const [orientation, setOrientation] = useState('south')

  // Step 4: Physics & Weights
  const [meshSize, setMeshSize] = useState(0.35)
  const [convectionMode, setConvectionMode] = useState<'auto' | 'custom'>('auto')
  const [customHtc, setCustomHtc] = useState(15.0)
  const [comfortMin, setComfortMin] = useState(18.0)
  const [comfortMax, setComfortMax] = useState(27.0)
  const [radiationEnabled, setRadiationEnabled] = useState(true)
  const [solarEnabled, setSolarEnabled] = useState(true)

  // Weights
  const [weights, setWeights] = useState({
    comfort_compliance: 0.35,
    nighttime_retention: 0.25,
    heat_loss: 0.20,
    solar_gain: 0.15,
    temperature_stability: 0.05,
  })

  // Real-time proportional auto-balancing weights handler
  const handleWeightChange = (changedKey: string, rawVal: number) => {
    const keys = ['comfort_compliance', 'nighttime_retention', 'heat_loss', 'solar_gain', 'temperature_stability'] as const
    const newV = Math.min(1, Math.max(0, Math.round(rawVal * 100) / 100))
    const remaining = Math.max(0, 1 - newV)

    const otherKeys = keys.filter(k => k !== changedKey)
    const otherSum = otherKeys.reduce((acc, k) => acc + (weights as any)[k], 0)

    const next: Record<string, number> = { [changedKey]: newV }

    if (otherSum > 0) {
      let allocated = 0
      otherKeys.forEach((k, idx) => {
        if (idx === otherKeys.length - 1) {
          const finalVal = Math.max(0, Math.round((remaining - allocated) * 100) / 100)
          next[k] = finalVal
        } else {
          const share = Math.max(0, Math.round(((weights as any)[k] / otherSum) * remaining * 100) / 100)
          allocated += share
          next[k] = share
        }
      })
    } else {
      const each = Math.round((remaining / otherKeys.length) * 100) / 100
      let allocated = 0
      otherKeys.forEach((k, idx) => {
        if (idx === otherKeys.length - 1) {
          next[k] = Math.max(0, Math.round((remaining - allocated) * 100) / 100)
        } else {
          allocated += each
          next[k] = each
        }
      })
    }

    setWeights(next as typeof weights)
  }

  const [launching, setLaunching] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [simulationName, setSimulationName] = useState('')
  const [isNameManuallyEdited, setIsNameManuallyEdited] = useState(false)

  // Smart simulation name generator
  const generateSmartName = () => {
    const locName = location?.name ? location.name.split(',')[0].trim() : 'Himalayan'
    const dNames = selectedDesignIds
      .map(id => designs.find(d => d.id === id)?.name)
      .filter(Boolean)
    const mNames = selectedMaterialIds
      .map(id => materials.find(m => m.id === id)?.name)
      .filter(Boolean)

    let descriptor = ''
    if (dNames.length === 1 && mNames.length === 1) {
      descriptor = `${dNames[0]} + ${mNames[0]}`
    } else if (dNames.length > 0 && mNames.length > 0) {
      descriptor = `${dNames.length} Designs × ${mNames.length} Materials`
    } else {
      descriptor = 'Thermal Evaluation'
    }

    return `${locName} — ${descriptor} (${startDate || '2025'})`
  }

  // Auto-fill simulation name if not manually modified
  useEffect(() => {
    if (!isNameManuallyEdited) {
      setSimulationName(generateSmartName())
    }
  }, [location, startDate, selectedDesignIds, selectedMaterialIds, designs, materials, isNameManuallyEdited])

  useEffect(() => {
    loadAssets()
    handleSearchLocation('Leh, Ladakh, India')
  }, [])

  const loadAssets = async () => {
    try {
      const [desRes, matRes] = await Promise.all([
        API.listDesigns(),
        API.listMaterials(),
      ])
      setDesigns(desRes.data)
      setMaterials(matRes.data)
      if (desRes.data.length > 0) {
        setSelectedDesignIds([desRes.data[0].id, desRes.data[1]?.id].filter(Boolean) as string[])
      }
      if (matRes.data.length > 0) {
        setSelectedMaterialIds([matRes.data[0].id, matRes.data[1]?.id].filter(Boolean) as string[])
      }
    } catch {
      // ignore
    }
  }

  const handleSearchLocation = async (queryText?: string) => {
    const q = queryText || searchQuery
    if (!q.trim()) return
    setSearchingLocation(true)
    setErrorMsg(null)
    try {
      const res = await API.searchLocation(q)
      setLocation(res.data)
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to geocode location.')
    } finally {
      setSearchingLocation(false)
    }
  }

  const handleFetchWeather = async () => {
    if (!location) return
    setFetchingWeather(true)
    setWeatherError(null)
    try {
      const res = await API.fetchWeather({
        location_id: location.id,
        start_date: startDate,
        end_date: endDate,
        force_refresh: false,
      })
      setWeatherDataset(res.data)
      setCurrentStep(2)
    } catch (err: any) {
      setWeatherError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Error fetching weather data.')
    } finally {
      setFetchingWeather(false)
    }
  }

  const handleLaunch = async () => {
    if (!location || !weatherDataset) return
    if (selectedDesignIds.length === 0 || selectedMaterialIds.length === 0) {
      setErrorMsg('Please select at least 1 design and 1 material.')
      return
    }
    setLaunching(true)
    setErrorMsg(null)
    try {
      const finalName = simulationName.trim() || generateSmartName()
      const configRes = await API.configure({
        name: finalName,
        location_id: location.id,
        weather_dataset_id: weatherDataset.id,
        design_ids: selectedDesignIds,
        material_ids: selectedMaterialIds,
        orientation,
        simulation_start: `${startDate}T00:00:00`,
        simulation_end: `${endDate}T23:00:00`,
        time_step_seconds: 3600,
        mesh_size: meshSize,
        convection_coefficient: convectionMode === 'custom' ? customHtc : null,
        radiation_enabled: radiationEnabled,
        solar_loading_enabled: solarEnabled,
        thermal_mass_enabled: true,
        comfort_min_temp: comfortMin,
        comfort_max_temp: comfortMax,
        recommendation_weights: (() => {
          const wSum = Object.values(weights).reduce((a, b) => a + b, 0) || 1
          const c = Math.round((weights.comfort_compliance / wSum) * 100) / 100
          const n = Math.round((weights.nighttime_retention / wSum) * 100) / 100
          const h = Math.round((weights.heat_loss / wSum) * 100) / 100
          const s = Math.round((weights.solar_gain / wSum) * 100) / 100
          const t = Math.max(0, Math.round((1.0 - (c + n + h + s)) * 100) / 100)
          return {
            comfort_compliance: c,
            nighttime_retention: n,
            heat_loss: h,
            solar_gain: s,
            temperature_stability: t,
          }
        })(),
      })
      const configId = configRes.data.config_id
      await API.launch(configId)
      navigate(`/monitor?config_id=${configId}`)
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to configure and launch simulation.')
    } finally {
      setLaunching(false)
    }
  }

  const toggleDesign = (id: string) => {
    setSelectedDesignIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const toggleMaterial = (id: string) => {
    setSelectedMaterialIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const totalCombinations = selectedDesignIds.length * selectedMaterialIds.length

  const presets = [
    { name: 'Leh, Ladakh, India', lat: 34.15, lon: 77.58, elev: 3500 },
    { name: 'Kargil, Ladakh, India', lat: 34.55, lon: 76.13, elev: 2676 },
    { name: 'Dras, Ladakh, India', lat: 34.43, lon: 75.76, elev: 3280 },
    { name: 'Kaza, Spiti Valley, India', lat: 32.23, lon: 78.07, elev: 3650 },
  ]

  const steps = [
    { step: 1, label: 'Location & Climate', icon: MapPin },
    { step: 2, label: 'Weather Telemetry', icon: CloudSun },
    { step: 3, label: 'Shelter Matrix', icon: Box },
    { step: 4, label: 'Thermal Physics', icon: Sliders },
    { step: 5, label: 'Review & Launch', icon: Play },
  ]

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 fade-in">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1A1D24] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-white mb-1">
            <span className="w-2 h-2 rounded-full bg-white"></span>
            ANSYS MAPDL Solver Suite
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Simulation Studio
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Himalayan passive thermal shelter design optimization & transient FEA setup.
          </p>
        </div>

        {/* Matrix Counter (Only shown in and after Step 3: Shelter Matrix) */}
        {currentStep >= 3 && (
          <div className="flex items-center gap-3 bg-[#121418] border border-[#20242C] rounded-xl px-4 py-2.5 fade-in">
            <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-white">
              <Layers size={16} />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-medium">
                Simulation Matrix
              </span>
              <span className="text-sm font-bold text-white font-mono">
                {totalCombinations} Runs <span className="text-xs text-slate-400 font-normal">({selectedDesignIds.length}D × {selectedMaterialIds.length}M)</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Step Wizard Progress Indicator (Read-Only) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-[#1A1D24]">
        {steps.map((item, idx) => {
          const isActive = currentStep === item.step
          const isDone = currentStep > item.step

          return (
            <React.Fragment key={item.step}>
              <div
                className={`flex items-center gap-2.5 px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap select-none ${isActive
                  ? 'bg-white/10 text-white border border-white/30 font-semibold'
                  : isDone
                    ? 'bg-[#121418] text-slate-300 border border-[#20242C]'
                    : 'text-slate-500'
                  }`}
              >
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${isActive
                    ? 'bg-sky-500 text-white'
                    : isDone
                      ? 'bg-emerald-500 text-white'
                      : 'bg-[#1A1D24] text-slate-400'
                    }`}
                >
                  {isDone ? '✓' : item.step}
                </span>
                <span>{item.label}</span>
              </div>
              {idx < steps.length - 1 && (
                <div className="w-4 h-[1px] bg-[#20242C] shrink-0 hidden sm:block" />
              )}
            </React.Fragment>
          )
        })}
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── STEP 1: Location & Time ── */}
      {currentStep === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 fade-in">
          {/* Location Picker */}
          <div className="lg:col-span-2 mono-card space-y-5">
            <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-[#20242C] pb-3">
              <MapPin size={16} className="text-white" />
              <span>Select Geographic Site</span>
            </h2>

            {/* Himalayan Presets */}
            <div>
              <label className="label">Ladakh & Himalayan Region Presets</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-2">
                {presets.map(p => (
                  <button
                    key={p.name}
                    type="button"
                    onClick={() => {
                      setSearchQuery(p.name)
                      handleSearchLocation(p.name)
                    }}
                    className="text-left p-3 rounded-lg bg-[#0D0F13] hover:bg-[#181B21] border border-[#20242C] hover:border-white/40 transition-all cursor-pointer"
                  >
                    <span className="font-semibold text-xs text-white block truncate">
                      {p.name.split(',')[0]}
                    </span>
                    <span className="text-[11px] text-slate-400 block font-mono mt-0.5">
                      {p.elev} m elev
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Search Input */}
            <div>
              <label className="label">Search Custom Coordinates / Town</label>
              <div className="flex gap-2 mt-1.5">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="e.g. Leh, Ladakh, India or 34.15, 77.58"
                  className="input flex-1"
                  onKeyDown={e => e.key === 'Enter' && handleSearchLocation()}
                />
                <button
                  type="button"
                  onClick={() => handleSearchLocation()}
                  disabled={searchingLocation}
                  className="btn btn-primary text-xs shrink-0"
                >
                  {searchingLocation ? <RefreshCw size={14} className="animate-spin" /> : <Search size={14} />}
                  <span>Geocode</span>
                </button>
              </div>
            </div>

            {/* Geocoded Confirmation Card */}
            {location && (
              <div className="p-4 rounded-lg bg-[#0D0F13] border border-white/20 flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-emerald-400" />
                    <span className="font-semibold text-sm text-white">{location.name}</span>
                    <span className="text-xs text-slate-400">({location.country})</span>
                  </div>
                  <div className="flex items-center gap-4 flex-wrap text-xs text-slate-400 font-mono">
                    <span>Lat: <strong className="text-slate-200">{location.latitude.toFixed(4)}°N</strong></span>
                    <span>Lon: <strong className="text-slate-200">{location.longitude.toFixed(4)}°E</strong></span>
                    <span>Elev: <strong className="text-slate-200">{location.elevation ?? 3500} m</strong></span>
                    <span>Timezone: <strong className="text-slate-200">{location.timezone ?? 'Asia/Kolkata'}</strong></span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Time Window Card */}
          <div className="mono-card space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-[#20242C] pb-3">
                <Calendar size={16} className="text-white" />
                <span>Simulation Time Horizon</span>
              </h2>

              <p className="text-xs text-slate-400 leading-relaxed">
                Define the high-altitude cold winter diurnal window to simulate in local MAPDL.
              </p>

              <div>
                <label className="label">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => handleStartDateChange(e.target.value)}
                  className="input"
                />
              </div>

              <div>
                <label className="label flex items-center justify-between">
                  <span>End Date</span>
                  <span className="text-[10px] text-slate-400 font-normal">Auto-advances to next day</span>
                </label>
                <input
                  type="date"
                  value={endDate}
                  min={startDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="input"
                />
              </div>

              <div className="p-3 rounded-lg bg-[#0D0F13] border border-[#20242C]">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-medium">
                  Time Step Resolution
                </span>
                <span className="text-xs text-slate-200 font-mono mt-0.5 block">
                  1.0 Hour (3600 s) — 24 steps/cycle
                </span>
              </div>
            </div>

            <button
              onClick={handleFetchWeather}
              disabled={!location || fetchingWeather}
              className="btn btn-primary w-full justify-center py-3 text-xs"
            >
              {fetchingWeather ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Fetching Real Climate Data...</span>
                </>
              ) : (
                <>
                  <span>Fetch Weather & Proceed</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 2: Weather Telemetry Preview ── */}
      {currentStep === 2 && weatherDataset && (
        <div className="space-y-6 fade-in">
          <div className="mono-card space-y-5">
            <div className="flex items-start justify-between border-b border-[#20242C] pb-4">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <CloudSun size={18} className="text-white" />
                  <span>Atmospheric Boundary Conditions Telemetry</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Open-Meteo meteorological telemetry for {location?.name} ({startDate} to {endDate}).
                </p>
              </div>
              <span className="badge badge-completed text-xs">
                ✓ {weatherDataset.data.length} Hourly Observations
              </span>
            </div>

            {/* Colorful Weather Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Temperature & Wind Chart */}
              <div className="p-4 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-2">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Ambient Temperature & Wind Speed
                </h3>
                <Plot
                  data={[
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.temperature_2m ?? 0),
                      type: 'scatter',
                      mode: 'lines+markers',
                      name: 'Ambient Temp (°C)',
                      line: { color: '#38BDF8', width: 2.5 },
                      marker: { size: 3.5, color: '#38BDF8' },
                    },
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.wind_speed_10m ?? 0),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Wind Speed (m/s)',
                      yaxis: 'y2',
                      line: { color: '#34D399', width: 2, dash: 'dot' },
                    },
                  ]}
                  layout={{
                    ...darkChartLayout,
                    autosize: true,
                    height: 260,
                    margin: { l: 45, r: 45, t: 10, b: 45 },
                    showlegend: true,
                    legend: { orientation: 'h', y: -0.28, font: { size: 10 } },
                    xaxis: { ...darkChartLayout.xaxis, tickformat: '%d %b %H:%M' },
                    yaxis: { ...darkChartLayout.yaxis, title: 'Temp (°C)' },
                    yaxis2: {
                      title: 'Wind (m/s)',
                      overlaying: 'y',
                      side: 'right',
                      showgrid: false,
                      tickcolor: '#34D399',
                      linecolor: '#34D399',
                      font: { color: '#34D399' },
                    },
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Solar Radiation Chart */}
              <div className="p-4 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-2">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Global Horizontal Solar Radiation (GHI)
                </h3>
                <Plot
                  data={[
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.shortwave_radiation ?? 0),
                      type: 'scatter',
                      fill: 'tozeroy',
                      fillcolor: 'rgba(56, 189, 248, 0.18)',
                      name: 'GHI Solar (W/m²)',
                      line: { color: '#38BDF8', width: 2.5 },
                    },
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.direct_radiation ?? 0),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Direct Solar (W/m²)',
                      line: { color: '#60A5FA', width: 1.8, dash: 'dot' },
                    },
                  ]}
                  layout={{
                    ...darkChartLayout,
                    autosize: true,
                    height: 260,
                    margin: { l: 45, r: 25, t: 10, b: 45 },
                    showlegend: true,
                    legend: { orientation: 'h', y: -0.28, font: { size: 10 } },
                    xaxis: { ...darkChartLayout.xaxis, tickformat: '%d %b %H:%M' },
                    yaxis: { ...darkChartLayout.yaxis, title: 'Flux (W/m²)' },
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%' }}
                />
              </div>
            </div>

            <div className="flex justify-between pt-4 border-t border-[#20242C]">
              <button onClick={() => setCurrentStep(1)} className="btn btn-secondary text-xs">
                ← Back to Location
              </button>
              <button onClick={() => setCurrentStep(3)} className="btn btn-primary text-xs">
                <span>Proceed to Shelter Matrix</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 3: Shelter Matrix Selection ── */}
      {currentStep === 3 && (
        <div className="space-y-6 fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Design Selection */}
            <div className="mono-card space-y-4">
              <div className="flex items-center justify-between border-b border-[#20242C] pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Box size={16} className="text-white" />
                  <span>Shelter Geometries</span>
                </h2>
                <span className="badge badge-solving text-xs font-mono">
                  {selectedDesignIds.length} Selected
                </span>
              </div>

              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {designs.map(d => {
                  const isSelected = selectedDesignIds.includes(d.id)
                  return (
                    <div
                      key={d.id}
                      onClick={() => toggleDesign(d.id)}
                      className={`p-3.5 rounded-lg cursor-pointer transition-all border ${isSelected
                        ? 'bg-white/10 border-white/40 text-white'
                        : 'bg-[#0D0F13] border-[#20242C] hover:border-slate-600 text-slate-300'
                        }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm">{d.name}</span>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => { }}
                          className="accent-sky-500 w-4 h-4 cursor-pointer"
                        />
                      </div>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {d.description}
                      </p>
                      <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400 mt-2 pt-2 border-t border-[#1A1D24]">
                        <span>{d.length}×{d.width}×{d.height} m</span>
                        {d.design_type === 'imported' ? (
                          <>
                            <span className="text-sky-300">3D CAD Solid Mesh</span>
                            <span>Integrated Openings</span>
                          </>
                        ) : (
                          <>
                            <span>Wall: {(d.wall_thickness * 100).toFixed(0)} cm</span>
                            <span>Window: {d.window_area} m²</span>
                          </>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Material Selection */}
            <div className="mono-card space-y-4">
              <div className="flex items-center justify-between border-b border-[#20242C] pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Layers size={16} className="text-white" />
                  <span>Envelope Materials</span>
                </h2>
                <span className="badge badge-solving text-xs font-mono">
                  {selectedMaterialIds.length} Selected
                </span>
              </div>

              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {materials.map(m => {
                  const isSelected = selectedMaterialIds.includes(m.id)
                  return (
                    <div
                      key={m.id}
                      onClick={() => toggleMaterial(m.id)}
                      className={`p-3.5 rounded-lg cursor-pointer transition-all border ${isSelected
                        ? 'bg-white/10 border-white/40 text-white'
                        : 'bg-[#0D0F13] border-[#20242C] hover:border-slate-600 text-slate-300'
                        }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm">{m.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="badge text-[10px] uppercase font-mono">
                            {m.category}
                          </span>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => { }}
                            className="accent-sky-500 w-4 h-4 cursor-pointer"
                          />
                        </div>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                        {m.description}
                      </p>
                      <div className="grid grid-cols-3 gap-2 font-mono text-[11px] text-slate-400 mt-2 pt-2 border-t border-[#1A1D24]">
                        <span>k: <strong className="text-slate-200">{m.thermal_conductivity}</strong></span>
                        <span>ρ: <strong className="text-slate-200">{m.density}</strong></span>
                        <span>Cp: <strong className="text-slate-200">{m.specific_heat}</strong></span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Orientation Picker */}
          <div className="mono-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="font-semibold text-sm text-white">Facade Orientation</span>
              <p className="text-xs text-slate-400 mt-0.5">
                South orientation maximizes direct passive solar irradiation in the Himalayas.
              </p>
            </div>
            <div className="flex gap-2 flex-wrap">
              {['south', 'southeast', 'southwest', 'east', 'north'].map(dir => (
                <button
                  key={dir}
                  type="button"
                  onClick={() => setOrientation(dir)}
                  className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-all cursor-pointer ${orientation === dir
                    ? 'bg-white text-slate-950 font-bold'
                    : 'bg-[#0D0F13] border border-[#20242C] text-slate-400 hover:text-white'
                    }`}
                >
                  {dir}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setCurrentStep(2)} className="btn btn-secondary text-xs">
              ← Back to Weather
            </button>
            <button
              onClick={() => setCurrentStep(4)}
              disabled={selectedDesignIds.length === 0 || selectedMaterialIds.length === 0}
              className="btn btn-primary text-xs"
            >
              <span>Thermal Physics & Weights</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 4: Thermal Physics & Weights ── */}
      {currentStep === 4 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
          {/* FEM Boundary Physics */}
          <div className="mono-card space-y-5">
            <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-[#20242C] pb-3">
              <Sliders size={16} className="text-white" />
              <span>FEM Mesh & Boundary Physics</span>
            </h2>

            {/* Target Mesh Element Size */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-slate-300 font-medium">Target Mesh Element Size</span>
                <span className="font-mono text-xs font-bold text-white">{meshSize.toFixed(2)} m</span>
              </div>
              <input
                type="range"
                min="0.15" max="0.60" step="0.05"
                value={meshSize}
                onChange={e => setMeshSize(parseFloat(e.target.value))}
                className="w-full accent-sky-500 cursor-pointer"
              />
              <span className="text-[11px] text-slate-400 block mt-1">
                Optimized for ANSYS Student &lt;128k node constraint. 0.35m ≈ 25,000 nodes.
              </span>
            </div>

            {/* Convection Mode */}
            <div>
              <label className="label">External Convection Heat Transfer Mode</label>
              <div className="grid grid-cols-2 gap-2.5 mt-1.5">
                {[
                  { val: 'auto', label: 'Wind-Based McAdams', sub: 'h = 5.7 + 3.8 × v (dynamic)' },
                  { val: 'custom', label: 'Fixed Custom HTC', sub: 'User-specified W/m²K' },
                ].map(opt => (
                  <button
                    key={opt.val}
                    type="button"
                    onClick={() => setConvectionMode(opt.val as any)}
                    className={`p-3 rounded-lg text-left transition-all border cursor-pointer ${convectionMode === opt.val
                      ? 'bg-white/10 border-white/40 text-white'
                      : 'bg-[#0D0F13] border-[#20242C] text-slate-300 hover:border-slate-500'
                      }`}
                  >
                    <span className="text-xs font-bold block">{opt.label}</span>
                    <span className="text-[10px] text-slate-400 mt-0.5 block">{opt.sub}</span>
                  </button>
                ))}
              </div>

              {convectionMode === 'custom' && (
                <div className="mt-3">
                  <label className="label">Fixed Convection HTC (W/m²K)</label>
                  <input
                    type="number"
                    value={customHtc}
                    onChange={e => setCustomHtc(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
              )}
            </div>

            {/* Comfort Range */}
            <div>
              <label className="label">Occupant Thermal Comfort Envelope (°C)</label>
              <div className="grid grid-cols-2 gap-3 mt-1.5">
                <div>
                  <span className="text-[11px] text-slate-400 block mb-1">Lower Bound</span>
                  <input
                    type="number"
                    value={comfortMin}
                    onChange={e => setComfortMin(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block mb-1">Upper Bound</span>
                  <input
                    type="number"
                    value={comfortMax}
                    onChange={e => setComfortMax(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
              </div>
            </div>

            {/* Boundary Condition Toggles */}
            <div className="space-y-2.5 pt-3 border-t border-[#20242C]">
              <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={solarEnabled}
                  onChange={e => setSolarEnabled(e.target.checked)}
                  className="accent-sky-500 w-4 h-4 cursor-pointer"
                />
                <span>Enable Dynamic Solar Radiation Loading (TABLE Heat Flux BC)</span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={radiationEnabled}
                  onChange={e => setRadiationEnabled(e.target.checked)}
                  className="accent-sky-500 w-4 h-4 cursor-pointer"
                />
                <span>Enable Linearized Grey-Body Surface Sky Radiation</span>
              </label>
            </div>
          </div>

          {/* Scoring Weights */}
          <div className="mono-card space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-[#20242C] pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Sparkles size={16} className="text-white" />
                  <span>Recommendation Scoring Weights</span>
                </h2>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                    <CheckCircle2 size={12} />
                    100%
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                Tune criteria weights to rank candidate shelter architectures based on cold-climate priorities. Sliders automatically balance proportionally in real time to guarantee a 100% total.
              </p>

              <div className="space-y-3.5">
                {[
                  { key: 'comfort_compliance', label: 'Comfort Compliance', sub: '% hours in comfort band', val: weights.comfort_compliance },
                  { key: 'nighttime_retention', label: 'Nighttime Retention', sub: 'overnight avg temperature', val: weights.nighttime_retention },
                  { key: 'heat_loss', label: 'Heat Loss Minimization', sub: 'envelope conduction', val: weights.heat_loss },
                  { key: 'solar_gain', label: 'Solar Gain Harvesting', sub: 'passive irradiance capture', val: weights.solar_gain },
                  { key: 'temperature_stability', label: 'Diurnal Stability', sub: 'thermal damping', val: weights.temperature_stability },
                ].map(item => (
                  <div key={item.key}>
                    <div className="flex justify-between text-xs mb-1">
                      <div>
                        <span className="font-semibold text-slate-200">{item.label}</span>
                        <span className="text-[11px] text-slate-500 ml-1.5">({item.sub})</span>
                      </div>
                      <span className="font-mono font-bold text-white">{(item.val * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0" max="1" step="0.05"
                      value={item.val}
                      onChange={e => handleWeightChange(item.key, parseFloat(e.target.value))}
                      className="w-full accent-sky-500 cursor-pointer"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-between pt-4 border-t border-[#20242C]">
              <button onClick={() => setCurrentStep(3)} className="btn btn-secondary text-xs">
                ← Back to Matrix
              </button>
              <button onClick={() => setCurrentStep(5)} className="btn btn-primary text-xs">
                <span>Review & Launch</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 5: Review & Launch ── */}
      {currentStep === 5 && (
        <div className="mono-card space-y-6 max-w-2xl mx-auto fade-in p-8">
          {/* Launch Hero */}
          <div className="rounded-xl bg-[#121418] border border-[#20242C] p-6 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center mx-auto text-white">
              <Play size={22} className="ml-0.5" />
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Ready to Launch ANSYS Transient Simulation
            </h2>
            <p className="text-xs text-slate-300 max-w-md mx-auto leading-relaxed">
              Execution will solve transient thermal finite-element runs across {totalCombinations} parametric combinations in local ANSYS MAPDL.
            </p>
          </div>

          {/* Custom Simulation Run Name Input Box */}
          <div className="p-4 rounded-xl bg-[#121418] border border-white/20 ring-1 ring-white/10 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-white flex items-center gap-1.5">
                <Sparkles size={14} className="text-white" />
                <span>Simulation Run Name</span>
              </label>
              <button
                type="button"
                onClick={() => {
                  setIsNameManuallyEdited(false)
                  setSimulationName(generateSmartName())
                }}
                className="text-[11px] font-medium text-white hover:text-slate-200 flex items-center gap-1 transition-colors cursor-pointer bg-white/10 hover:bg-white/15 px-2.5 py-1 rounded border border-white/20"
              >
                <RefreshCw size={11} />
                <span>Auto-Fill / Reset</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-300">
              Customize the name of this simulation batch so you can easily locate, identify, and compare it later in Saved Simulations.
            </p>
            <input
              type="text"
              value={simulationName}
              onChange={e => {
                setSimulationName(e.target.value)
                setIsNameManuallyEdited(true)
              }}
              placeholder="e.g. Leh Winter Trial — Stone & Double Glazing"
              className="input text-xs w-full font-medium bg-[#0D0F13] border-slate-700 focus:border-white text-white"
            />
          </div>

          {/* Configuration Summary Table */}
          <div className="p-4 rounded-xl bg-[#0D0F13] border border-[#20242C] space-y-4">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="label">Site Location</span>
                <span className="font-semibold text-white">{location?.name}</span>
              </div>
              <div>
                <span className="label">Weather Provider</span>
                <span className="font-mono text-slate-200">{weatherDataset?.provider} (Real Data)</span>
              </div>
              <div>
                <span className="label">Time Span</span>
                <span className="font-mono text-slate-200">{startDate} → {endDate}</span>
              </div>
              <div>
                <span className="label">Total Solver Runs</span>
                <span className="font-semibold text-white">{totalCombinations} solid thermal runs</span>
              </div>
            </div>

            <div className="pt-3 border-t border-[#1A1D24]">
              <span className="label">Evaluation Matrix</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {selectedDesignIds.map(dId => {
                  const dName = designs.find(d => d.id === dId)?.name || 'Design'
                  return selectedMaterialIds.map(mId => {
                    const mName = materials.find(m => m.id === mId)?.name || 'Material'
                    return (
                      <span
                        key={`${dId}-${mId}`}
                        className="px-2.5 py-1 rounded-md bg-[#181B21] border border-[#262A34] text-slate-300 text-xs font-mono"
                      >
                        {dName} + {mName}
                      </span>
                    )
                  })
                })}
              </div>
            </div>
          </div>

          {/* Navigation Action Buttons */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setCurrentStep(4)}
              disabled={launching}
              className="btn btn-secondary text-xs"
            >
              ← Back to Settings
            </button>
            <button
              onClick={handleLaunch}
              disabled={launching}
              className="btn btn-primary text-xs px-6 py-2.5 flex items-center gap-2"
            >
              {launching ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Launching Solver Queue...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Execute Simulation ({totalCombinations} Runs)</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
