import React, { useState, useEffect } from 'react'
import { API, Design } from '../api'
import {
  Box,
  Plus,
  Upload,
  Copy,
  CheckCircle2,
  FileCode2,
  X,
  Trash2,
  Sparkles,
} from 'lucide-react'

export const DesignLibrary: React.FC = () => {
  const [designs, setDesigns] = useState<Design[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)

  // Parametric Form State
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [length, setLength] = useState(5.0)
  const [width, setWidth] = useState(4.0)
  const [height, setHeight] = useState(3.0)
  const [wallThk, setWallThk] = useState(0.30)
  const [roofThk, setRoofThk] = useState(0.25)
  const [floorThk, setFloorThk] = useState(0.20)
  const [windowArea, setWindowArea] = useState(1.5)
  const [doorArea, setDoorArea] = useState(2.0)
  const [orientation, setOrientation] = useState('south')

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    loadDesigns()
  }, [])

  const loadDesigns = async () => {
    setLoading(true)
    try {
      const res = await API.listDesigns()
      setDesigns(res.data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleDuplicate = async (id: string) => {
    try {
      await API.duplicateDesign(id)
      loadDesigns()
    } catch {
      alert('Failed to duplicate design.')
    }
  }

  const handleDelete = async (id: string, designName: string) => {
    if (!window.confirm(`Are you sure you want to delete blueprint "${designName}"?`)) {
      return
    }
    setDeletingId(id)
    try {
      await API.deleteDesign(id)
      loadDesigns()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete design.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await API.createDesign({
        name,
        description,
        design_type: 'parametric',
        length,
        width,
        height,
        wall_thickness: wallThk,
        roof_thickness: roofThk,
        floor_thickness: floorThk,
        window_area: windowArea,
        door_area: doorArea,
        orientation,
        glazing_u_value: 2.8,
      })
      setShowAddModal(false)
      loadDesigns()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create design.')
    }
  }

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      alert('Please select a CAD or mesh file (.step, .stp, .iges, .igs, .stl, .cdb, .ans).')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('name', name || selectedFile.name.replace(/\.[^/.]+$/, ''))
      formData.append('description', description || 'Imported 3D CAD Geometry')
      formData.append('length', length.toString())
      formData.append('width', width.toString())
      formData.append('height', height.toString())
      formData.append('wall_thickness', wallThk.toString())
      formData.append('roof_thickness', roofThk.toString())
      formData.append('floor_thickness', floorThk.toString())
      formData.append('orientation', orientation)

      await API.uploadDesign(formData)
      setShowUploadModal(false)
      setSelectedFile(null)
      loadDesigns()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to upload CAD file.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1A1D24] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-white mb-1">
            <span className="w-2 h-2 rounded-full bg-white"></span>
            Architectural Geometry Archive
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Box className="w-6 h-6 text-white" />
            <span>Shelter Architecture & Geometry Database</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Parametric 3D solid models and imported CAD geometries (.STEP, .IGES, .CDB) for ANSYS MAPDL meshing.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => {
              setName('')
              setDescription('')
              setSelectedFile(null)
              setShowUploadModal(true)
            }}
            className="btn btn-secondary text-xs flex items-center gap-2"
          >
            <Upload size={14} />
            <span>Upload CAD (.STEP / .CDB)</span>
          </button>
          <button
            onClick={() => {
              setName('')
              setDescription('')
              setShowAddModal(true)
            }}
            className="btn btn-primary text-xs flex items-center gap-2"
          >
            <Plus size={14} />
            <span>Create Parametric Blueprint</span>
          </button>
        </div>
      </div>

      {/* Grid of designs */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400 font-mono">
          Loading architectural models...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {designs.map(d => (
            <div
              key={d.id}
              className="mono-card p-5 space-y-4 flex flex-col justify-between hover:border-slate-600 transition-all"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-3 border-b border-[#1A1D24] pb-3">
                  <div>
                    <span className="font-semibold text-base text-white block">
                      {d.name}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono block mt-0.5">
                      ID: {d.id}
                    </span>
                  </div>
                  <span className="badge badge-completed text-[10px] uppercase font-mono">
                    {d.design_type}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {d.description || 'Parametric rectangular shelter model with solid wall shells.'}
                </p>
              </div>

              {/* Dimensional / CAD Specification Box */}
              <div className="bg-[#0D0F13] p-4 rounded-lg border border-[#1A1D24] space-y-2.5 text-xs">
                <div className="flex items-center justify-between border-b border-[#1A1D24] pb-1">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    {d.design_type === 'imported' ? 'CAD Geometry Specification' : 'Dimensional Specification'}
                  </span>
                  {d.design_type === 'imported' && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                      {d.file_format ? `.${d.file_format.toUpperCase()}` : '3D CAD'}
                    </span>
                  )}
                </div>

                {d.design_type === 'imported' ? (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 font-mono">
                    <div>
                      <span className="text-slate-400 block text-[11px]">Bounding Span:</span>
                      <span className="font-bold text-white">
                        {d.length}m (L) × {d.width}m (W)
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Height (Z max):</span>
                      <span className="font-bold text-white">{d.height}m</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Envelope Shell:</span>
                      <span className="font-bold text-slate-200">
                        Geometry-Defined 3D Solid
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Roof / Apex:</span>
                      <span className="font-bold text-slate-200">
                        Sculpted B-Rep Surface
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Windows / Openings:</span>
                      <span className="font-bold text-white">
                        Integrated CAD Cutouts
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Enclosed Volume:</span>
                      <span className="font-bold text-slate-200">
                        {(d.length * d.width * d.height).toFixed(1)} m³
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 font-mono">
                    <div>
                      <span className="text-slate-400 block text-[11px]">Footprint:</span>
                      <span className="font-bold text-white">
                        {d.length}m (L) × {d.width}m (W)
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Height (Z):</span>
                      <span className="font-bold text-white">{d.height}m</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Wall Thickness:</span>
                      <span className="font-bold text-slate-200">
                        {(d.wall_thickness * 100).toFixed(0)} cm
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Roof Thickness:</span>
                      <span className="font-bold text-slate-200">
                        {(d.roof_thickness * 100).toFixed(0)} cm
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">South Window Area:</span>
                      <span className="font-bold text-white">
                        {d.window_area ?? 1.5} m²
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Internal Volume:</span>
                      <span className="font-bold text-slate-200">
                        {(d.length * d.width * d.height).toFixed(1)} m³
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#1A1D24] text-xs">
                <span className="text-[11px] text-slate-500 font-mono">
                  {d.is_builtin ? 'Built-in Blueprint' : `Custom ${d.design_type}`}
                </span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleDuplicate(d.id)}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 cursor-pointer transition-colors font-medium"
                  >
                    <Copy size={13} />
                    <span>Duplicate</span>
                  </button>
                  <button
                    onClick={() => handleDelete(d.id, d.name)}
                    disabled={deletingId === d.id}
                    className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1 cursor-pointer transition-colors font-medium"
                    title="Delete blueprint"
                  >
                    {deletingId === d.id ? (
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

      {/* Add Parametric Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="mono-card max-w-xl w-full p-6 space-y-5 border border-[#262A34] bg-[#121418] shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1A1D24] pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Plus size={16} className="text-white" />
                <span>New Parametric Shelter Blueprint</span>
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
                <label className="label">Blueprint Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. High-Altitude 6x4m Extended Trombe Shelter"
                  className="input"
                />
              </div>

              <div>
                <label className="label">Description / Application Notes</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Purpose of shelter, occupant capacity, Ladakh climate zone..."
                  className="input h-16"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label">Length (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    value={length}
                    onChange={e => setLength(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Width (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    value={width}
                    onChange={e => setWidth(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Height (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    value={height}
                    onChange={e => setHeight(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Wall Thk (m)</label>
                  <input
                    type="number"
                    step="0.05"
                    required
                    value={wallThk}
                    onChange={e => setWallThk(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Roof Thk (m)</label>
                  <input
                    type="number"
                    step="0.05"
                    required
                    value={roofThk}
                    onChange={e => setRoofThk(parseFloat(e.target.value))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Window Area (m²)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    value={windowArea}
                    onChange={e => setWindowArea(parseFloat(e.target.value))}
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
                  Save Blueprint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload CAD File Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="mono-card max-w-xl w-full p-6 space-y-5 border border-[#262A34] bg-[#121418] shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1A1D24] pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FileCode2 size={16} className="text-white" />
                <span>Upload CAD / Mesh File for ANSYS MAPDL</span>
              </h2>
              <button
                type="button"
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4 text-xs">
              {/* File Dropzone */}
              <div className="border-2 border-dashed border-[#262A34] hover:border-white/40 rounded-xl p-6 text-center space-y-2 bg-[#0D0F13] transition-colors cursor-pointer">
                <Upload className="w-8 h-8 text-white mx-auto mb-1" />
                <label className="block cursor-pointer">
                  <span className="font-semibold text-white block text-sm">
                    Click to browse or drop CAD geometry file
                  </span>
                  <span className="text-[11px] text-slate-400 block mt-1">
                    Supports <strong>.STEP, .STP, .IGES, .IGS, .CDB, .ANS, .STL</strong>
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">
                    From ANSYS Discovery (.dsco) / SpaceClaim, export via File → Export → STEP or CDB
                  </span>
                  <input
                    type="file"
                    accept=".step,.stp,.iges,.igs,.stl,.cdb,.ans"
                    onChange={e => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0])
                        if (!name) {
                          setName(e.target.files[0].name.replace(/\.[^/.]+$/, ''))
                        }
                      }
                    }}
                    className="hidden"
                  />
                </label>
                {selectedFile && (
                  <div className="bg-[#161920] border border-emerald-500/30 px-3 py-1.5 rounded-lg inline-flex items-center gap-2 text-emerald-400 font-bold mt-2 font-mono text-xs">
                    <CheckCircle2 size={14} />
                    <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                  </div>
                )}
              </div>

              <div>
                <label className="label">Design Model Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Custom Hexagonal Passive Shelter"
                  className="input"
                />
              </div>

              <div className="p-3.5 rounded-lg bg-[#0D0F13] border border-[#1A1D24] text-xs space-y-1.5">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Sparkles size={14} className="text-sky-400 shrink-0" />
                  <span>Automatic 3D Dimension & Volume Extraction</span>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Length, width, apex height, bounding span, and solid volume are automatically computed directly from your CAD geometry via OpenCASCADE B-Rep analysis upon upload. Manual dimensions are not needed.
                </p>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-[#1A1D24]">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="btn btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !selectedFile}
                  className="btn btn-primary text-xs flex items-center gap-2"
                >
                  {uploading ? (
                    <span>Uploading CAD...</span>
                  ) : (
                    <>
                      <Upload size={14} />
                      <span>Upload to Library</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
