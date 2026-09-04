import React, { useState, useEffect } from 'react'
import { API, Material } from '../api'
import {
  Layers,
  Plus,
  Copy,
  Search,
  X,
  Thermometer,
  Trash2,
} from 'lucide-react'

export const MaterialLibrary: React.FC = () => {
  const [materials, setMaterials] = useState<Material[]>([])
  const [category, setCategory] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)

  // Form State
  const [name, setName] = useState('')
  const [matCategory, setMatCategory] = useState('structural')
  const [description, setDescription] = useState('')
  const [k, setK] = useState(0.5)
  const [rho, setRho] = useState(1700)
  const [cp, setCp] = useState(840)
  const [emissivity, setEmissivity] = useState(0.9)
  const [absorptivity, setAbsorptivity] = useState(0.7)

  useEffect(() => {
    loadMaterials()
  }, [category])

  const loadMaterials = async () => {
    setLoading(true)
    try {
      const res = await API.listMaterials(category === 'all' ? undefined : category)
      setMaterials(res.data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleDuplicate = async (id: string) => {
    try {
      await API.duplicateMaterial(id)
      loadMaterials()
    } catch {
      alert('Failed to duplicate material.')
    }
  }

  const handleDelete = async (id: string, matName: string) => {
    if (!window.confirm(`Are you sure you want to delete material "${matName}"?`)) {
      return
    }
    setDeletingId(id)
    try {
      await API.deleteMaterial(id)
      loadMaterials()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete material.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await API.createMaterial({
        name,
        category: matCategory,
        description,
        thermal_conductivity: k,
        density: rho,
        specific_heat: cp,
        emissivity,
        solar_absorptivity: absorptivity,
      })
      setShowAddModal(false)
      loadMaterials()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create material.')
    }
  }

  const filteredMaterials = materials.filter(m =>
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.description?.toLowerCase().includes(search.toLowerCase())
  )

  const categories = ['all', 'structural', 'insulation', 'glazing', 'thermal_mass', 'composite']

  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'insulation':
        return 'bg-sky-500/15 text-sky-300 border-sky-500/30'
      case 'structural':
        return 'bg-white/10 text-white border-white/20'
      case 'thermal_mass':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
      case 'glazing':
        return 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
      default:
        return 'bg-teal-500/15 text-teal-400 border-teal-500/30'
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 fade-in">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1A1D24] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-white mb-1">
            <span className="w-2 h-2 rounded-full bg-white"></span>
            ANSYS MAPDL Calibrated Database
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Layers className="w-6 h-6 text-white" />
            <span>Building Envelope Material Library</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Standard and indigenous Himalayan envelope materials calibrated for transient thermal analysis.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary text-xs flex items-center gap-2 self-start md:self-auto"
        >
          <Plus size={15} />
          <span>Add Custom Material</span>
        </button>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-all cursor-pointer whitespace-nowrap ${
                category === cat
                  ? 'bg-white/10 text-white border border-white/30 font-semibold'
                  : 'bg-[#121418] text-slate-400 hover:text-slate-200 border border-[#20242C]'
              }`}
            >
              {cat.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Filter materials..."
            className="input pl-9 text-xs"
          />
        </div>
      </div>

      {/* Material Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">
          Loading material catalog...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredMaterials.map(m => (
            <div
              key={m.id}
              className="mono-card p-5 space-y-4 flex flex-col justify-between hover:border-slate-600 transition-all"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-semibold text-sm text-white">{m.name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase border ${getCategoryColor(m.category)}`}>
                    {m.category.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
                  {m.description || 'Thermal envelope material.'}
                </p>
              </div>

              {/* Thermal Properties Table */}
              <div className="rounded-lg bg-[#0D0F13] p-3 border border-[#1A1D24] space-y-2 text-xs font-mono">
                <div className="flex justify-between items-center text-slate-400 border-b border-[#1A1D24] pb-1.5">
                  <span className="text-[11px]">Conductivity (k)</span>
                  <span className="font-bold text-white">{m.thermal_conductivity} W/m·K</span>
                </div>
                <div className="flex justify-between items-center text-slate-400 border-b border-[#1A1D24] pb-1.5">
                  <span className="text-[11px]">Density (ρ)</span>
                  <span className="font-bold text-slate-200">{m.density} kg/m³</span>
                </div>
                <div className="flex justify-between items-center text-slate-400 border-b border-[#1A1D24] pb-1.5">
                  <span className="text-[11px]">Specific Heat (Cp)</span>
                  <span className="font-bold text-slate-200">{m.specific_heat} J/kg·K</span>
                </div>
                <div className="flex justify-between items-center text-slate-400 pt-0.5">
                  <span className="text-[11px]">Emissivity / Solar α</span>
                  <span className="font-bold text-white">{m.emissivity ?? 0.9} / {m.solar_absorptivity ?? 0.7}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#1A1D24] text-xs">
                <span className="text-[11px] text-slate-500 font-mono">
                  {m.is_builtin ? 'Built-in material' : 'Custom material'}
                </span>
                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => handleDuplicate(m.id)}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 cursor-pointer transition-colors"
                  >
                    <Copy size={13} />
                    <span>Duplicate</span>
                  </button>
                  <button
                    onClick={() => handleDelete(m.id, m.name)}
                    disabled={deletingId === m.id}
                    className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1 cursor-pointer transition-colors"
                    title="Delete material"
                  >
                    {deletingId === m.id ? (
                      <span className="text-[11px] text-rose-400 animate-pulse">Deleting...</span>
                    ) : (
                      <>
                        <Trash2 size={13} />
                        <span>Delete</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Material Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="mono-card max-w-lg w-full p-6 space-y-5 border border-[#262A34] bg-[#121418] shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1A1D24] pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Plus size={16} className="text-white" />
                <span>Add Thermal Material</span>
              </h2>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div>
                <label className="label">Material Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Expanded Corkboard Insulation"
                  className="input"
                />
              </div>

              <div>
                <label className="label">Category</label>
                <select
                  value={matCategory}
                  onChange={e => setMatCategory(e.target.value)}
                  className="input"
                >
                  <option value="structural">Structural</option>
                  <option value="insulation">Insulation</option>
                  <option value="glazing">Glazing</option>
                  <option value="thermal_mass">Thermal Mass</option>
                  <option value="composite">Composite</option>
                </select>
              </div>

              <div>
                <label className="label">Description / Material Notes</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Thermal properties reference, density, source..."
                  className="input h-16"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label">Cond. k (W/m·K)</label>
                  <input
                    type="number"
                    step="0.001"
                    required
                    value={k}
                    onChange={e => setK(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Density (kg/m³)</label>
                  <input
                    type="number"
                    required
                    value={rho}
                    onChange={e => setRho(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Cp (J/kg·K)</label>
                  <input
                    type="number"
                    required
                    value={cp}
                    onChange={e => setCp(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Emissivity ε (0–1)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={emissivity}
                    onChange={e => setEmissivity(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Solar Abs. α (0–1)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={absorptivity}
                    onChange={e => setAbsorptivity(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-[#1A1D24]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary text-xs">
                  Save Material
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
