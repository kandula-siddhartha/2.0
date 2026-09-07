import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  API,
  Location,
  WeatherDataset,
  Design,
  Material,
  AnsysStatus,
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
  Settings,
} from 'lucide-react'
import Plot from 'react-plotly.js'

/* ─── Shared Vibrant Plotly Theme (Light) ─────────────────── */
const darkChartLayout: any = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: '#FFFFFF',
  font: { color: '#475569', size: 11, family: 'Inter, system-ui, sans-serif' },
  xaxis: {
    gridcolor: '#EDF2F7',
    tickcolor: '#CBD5E1',
    linecolor: '#CBD5E1',
    zerolinecolor: '#CBD5E1'
  },
  yaxis: {
    gridcolor: '#EDF2F7',
    tickcolor: '#CBD5E1',
    linecolor: '#CBD5E1',
    zerolinecolor: '#CBD5E1'
  },
  legend: {
    bgcolor: 'rgba(255, 255, 255, 0.95)',
    bordercolor: '#E2E8F0',
    borderwidth: 1,
    font: { color: '#0F172A', size: 10 }
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

  const applyWeightPreset = (preset: 'balanced' | 'night' | 'solar') => {
    if (preset === 'balanced') {
      setWeights({ comfort_compliance: 0.35, nighttime_retention: 0.25, heat_loss: 0.20, solar_gain: 0.15, temperature_stability: 0.05 })
    } else if (preset === 'night') {
      setWeights({ comfort_compliance: 0.25, nighttime_retention: 0.40, heat_loss: 0.25, solar_gain: 0.05, temperature_stability: 0.05 })
    } else if (preset === 'solar') {
      setWeights({ comfort_compliance: 0.25, nighttime_retention: 0.15, heat_loss: 0.15, solar_gain: 0.40, temperature_stability: 0.05 })
    }
  }

  const [launching, setLaunching] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [simulationName, setSimulationName] = useState('')
  const [isNameManuallyEdited, setIsNameManuallyEdited] = useState(false)
  const [ansysStatus, setAnsysStatus] = useState<AnsysStatus | null>(null)

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

  useEffect(() => {
    if (currentStep === 5) {
      API.ansysStatus().then(res => setAnsysStatus(res.data)).catch(() => {})
    }
  }, [currentStep])

  const loadAssets = async () => {
    try {
      const [desRes, matRes, ansysRes] = await Promise.all([
        API.listDesigns(),
        API.listMaterials(),
        API.ansysStatus().catch(() => ({ data: null })),
      ])
      setDesigns(desRes.data)
      setMaterials(matRes.data)
      if (ansysRes?.data) {
        setAnsysStatus(ansysRes.data)
      }
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E4E4E7] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-800 mb-1">
            <span className="w-2 h-2 rounded-full bg-black"></span>
            ANSYS MAPDL Solver Suite
          </div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
            Simulation Studio
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Himalayan passive thermal shelter design optimization & transient FEA setup.
          </p>
        </div>

        {/* Matrix Counter (Only shown in and after Step 3: Shelter Matrix) */}
        {currentStep >= 3 && (
          <div className="flex items-center gap-3 bg-[#FFFFFF] border border-[#E4E4E7] shadow-sm rounded-xl px-4 py-2.5 fade-in">
            <div className="w-8 h-8 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-900">
              <Layers size={16} />
            </div>
            <div>
              <span className="text-[11px] text-zinc-500 uppercase tracking-wider block font-medium">
                Simulation Matrix
              </span>
              <span className="text-sm font-bold text-zinc-900 font-mono">
                {totalCombinations} Runs <span className="text-xs text-zinc-500 font-normal">({selectedDesignIds.length}D × {selectedMaterialIds.length}M)</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Step Wizard Connected Pipeline Stepper */}
      <div className="bg-white/90 backdrop-blur-sm p-2 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between gap-1 overflow-x-auto">
          {steps.map((item, idx) => {
            const Icon = item.icon
            const isActive = currentStep === item.step
            const isDone = currentStep > item.step

            return (
              <React.Fragment key={item.step}>
                <button
                  type="button"
                  disabled={!isDone && !isActive}
                  onClick={() => isDone && setCurrentStep(item.step)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all select-none ${isActive
                    ? 'bg-black text-white font-semibold shadow-xs ring-1 ring-black'
                    : isDone
                      ? 'bg-zinc-100 text-zinc-900 border border-zinc-300 font-medium hover:bg-zinc-200 cursor-pointer'
                      : 'text-slate-400 cursor-not-allowed opacity-60'
                    }`}
                >
                  <span
                    className={`w-5 h-5 rounded-lg flex items-center justify-center text-xs shrink-0 transition-colors ${isActive
                      ? 'bg-white/20 text-white'
                      : isDone
                        ? 'bg-zinc-200 text-zinc-900'
                        : 'bg-slate-100 text-slate-400'
                      }`}
                  >
                    {isDone ? (
                      <CheckCircle2 size={13} className="text-black" />
                    ) : (
                      <Icon size={13} />
                    )}
                  </span>
                  <span className="tracking-tight">{item.label}</span>
                </button>
                {idx < steps.length - 1 && (
                  <div
                    className={`flex-1 h-[2px] min-w-3 rounded-full transition-colors hidden sm:block ${currentStep > idx + 1
                      ? 'bg-black'
                      : currentStep === idx + 1
                        ? 'bg-gradient-to-r from-black to-zinc-200'
                        : 'bg-zinc-200'
                      }`}
                  />
                )}
              </React.Fragment>
            )
          })}
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-[#FFFFFF] border border-zinc-300 text-zinc-900 text-xs shadow-sm">
          <AlertTriangle size={16} className="shrink-0 text-black" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── STEP 1: Location & Time ── */}
      {currentStep === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 fade-in">
          {/* Location Picker */}
          <div className="lg:col-span-2 mono-card space-y-5 bg-[#FFFFFF] border border-[#E4E4E7]">
            <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2 border-b border-[#E4E4E7] pb-3">
              <MapPin size={16} className="text-black" />
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
                    className="text-left p-3 rounded-lg bg-[#FAFAFA] hover:bg-[#F4F4F5] border border-[#E4E4E7] hover:border-zinc-400 transition-all cursor-pointer"
                  >
                    <span className="font-semibold text-xs text-zinc-900 block truncate">
                      {p.name.split(',')[0]}
                    </span>
                    <span className="text-[11px] text-zinc-500 block font-mono mt-0.5">
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
              <div className="p-4 rounded-lg bg-[#F8F9FA] border border-[#E4E4E7] flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-black" />
                    <span className="font-semibold text-sm text-zinc-900">{location.name}</span>
                    <span className="text-xs text-zinc-500">({location.country})</span>
                  </div>
                  <div className="flex items-center gap-4 flex-wrap text-xs text-zinc-500 font-mono">
                    <span>Lat: <strong className="text-zinc-800">{location.latitude.toFixed(4)}°N</strong></span>
                    <span>Lon: <strong className="text-zinc-800">{location.longitude.toFixed(4)}°E</strong></span>
                    <span>Elev: <strong className="text-zinc-800">{location.elevation ?? 3500} m</strong></span>
                    <span>Timezone: <strong className="text-zinc-800">{location.timezone ?? 'Asia/Kolkata'}</strong></span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Time Window Card */}
          <div className="mono-card space-y-5 flex flex-col justify-between bg-[#FFFFFF] border border-[#E4E4E7]">
            <div className="space-y-4">
              <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2 border-b border-[#E4E4E7] pb-3">
                <Calendar size={16} className="text-black" />
                <span>Simulation Time Horizon</span>
              </h2>

              <p className="text-xs text-zinc-500 leading-relaxed">
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
                  <span className="text-[10px] text-zinc-400 font-normal">Auto-advances to next day</span>
                </label>
                <input
                  type="date"
                  value={endDate}
                  min={startDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="input"
                />
              </div>

              <div className="p-3 rounded-lg bg-[#FAFAFA] border border-[#E4E4E7]">
                <span className="text-[11px] text-zinc-500 uppercase tracking-wider block font-medium">
                  Time Step Resolution
                </span>
                <span className="text-xs text-zinc-800 font-mono mt-0.5 block">
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
          <div className="mono-card space-y-5 bg-[#FFFFFF] border border-[#E4E4E7]">
            <div className="flex items-start justify-between border-b border-[#E4E4E7] pb-4">
              <div>
                <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                  <CloudSun size={18} className="text-black" />
                  <span>Atmospheric Boundary Conditions Telemetry</span>
                </h2>
                <p className="text-xs text-zinc-500 mt-1">
                  Open-Meteo meteorological telemetry for {location?.name} ({startDate} to {endDate}).
                </p>
              </div>
              <span className="badge badge-completed text-xs">
                {weatherDataset.data.length} Hourly Observations
              </span>
            </div>

            {/* Vibrant Weather Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Temperature & Wind Chart */}
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#E2E8F0] space-y-2 shadow-sm">
                <h3 className="text-xs font-semibold text-zinc-800 uppercase tracking-wider">
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
                      line: { color: '#2563EB', width: 2.8 },
                      marker: { size: 4, color: '#1D4ED8' },
                    },
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.wind_speed_10m ?? 0),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Wind Speed (m/s)',
                      yaxis: 'y2',
                      line: { color: '#059669', width: 2.2, dash: 'dash' },
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
                      tickcolor: '#CBD5E1',
                      linecolor: '#CBD5E1',
                      font: { color: '#059669' },
                    },
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Solar Radiation Chart */}
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#E2E8F0] space-y-2 shadow-sm">
                <h3 className="text-xs font-semibold text-zinc-800 uppercase tracking-wider">
                  Global Horizontal Solar Radiation (GHI)
                </h3>
                <Plot
                  data={[
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.shortwave_radiation ?? 0),
                      type: 'scatter',
                      fill: 'tozeroy',
                      fillcolor: 'rgba(245, 158, 11, 0.18)',
                      name: 'GHI Solar (W/m²)',
                      line: { color: '#F59E0B', width: 2.8 },
                    },
                    {
                      x: weatherDataset.data.map(d => d.timestamp),
                      y: weatherDataset.data.map(d => d.direct_radiation ?? 0),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Direct Solar (W/m²)',
                      line: { color: '#DC2626', width: 2.0, dash: 'dash' },
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

            <div className="flex justify-between pt-4 border-t border-[#E4E4E7]">
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
            <div className="mono-card space-y-4 bg-[#FFFFFF] border border-[#E4E4E7]">
              <div className="flex items-center justify-between border-b border-[#E4E4E7] pb-3">
                <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                  <Box size={16} className="text-black" />
                  <span>Shelter Geometries</span>
                </h2>
                <span className="badge badge-completed text-xs font-mono">
                  {selectedDesignIds.length} Selected
                </span>
              </div>

              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {designs.map(d => {
                  const isSelected = selectedDesignIds.includes(d.id)
                  const isImported = d.design_type === 'imported'
                  const volume = (d.length * d.width * d.height).toFixed(1)
                  return (
                    <div
                      key={d.id}
                      onClick={() => toggleDesign(d.id)}
                      className={`group p-3.5 rounded-xl cursor-pointer transition-all ${isSelected
                        ? 'border-2 border-black bg-white shadow-xs'
                        : 'studio-card studio-card-interactive border-slate-200/80 hover:border-zinc-400'
                        }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border bg-zinc-100 border-zinc-200 text-zinc-900">
                            <Box size={16} />
                          </div>
                          <div>
                            <span className="font-bold text-sm text-slate-900 group-hover:text-black transition-colors block">
                              {d.name}
                            </span>
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded border border-zinc-300 bg-zinc-100 text-zinc-800 mt-0.5">
                              {isImported ? '3D CAD Solid STEP/IGES' : 'Parametric Solid'}
                            </span>
                          </div>
                        </div>

                        {isSelected ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-zinc-900 bg-zinc-100 border border-zinc-300 px-2.5 py-0.5 rounded-full shrink-0 shadow-xs">
                            <CheckCircle2 size={12} className="text-black" />
                            Selected
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-medium text-slate-400 group-hover:text-zinc-900 transition-colors px-2 py-0.5 rounded-full shrink-0">
                            + Select
                          </span>
                        )}
                      </div>

                      <p className="text-xs mt-2 line-clamp-2 text-slate-600 leading-relaxed">
                        {d.description}
                      </p>

                      <div className="grid grid-cols-3 gap-2 font-mono text-[11px] mt-2.5 pt-2 border-t border-slate-200/70 text-slate-600">
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-100">
                          Dim: <strong className="text-slate-900">{d.length}×{d.width}×{d.height}m</strong>
                        </span>
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-100">
                          Vol: <strong className="text-slate-900">{volume} m³</strong>
                        </span>
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-100">
                          {isImported ? 'FEA: ' : 'Wall: '}
                          <strong className="text-slate-900">
                            {isImported ? 'Solid Mesh' : `${(d.wall_thickness * 100).toFixed(0)}cm`}
                          </strong>
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Material Selection */}
            <div className="mono-card space-y-4 bg-[#FFFFFF] border border-[#E4E4E7]">
              <div className="flex items-center justify-between border-b border-[#E4E4E7] pb-3">
                <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                  <Layers size={16} className="text-black" />
                  <span>Envelope Materials</span>
                </h2>
                <span className="badge badge-completed text-xs font-mono">
                  {selectedMaterialIds.length} Selected
                </span>
              </div>

              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {materials.map(m => {
                  const isSelected = selectedMaterialIds.includes(m.id)
                  const getCategoryStyle = () => {
                    return 'bg-zinc-100 text-zinc-800 border-zinc-300'
                  }

                  return (
                    <div
                      key={m.id}
                      onClick={() => toggleMaterial(m.id)}
                      className={`group p-3.5 rounded-xl cursor-pointer transition-all ${isSelected
                        ? 'border-2 border-black bg-white shadow-xs'
                        : 'studio-card studio-card-interactive border-slate-200/80 hover:border-zinc-400'
                        }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-slate-900 group-hover:text-black transition-colors">
                              {m.name}
                            </span>
                            <span className={`badge text-[10px] uppercase font-mono border ${getCategoryStyle()}`}>
                              {m.category}
                            </span>
                          </div>
                          <p className="text-xs mt-1 line-clamp-1 text-slate-600">
                            {m.description}
                          </p>
                        </div>

                        {isSelected ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-zinc-900 bg-zinc-100 border border-zinc-300 px-2.5 py-0.5 rounded-full shrink-0 shadow-xs">
                            <CheckCircle2 size={12} className="text-black" />
                            Selected
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-medium text-slate-400 group-hover:text-zinc-900 transition-colors px-2 py-0.5 rounded-full shrink-0">
                            + Select
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-3 gap-2 font-mono text-[11px] mt-2.5 pt-2 border-t border-slate-200/70 text-slate-600">
                        <div className="p-1 rounded bg-slate-50 border border-slate-100 text-center">
                          <span className="text-[10px] text-slate-400 block">k (W/m·K)</span>
                          <span className="font-bold text-slate-900 text-xs">{m.thermal_conductivity}</span>
                        </div>
                        <div className="p-1 rounded bg-slate-50 border border-slate-100 text-center">
                          <span className="text-[10px] text-slate-400 block">ρ (kg/m³)</span>
                          <span className="font-bold text-slate-900 text-xs">{m.density}</span>
                        </div>
                        <div className="p-1 rounded bg-slate-50 border border-slate-100 text-center">
                          <span className="text-[10px] text-slate-400 block">Cp (J/kg·K)</span>
                          <span className="font-bold text-slate-900 text-xs">{m.specific_heat}</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Orientation Picker */}
          <div className="mono-card flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] border border-[#E4E4E7]">
            <div>
              <span className="font-semibold text-sm text-zinc-900">Facade Orientation</span>
              <p className="text-xs text-zinc-500 mt-0.5">
                South orientation maximizes direct passive solar irradiation in the Himalayas.
              </p>
            </div>
            <div className="flex gap-2 flex-wrap">
              {['south', 'southeast', 'southwest', 'east', 'west', 'north'].map(dir => (
                <button
                  key={dir}
                  type="button"
                  onClick={() => setOrientation(dir)}
                  className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-all cursor-pointer border-2 ${orientation === dir
                    ? 'bg-white border-black text-zinc-900 font-bold shadow-xs'
                    : 'bg-[#FAFAFA] border-[#E4E4E7] text-zinc-600 hover:text-black hover:border-zinc-400 hover:bg-[#F4F4F5]'
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
          <div className="mono-card space-y-5 bg-[#FFFFFF] border border-[#E4E4E7]">
            <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2 border-b border-[#E4E4E7] pb-3">
              <Sliders size={16} className="text-black" />
              <span>FEM Mesh & Boundary Physics</span>
            </h2>

            {/* Target Mesh Element Size */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-zinc-700 font-medium">Target Mesh Element Size</span>
                <span className="font-mono text-xs font-bold text-zinc-900 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200">{meshSize.toFixed(2)} m</span>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0.15" max="0.60" step="0.05"
                  value={meshSize}
                  onChange={e => setMeshSize(parseFloat(e.target.value))}
                  className="slider-glacier w-44 sm:w-56 cursor-pointer"
                />
              </div>
              <span className="text-[11px] text-zinc-500 block mt-1">
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
                      ? 'border-2 border-black bg-white text-zinc-900 font-semibold shadow-xs'
                      : 'studio-card studio-card-interactive border-slate-200 text-zinc-700'
                      }`}
                  >
                    <span className="text-xs font-bold block">{opt.label}</span>
                    <span className="text-[10px] mt-0.5 block text-zinc-500">{opt.sub}</span>
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
                  <span className="text-[11px] text-zinc-500 block mb-1">Lower Bound</span>
                  <input
                    type="number"
                    value={comfortMin}
                    onChange={e => setComfortMin(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-zinc-500 block mb-1">Upper Bound</span>
                  <input
                    type="number"
                    value={comfortMax}
                    onChange={e => setComfortMax(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
              </div>
            </div>

            {/* Boundary Condition Toggles with iOS Slider Switch */}
            <div className="space-y-2.5 pt-3 border-t border-[#E4E4E7]">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50/70 border border-slate-200/80">
                <div>
                  <span className="text-xs font-semibold text-slate-800 block">
                    Dynamic Solar Radiation Loading
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    TABLE Heat Flux BC mapped from Open-Meteo irradiance
                  </span>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={solarEnabled}
                    onChange={e => setSolarEnabled(e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50/70 border border-slate-200/80">
                <div>
                  <span className="text-xs font-semibold text-slate-800 block">
                    Linearized Grey-Body Surface Sky Radiation
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    Radiative cooling heat loss to clear night sky
                  </span>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={radiationEnabled}
                    onChange={e => setRadiationEnabled(e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>

          {/* Scoring Weights */}
          <div className="mono-card space-y-5 flex flex-col justify-between bg-[#FFFFFF] border border-[#E4E4E7]">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-[#E4E4E7] pb-3">
                <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                  <Sparkles size={16} className="text-black" />
                  <span>Recommendation Scoring Weights</span>
                </h2>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-zinc-100 text-zinc-900 border border-zinc-300 flex items-center gap-1.5">
                    <CheckCircle2 size={12} className="text-black" />
                    100% Balanced
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] font-semibold text-slate-500 mr-1">Presets:</span>
                <button
                  type="button"
                  onClick={() => applyWeightPreset('balanced')}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors cursor-pointer"
                >
                  Balanced Comfort
                </button>
                <button
                  type="button"
                  onClick={() => applyWeightPreset('night')}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors cursor-pointer"
                >
                  Night Retention
                </button>
                <button
                  type="button"
                  onClick={() => applyWeightPreset('solar')}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors cursor-pointer"
                >
                  Solar Maximizer
                </button>
              </div>

              <div className="space-y-2.5">
                {[
                  { key: 'comfort_compliance', label: 'Comfort Compliance', sub: '% hours in comfort band', val: weights.comfort_compliance },
                  { key: 'nighttime_retention', label: 'Nighttime Retention', sub: 'overnight avg temperature', val: weights.nighttime_retention },
                  { key: 'heat_loss', label: 'Heat Loss Minimization', sub: 'envelope conduction', val: weights.heat_loss },
                  { key: 'solar_gain', label: 'Solar Gain Harvesting', sub: 'passive irradiance capture', val: weights.solar_gain },
                  { key: 'temperature_stability', label: 'Diurnal Stability', sub: 'thermal damping', val: weights.temperature_stability },
                ].map(item => (
                  <div key={item.key} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-50/70 border border-slate-200/80">
                    <div className="flex-1 pr-2">
                      <span className="font-semibold text-xs text-zinc-800 block">{item.label}</span>
                      <span className="text-[10px] text-zinc-500 block">{item.sub}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <input
                        type="range"
                        min="0" max="1" step="0.05"
                        value={item.val}
                        onChange={e => handleWeightChange(item.key, parseFloat(e.target.value))}
                        className="slider-glacier w-32 sm:w-44 cursor-pointer"
                      />
                      <span className="font-mono font-bold text-xs text-zinc-900 w-10 text-right">
                        {(item.val * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-between pt-4 border-t border-[#E4E4E7]">
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
        <div className="mono-card space-y-6 max-w-2xl mx-auto fade-in p-8 bg-[#FFFFFF] border border-[#E4E4E7] shadow-sm">
          {/* Launch Hero */}
          <div className="rounded-xl bg-[#FAFAFA] border border-[#E4E4E7] p-6 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-[#09090B] text-white flex items-center justify-center mx-auto shadow-sm">
              <Play size={22} className="ml-0.5" />
            </div>
            <h2 className="text-xl font-bold text-zinc-900 tracking-tight">
              Ready to Launch ANSYS Transient Simulation
            </h2>
            <p className="text-xs text-zinc-600 max-w-md mx-auto leading-relaxed">
              Execution will solve transient thermal finite-element runs across {totalCombinations} parametric combinations in local ANSYS MAPDL.
            </p>
          </div>

          {/* Custom Simulation Run Name Input Box */}
          <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#E4E4E7] shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-zinc-900 flex items-center gap-1.5">
                <Sparkles size={14} className="text-black" />
                <span>Simulation Run Name</span>
              </label>
              <button
                type="button"
                onClick={() => {
                  setIsNameManuallyEdited(false)
                  setSimulationName(generateSmartName())
                }}
                className="text-[11px] font-medium text-zinc-800 hover:text-black flex items-center gap-1 transition-colors cursor-pointer bg-zinc-100 hover:bg-zinc-200 px-2.5 py-1 rounded border border-zinc-200"
              >
                <RefreshCw size={11} />
                <span>Auto-Fill / Reset</span>
              </button>
            </div>
            <p className="text-[11px] text-zinc-500">
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
              className="input text-xs w-full font-medium bg-[#FFFFFF] border-[#E4E4E7] focus:border-black text-zinc-900"
            />
          </div>

          {/* Configuration Summary Table */}
          <div className="p-4 rounded-xl bg-[#FAFAFA] border border-[#E4E4E7] space-y-4">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="label">Site Location</span>
                <span className="font-semibold text-zinc-900">{location?.name}</span>
              </div>
              <div>
                <span className="label">Weather Provider</span>
                <span className="font-mono text-zinc-700">{weatherDataset?.provider} (Real Data)</span>
              </div>
              <div>
                <span className="label">Time Span</span>
                <span className="font-mono text-zinc-700">{startDate} → {endDate}</span>
              </div>
              <div>
                <span className="label">Total Solver Runs</span>
                <span className="font-semibold text-zinc-900">{totalCombinations} solid thermal runs</span>
              </div>
            </div>

            <div className="pt-3 border-t border-[#E4E4E7]">
              <span className="label">Evaluation Matrix</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {selectedDesignIds.map(dId => {
                  const dName = designs.find(d => d.id === dId)?.name || 'Design'
                  return selectedMaterialIds.map(mId => {
                    const mName = materials.find(m => m.id === mId)?.name || 'Material'
                    return (
                      <span
                        key={`${dId}-${mId}`}
                        className="px-2.5 py-1 rounded-md bg-[#FFFFFF] border border-[#E4E4E7] text-zinc-700 text-xs font-mono shadow-sm"
                      >
                        {dName} + {mName}
                      </span>
                    )
                  })
                })}
              </div>
            </div>
          </div>

          {/* ANSYS MAPDL Engine Readiness Verification */}
          {ansysStatus && (!ansysStatus.ansys_detected || !ansysStatus.mapdl_exe_exists) && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 flex items-start gap-3 text-xs">
              <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-1.5 flex-1">
                <span className="font-bold text-sm block">ANSYS MAPDL Solver Required</span>
                <p className="text-zinc-700 leading-relaxed">
                  Transient finite-element thermal solves require a verified local ANSYS Mechanical APDL installation. No working executable was detected at the configured path on this laptop.
                </p>
                <Link
                  to="/settings"
                  className="inline-flex items-center gap-1.5 font-semibold text-xs text-zinc-900 bg-white hover:bg-zinc-100 px-3 py-1.5 rounded-md border border-zinc-300 mt-1 cursor-pointer transition-colors shadow-xs"
                >
                  <Settings size={13} />
                  <span>Configure ANSYS Connection in Setup →</span>
                </Link>
              </div>
            </div>
          )}

          {/* Navigation Action Buttons */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setCurrentStep(4)}
              disabled={launching}
              className="btn btn-secondary text-xs"
            >
              ← Back to Settings
            </button>
            <div className="flex items-center gap-3">
              {ansysStatus && (!ansysStatus.ansys_detected || !ansysStatus.mapdl_exe_exists) && (
                <span className="text-[11px] font-mono text-amber-700 font-medium">
                  Connect ANSYS to run
                </span>
              )}
              <button
                onClick={handleLaunch}
                disabled={launching || (ansysStatus !== null && (!ansysStatus.ansys_detected || !ansysStatus.mapdl_exe_exists))}
                className={`btn btn-primary text-xs px-6 py-2.5 flex items-center gap-2 font-bold shadow-md ${
                  ansysStatus !== null && (!ansysStatus.ansys_detected || !ansysStatus.mapdl_exe_exists)
                    ? 'opacity-50 cursor-not-allowed'
                    : ''
                }`}
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
        </div>
      )}
    </div>
  )
}
