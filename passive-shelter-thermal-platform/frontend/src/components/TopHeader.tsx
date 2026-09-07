import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API, AnsysStatus } from '../api'
import { Server, WifiOff, Zap } from 'lucide-react'

interface TopHeaderProps {
  wsConnected: boolean
  onQuickLoadLeh?: () => void
}

export const TopHeader: React.FC<TopHeaderProps> = ({ wsConnected, onQuickLoadLeh }) => {
  const [ansysStatus, setAnsysStatus] = useState<AnsysStatus | null>(null)

  useEffect(() => {
    fetchStatus()
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await API.ansysStatus()
      setAnsysStatus(res.data)
    } catch {
      // ignore
    }
  }

  const isAnsysReady = ansysStatus?.ansys_detected && ansysStatus?.mapdl_exe_exists

  return (
    <header className="h-14 border-b border-slate-200 bg-white px-6 flex items-center justify-between shrink-0">
      {/* Left: active system status */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="font-semibold text-slate-800 tracking-tight">System Operational</span>
        <span className="w-1 h-1 rounded-full bg-slate-300" />
        <span>PyAnsys Transient FEA Core</span>
        <span className="w-1 h-1 rounded-full bg-slate-300" />
        <span className="font-mono text-[11px] text-slate-400">gRPC v0.74.1</span>
      </div>

      {/* Right: Telemetry & Quick Action */}
      <div className="flex items-center gap-3">
        {onQuickLoadLeh && (
          <button
            onClick={onQuickLoadLeh}
            className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 cursor-pointer text-zinc-900 border-zinc-300 hover:bg-zinc-100 hover:border-black transition-all"
            title="Pre-fill Studio with Leh, Ladakh coordinates & -15°C winter climate window"
          >
            <Zap size={13} className="text-zinc-900" />
            <span>Load Leh Winter Baseline</span>
          </button>
        )}

        {/* Telemetry pill */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-xs">
          {wsConnected ? (
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-1.5 h-1.5 rounded-full bg-black animate-pulse" />
              <span className="font-mono text-[11px]">Live WebSocket</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-slate-400">
              <WifiOff size={12} />
              <span className="font-mono text-[11px]">Telemetry Offline</span>
            </span>
          )}
        </div>

        <div className="w-[1px] h-4 bg-slate-200" />

        {/* Clickable ANSYS solver badge */}
        <Link
          to="/settings"
          className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs shadow-xs transition-colors cursor-pointer hover:opacity-90 ${
            isAnsysReady
              ? 'bg-emerald-50/70 border-emerald-300 text-emerald-900'
              : 'bg-amber-50/70 border-amber-300 text-amber-900'
          }`}
          title="Click to view ANSYS MAPDL Setup & Connection Diagnostics"
        >
          <Server size={12} className={isAnsysReady ? 'text-emerald-700' : 'text-amber-700'} />
          <span className="font-medium">ANSYS MAPDL:</span>
          <span className="font-mono font-bold">
            {isAnsysReady ? `v${ansysStatus?.ansys_version}` : 'Not Detected'}
          </span>
          <span className="inline-flex items-center gap-1 text-[10px] font-mono ml-1">
            <span className={`w-1.5 h-1.5 rounded-full ${isAnsysReady ? 'bg-emerald-600' : 'bg-amber-600 animate-pulse'}`} />
            {isAnsysReady ? 'Ready' : 'Configure'}
          </span>
        </Link>
      </div>
    </header>
  )
}
