import React, { useState, useEffect } from 'react'
import { API, AnsysStatus } from '../api'
import {
  Settings,
  Cpu,
  Server,
  CheckCircle2,
  AlertTriangle,
  Play,
  RefreshCw,
  FolderSearch,
  Save,
  Compass,
} from 'lucide-react'

export const AnsysSettingsPage: React.FC = () => {
  const [status, setStatus] = useState<AnsysStatus | null>(null)
  const [customPath, setCustomPath] = useState('')
  const [testing, setTesting] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState<AnsysStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
  }, [])

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const res = await API.ansysStatus()
      setStatus(res.data)
      if (res.data.mapdl_exe_path) {
        setCustomPath(res.data.mapdl_exe_path)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const handleAutoDetect = async () => {
    setDetecting(true)
    try {
      const res = await API.autoDetectAnsys()
      setStatus(res.data)
      setTestResult(res.data)
      if (res.data.mapdl_exe_path) {
        setCustomPath(res.data.mapdl_exe_path)
      }
    } catch (err: any) {
      alert('Auto-detection failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setDetecting(false)
    }
  }

  const handleSaveAndConnect = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!customPath.trim()) {
      alert('Please enter an ANSYS executable or installation path.')
      return
    }

    setSaving(true)
    try {
      const res = await API.configureAnsys({ exe_path: customPath.trim(), test_now: true })
      setStatus(res.data)
      setTestResult(res.data)
      if (res.data.mapdl_exe_path) {
        setCustomPath(res.data.mapdl_exe_path)
      }
    } catch (err: any) {
      alert('Failed to configure ANSYS path: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async () => {
    setTesting(true)
    try {
      const res = await API.testConnection()
      setTestResult(res.data)
      setStatus(res.data)
    } catch (err: any) {
      alert('Connection test failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setTesting(false)
    }
  }

  const handleQuickFill = (presetPath: string) => {
    setCustomPath(presetPath)
  }

  const isAnsysReady = status?.ansys_detected && status?.mapdl_exe_exists

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E4E4E7] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-800 mb-1">
            <span className={`w-2 h-2 rounded-full ${isAnsysReady ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            Integration & gRPC Health
          </div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight flex items-center gap-2.5">
            <Settings className="w-6 h-6 text-zinc-900" />
            <span>ANSYS MAPDL Setup & Connection</span>
          </h1>
          <p className="text-sm text-zinc-600 mt-1">
            Configure local ANSYS MAPDL binary path, academic license constraints, and PyMAPDL gRPC communication.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={handleAutoDetect}
            disabled={detecting || testing || saving}
            className="btn btn-secondary text-xs py-2 px-3 flex items-center gap-1.5 cursor-pointer"
            title="Scan system drives and environment variables"
          >
            <FolderSearch size={14} className={detecting ? 'animate-spin' : ''} />
            <span>{detecting ? 'Scanning Drives...' : 'Auto-Detect ANSYS'}</span>
          </button>

          <button
            onClick={handleTestConnection}
            disabled={testing || detecting || saving || !isAnsysReady}
            className="btn btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5 cursor-pointer"
          >
            {testing ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Testing MAPDL Launch...</span>
              </>
            ) : (
              <>
                <Play size={14} />
                <span>Test Live Connection</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Connection Status & Path Configuration Card */}
      <div className="mono-card bg-white p-6 space-y-5 border border-[#E4E4E7] shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E4E4E7] pb-4">
          <div>
            <h2 className="font-semibold text-sm text-zinc-900 flex items-center gap-2">
              <Compass size={16} className="text-zinc-900" />
              <span>Connect ANSYS Installation</span>
            </h2>
            <p className="text-xs text-zinc-500 mt-0.5">
              Specify the path to <code className="bg-zinc-100 px-1 py-0.5 rounded text-zinc-800">ansysXXX.exe</code> or the root installation directory.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-medium flex items-center gap-1.5 ${
                isAnsysReady
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border border-amber-200'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isAnsysReady ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
              {isAnsysReady ? `ANSYS v${status?.ansys_version} Connected` : 'ANSYS Not Detected'}
            </span>
          </div>
        </div>

        <form onSubmit={handleSaveAndConnect} className="space-y-4">
          <div>
            <label className="label text-xs font-semibold text-zinc-700">
              ANSYS Executable Path (ansysXXX.exe or Install Directory)
            </label>
            <div className="flex gap-2.5 mt-1.5">
              <input
                type="text"
                value={customPath}
                onChange={e => setCustomPath(e.target.value)}
                placeholder="e.g. C:\Program Files\ANSYS Inc\v242\ansys\bin\winx64\ansys242.exe"
                className="input font-mono text-xs flex-1"
              />
              <button
                type="submit"
                disabled={saving || detecting || testing}
                className="btn btn-primary text-xs px-4 flex items-center gap-1.5 shrink-0"
              >
                {saving ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    <span>Verifying & Saving...</span>
                  </>
                ) : (
                  <>
                    <Save size={14} />
                    <span>Save & Connect</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Preset Helper Paths */}
          <div className="bg-[#F8FAFC] p-3 rounded-lg border border-[#E4E4E7] space-y-1.5 text-[11px]">
            <span className="font-semibold text-zinc-700 block">Common Default Locations (click to use):</span>
            <div className="flex flex-wrap gap-2">
              {[
                { label: 'C: Student v24.2', path: 'C:\\Program Files\\ANSYS Inc\\ANSYS Student\\v242\\ansys\\bin\\winx64\\ansys242.exe' },
                { label: 'C: Commercial v24.2', path: 'C:\\Program Files\\ANSYS Inc\\v242\\ansys\\bin\\winx64\\ansys242.exe' },
                { label: 'C: Student v23.2', path: 'C:\\Program Files\\ANSYS Inc\\ANSYS Student\\v232\\ansys\\bin\\winx64\\ansys232.exe' },
                { label: 'D: Student v26.1', path: 'D:\\ANSYS\\ANSYS Inc\\ANSYS Student\\v261\\ansys\\bin\\winx64\\ansys261.exe' },
              ].map(preset => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => handleQuickFill(preset.path)}
                  className="px-2 py-1 rounded bg-white hover:bg-zinc-100 text-zinc-700 border border-zinc-200 text-[10px] font-mono cursor-pointer transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* Connection Test Result Alert */}
      {testResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 text-xs transition-all ${
            testResult.connection_successful
              ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
              : 'bg-amber-50/60 border-amber-200 text-amber-950'
          }`}
        >
          {testResult.connection_successful ? (
            <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
          )}
          <div className="space-y-1">
            <span className="font-semibold text-sm block">
              {testResult.connection_successful
                ? `Connection Successful: ANSYS MAPDL v${testResult.ansys_version} Verified`
                : 'Connection Check Failed'}
            </span>
            <p className="leading-relaxed text-zinc-700">
              {testResult.connection_successful
                ? 'PyMAPDL successfully initialized a local gRPC session, queried the solver kernel state, and cleanly decoupled. Ready for transient simulations.'
                : testResult.connection_error || 'Could not communicate with MAPDL executable at this path.'}
            </p>
          </div>
        </div>
      )}

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ANSYS MAPDL Core */}
        <div className="mono-card bg-white p-5 space-y-4 border border-[#E4E4E7] shadow-xs">
          <div className="flex items-center gap-3 border-b border-[#E4E4E7] pb-3">
            <div className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-900 shrink-0">
              <Server size={16} />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-zinc-900">ANSYS MAPDL Solver Kernel</h2>
              <span className="text-[11px] text-zinc-500 font-mono block">Mechanical APDL Engine</span>
            </div>
          </div>

          <div className="space-y-2.5 text-xs bg-[#F8FAFC] p-4 rounded-lg border border-[#E4E4E7]">
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Detected Version:</span>
              <span className="font-mono font-bold text-zinc-900">v{status?.ansys_version ?? 'Not Detected'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">License Tier:</span>
              <span className="font-semibold text-zinc-900">
                {status?.ansys_detected
                  ? status?.student_license
                    ? 'ANSYS Student (Free Academic)'
                    : 'Commercial / Research'
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Node Limit:</span>
              <span className="font-mono font-bold text-zinc-900">
                {status?.node_limit ? `${status.node_limit.toLocaleString()} Nodes` : 'Unlimited'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Binary Found:</span>
              <span className={`font-semibold ${status?.mapdl_exe_exists ? 'text-emerald-600' : 'text-amber-600'}`}>
                {status?.mapdl_exe_exists ? 'Verified on Disk' : 'Not Found'}
              </span>
            </div>
            <div className="pt-2 border-t border-[#E4E4E7]">
              <span className="text-zinc-500 block text-[11px] mb-1">Active Executable Path:</span>
              <div className="font-mono text-[10px] text-zinc-800 break-all bg-white p-2 rounded border border-[#E4E4E7]">
                {status?.mapdl_exe_path || 'No executable configured'}
              </div>
            </div>
          </div>
        </div>

        {/* PyMAPDL Python Interface */}
        <div className="mono-card bg-white p-5 space-y-4 border border-[#E4E4E7] shadow-xs">
          <div className="flex items-center gap-3 border-b border-[#E4E4E7] pb-3">
            <div className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-900 shrink-0">
              <Cpu size={16} />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-zinc-900">PyAnsys Gateway</h2>
              <span className="text-[11px] text-zinc-500 font-mono block">ansys-mapdl-core</span>
            </div>
          </div>

          <div className="space-y-2.5 text-xs bg-[#F8FAFC] p-4 rounded-lg border border-[#E4E4E7]">
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">PyMAPDL Version:</span>
              <span className="font-mono font-bold text-zinc-900">{status?.pymapdl_version ?? '0.74.1'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Communication Mode:</span>
              <span className="font-semibold text-zinc-900">gRPC (Binary Stream)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Default gRPC Port:</span>
              <span className="font-mono font-bold text-zinc-800">50052</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Process Concurrency:</span>
              <span className="font-mono font-bold text-zinc-800">1 (Sequential Safe Queue)</span>
            </div>
            <div className="pt-2 border-t border-[#E4E4E7]">
              <span className="text-zinc-500 block text-[11px] mb-1">Root Directory:</span>
              <div className="font-mono text-[10px] text-zinc-800 break-all bg-white p-2 rounded border border-[#E4E4E7]">
                {status?.ansys_install_path || 'Not located'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
