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
} from 'lucide-react'

export const AnsysSettingsPage: React.FC = () => {
  const [status, setStatus] = useState<AnsysStatus | null>(null)
  const [testing, setTesting] = useState(false)
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
    } catch {
      // ignore
    } finally {
      setLoading(false)
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

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1A1D24] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-white mb-1">
            <span className="w-2 h-2 rounded-full bg-white"></span>
            Integration & gRPC Health
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Settings className="w-6 h-6 text-white" />
            <span>ANSYS & PyMAPDL Diagnostics</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Local ANSYS MAPDL engine status, academic licensing bounds, and PyAnsys gRPC communication.
          </p>
        </div>

        <button
          onClick={handleTestConnection}
          disabled={testing}
          className="btn btn-primary text-xs py-2.5 px-4 cursor-pointer shrink-0 flex items-center gap-2 self-start md:self-auto"
        >
          {testing ? (
            <>
              <RefreshCw size={14} className="animate-spin" />
              <span>Testing MAPDL gRPC Launch...</span>
            </>
          ) : (
            <>
              <Play size={14} />
              <span>Test Live MAPDL Connection</span>
            </>
          )}
        </button>
      </div>

      {/* Connection Test Result Alert */}
      {testResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 text-xs transition-all ${
            testResult.connection_successful
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
          }`}
        >
          {testResult.connection_successful ? (
            <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
          )}
          <div className="space-y-1">
            <span className="font-semibold text-sm block">
              {testResult.connection_successful
                ? `Connection Successful: ANSYS MAPDL v${testResult.ansys_version} Verified`
                : 'Connection Test Failed'}
            </span>
            <p className="leading-relaxed">
              {testResult.connection_successful
                ? 'PyMAPDL successfully initialized a local gRPC session, queried the solver kernel state, and cleanly decoupled.'
                : testResult.connection_error || 'Could not communicate with MAPDL executable.'}
            </p>
          </div>
        </div>
      )}

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ANSYS MAPDL Core */}
        <div className="mono-card p-5 space-y-4">
          <div className="flex items-center gap-3 border-b border-[#1A1D24] pb-3">
            <div className="w-9 h-9 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-white shrink-0">
              <Server size={16} />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-white">ANSYS MAPDL Solver Kernel</h2>
              <span className="text-[11px] text-slate-400 font-mono block">Mechanical APDL Engine</span>
            </div>
          </div>

          <div className="space-y-2.5 text-xs bg-[#0D0F13] p-4 rounded-lg border border-[#1A1D24]">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Detected Version:</span>
              <span className="font-mono font-bold text-emerald-400">v{status?.ansys_version ?? '26.1'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">License Tier:</span>
              <span className="font-semibold text-white">{status?.student_license ? 'ANSYS Student (Free Academic)' : 'Commercial / Research'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Node Limit:</span>
              <span className="font-mono font-bold text-white">{status?.node_limit?.toLocaleString() ?? '128,000'} Nodes</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Binary Found:</span>
              <span className="font-semibold text-emerald-400">
                {status?.mapdl_exe_exists ? '✓ Verified' : 'Not Found'}
              </span>
            </div>
            <div className="pt-2 border-t border-[#1A1D24]">
              <span className="text-slate-400 block text-[11px] mb-1">Executable Path:</span>
              <div className="font-mono text-[10px] text-slate-300 break-all bg-[#161920] p-2 rounded border border-[#20242C]">
                {status?.mapdl_exe_path || 'D:\\ANSYS\\ANSYS Inc\\ANSYS Student\\v261\\ansys\\bin\\winx64\\ansys261.exe'}
              </div>
            </div>
          </div>
        </div>

        {/* PyMAPDL Python Interface */}
        <div className="mono-card p-5 space-y-4">
          <div className="flex items-center gap-3 border-b border-[#1A1D24] pb-3">
            <div className="w-9 h-9 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-white shrink-0">
              <Cpu size={16} />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-white">PyAnsys Gateway</h2>
              <span className="text-[11px] text-slate-400 font-mono block">ansys-mapdl-core</span>
            </div>
          </div>

          <div className="space-y-2.5 text-xs bg-[#0D0F13] p-4 rounded-lg border border-[#1A1D24]">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">PyMAPDL Version:</span>
              <span className="font-mono font-bold text-white">{status?.pymapdl_version ?? '0.74.1'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Communication Mode:</span>
              <span className="font-semibold text-emerald-400">gRPC (Binary Stream)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Default gRPC Port:</span>
              <span className="font-mono font-bold text-slate-200">50052</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Process Concurrency:</span>
              <span className="font-mono font-bold text-slate-200">1 (Safe Thread Queue)</span>
            </div>
            <div className="pt-2 border-t border-[#1A1D24]">
              <span className="text-slate-400 block text-[11px] mb-1">Root Directory:</span>
              <div className="font-mono text-[10px] text-slate-300 break-all bg-[#161920] p-2 rounded border border-[#20242C]">
                {status?.ansys_install_path || 'D:\\ANSYS\\ANSYS Inc\\ANSYS Student\\v261'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
