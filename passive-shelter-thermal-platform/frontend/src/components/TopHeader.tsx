import React, { useEffect, useState } from 'react'
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

  return (
    <header className="h-14 px-6 flex items-center justify-between sticky top-0 z-30 bg-[#0E1624] border-b border-[#1E293B]">
      {/* Left: Quick-Load (if provided) */}
      <div className="flex items-center gap-3">
        {onQuickLoadLeh && (
          <button
            onClick={onQuickLoadLeh}
            className="px-2.5 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/25 text-sky-300 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Zap size={13} className="text-sky-400" />
            <span>Quick-Load Leh</span>
          </button>
        )}
      </div>

      {/* Right: Status indicators */}
      <div className="flex items-center gap-4">
        {/* WebSocket status */}
        <div className="flex items-center gap-2 text-xs font-medium">
          {wsConnected ? (
            <span className="inline-flex items-center gap-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Telemetry
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-slate-500">
              <WifiOff size={13} />
              Offline
            </span>
          )}
        </div>

        <div className="w-[1px] h-4 bg-[#223049]" />

        {/* ANSYS solver badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#141E30] border border-[#223049] text-xs">
          <Server size={13} className="text-slate-400" />
          <span className="text-slate-400">ANSYS:</span>
          <span className="font-mono font-semibold text-slate-200">
            {ansysStatus?.ansys_version ? `v${ansysStatus.ansys_version}` : 'v26.1'}
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        </div>
      </div>
    </header>
  )
}
