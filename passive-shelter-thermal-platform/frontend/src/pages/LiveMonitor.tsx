import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { API, SimulationJob } from '../api'
import {
  Activity,
  Award,
  RefreshCw,
  Cpu,
  AlertCircle,
  ArrowRight
} from 'lucide-react'

interface LiveMonitorProps {
  wsLastMessage?: any
}

export const LiveMonitor: React.FC<LiveMonitorProps> = ({ wsLastMessage }) => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const configId = searchParams.get('config_id')
  const [activeConfigId, setActiveConfigId] = useState<string | null>(configId)
  const [jobs, setJobs] = useState<SimulationJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (configId) {
      setActiveConfigId(configId)
    } else {
      API.getLatestConfig()
        .then(res => {
          if (res.data?.config_id) {
            setActiveConfigId(res.data.config_id)
          } else {
            setLoading(false)
          }
        })
        .catch(() => {
          setLoading(false)
        })
    }
  }, [configId])

  // Fetch jobs for this config or latest active
  useEffect(() => {
    if (!activeConfigId) return
    fetchJobs(activeConfigId)
    const interval = setInterval(() => fetchJobs(activeConfigId), 3000)
    return () => clearInterval(interval)
  }, [activeConfigId])

  // React to WS updates
  useEffect(() => {
    if (wsLastMessage && wsLastMessage.type === 'job_update') {
      const payload = wsLastMessage.payload
      setJobs(prev =>
        prev.map(j =>
          j.id === payload.job_id
            ? { ...j, status: payload.status, progress_message: payload.progress_message, error_message: payload.error_message }
            : j
        )
      )
    }
  }, [wsLastMessage])

  const fetchJobs = async (targetId: string) => {
    try {
      const res = await API.listJobs(targetId)
      setJobs(res.data)
      setError(null)
    } catch (err: any) {
      setError('Could not load simulation jobs.')
    } finally {
      setLoading(false)
    }
  }

  const allCompleted = jobs.length > 0 && jobs.every(j => j.status === 'COMPLETED' || j.status === 'FAILED' || j.status === 'CANCELLED')
  const hasCompleted = jobs.some(j => j.status === 'COMPLETED')

  const stages = [
    { key: 'PREPARING', label: 'Prep' },
    { key: 'LOADING_GEOMETRY', label: 'Geometry' },
    { key: 'ASSIGNING_MATERIAL', label: 'Material' },
    { key: 'MESHING', label: 'Mesh' },
    { key: 'APPLYING_BOUNDARY_CONDITIONS', label: 'Boundary' },
    { key: 'SOLVING', label: 'MAPDL Solve' },
    { key: 'POST_PROCESSING', label: 'Post-Proc' },
    { key: 'COMPLETED', label: 'Done' },
  ]

  const getStageIndex = (status: string) => {
    return stages.findIndex(s => s.key === status)
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1A1D24] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-white mb-1">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
            Real-Time FEA Execution Telemetry
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-white" />
            <span>Live ANSYS Solver Monitor</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time finite-element transient thermal runs in local ANSYS MAPDL via PyMAPDL gRPC.
          </p>
        </div>

        {hasCompleted && activeConfigId && (
          <button
            onClick={() => navigate(`/recommendations?config_id=${activeConfigId}`)}
            className="btn btn-primary text-xs py-2.5 px-5 flex items-center gap-2"
          >
            <Award className="w-4 h-4" />
            <span>View Recommendation Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-lg bg-rose-500/15 border border-rose-500/30 p-4 text-xs font-mono flex items-center gap-2 text-rose-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* No Config Loaded */}
      {!activeConfigId && (
        <div className="mono-card p-12 text-center space-y-4 max-w-lg mx-auto my-12">
          <div className="w-12 h-12 rounded-xl bg-white/10 border border-white/20 mx-auto flex items-center justify-center text-white">
            <Cpu className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white">No Active Simulation Config Loaded</h2>
          <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
            Configure parameters and launch a transient thermal run from the Simulation Studio to track real-time solver execution.
          </p>
          <button
            onClick={() => navigate('/')}
            className="btn btn-primary text-xs"
          >
            Open Simulation Studio
          </button>
        </div>
      )}

      {activeConfigId && (
        <div className="space-y-5">
          {/* Progress Summary Banner */}
          <div className="mono-card p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#121418] border border-[#20242C]">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center shrink-0 text-white">
                <RefreshCw className={`w-5 h-5 ${!allCompleted ? 'animate-spin' : ''}`} />
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Batch Execution Status
                </span>
                <span className="text-base font-bold text-white">
                  {allCompleted ? 'Batch Execution Completed' : 'Simulations in Progress on Local ANSYS Kernel'}
                </span>
                <span className="text-xs text-slate-400 font-mono block mt-0.5">
                  Batch ID: {activeConfigId}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs border-t sm:border-t-0 pt-2 sm:pt-0 border-[#20242C] w-full sm:w-auto justify-between sm:justify-end">
              <div>
                <span className="text-slate-400 block text-[11px] uppercase tracking-wider">Completed</span>
                <span className="font-bold text-emerald-400 text-base font-mono">
                  {jobs.filter(j => j.status === 'COMPLETED').length} <span className="text-slate-500 text-xs font-normal">/</span> {jobs.length}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px] uppercase tracking-wider">Active State</span>
                <span className={`text-xs font-semibold uppercase ${allCompleted ? 'text-emerald-400' : 'text-white animate-pulse'}`}>
                  {allCompleted ? 'Finished' : 'Running'}
                </span>
              </div>
            </div>
          </div>

          {/* Job List Cards */}
          <div className="space-y-4">
            {jobs.map((job, idx) => {
              const stageIdx = getStageIndex(job.status)
              const isRunning = !['COMPLETED', 'FAILED', 'CANCELLED', 'QUEUED'].includes(job.status)
              const isDone = job.status === 'COMPLETED'
              const isFailed = job.status === 'FAILED'

              return (
                <div
                  key={job.id}
                  className={`mono-card p-5 space-y-4 transition-all ${
                    isRunning
                      ? 'border-sky-500/40 shadow-lg shadow-sky-500/5'
                      : isDone
                      ? 'border-emerald-500/40'
                      : isFailed
                      ? 'border-rose-500/40'
                      : 'border-[#20242C]'
                  }`}
                >
                  {/* Job Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1A1D24] pb-3">
                    <div className="flex items-center gap-3">
                      <span className="w-8 h-8 rounded-lg bg-[#181B21] border border-[#262A34] text-white flex items-center justify-center font-mono font-bold text-xs shrink-0">
                        #{idx + 1}
                      </span>
                      <div>
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <span className="font-mono font-bold text-sm text-white">{job.sim_id}</span>
                          <span className={`badge ${isDone ? 'badge-completed' : isRunning ? 'badge-solving' : isFailed ? 'badge-failed' : 'badge-queued'}`}>
                            {job.status}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400 font-mono block mt-0.5">
                          Job ID: {job.id}
                        </span>
                      </div>
                    </div>

                    {job.progress_message && (
                      <div className="text-xs text-slate-300 bg-[#0D0F13] border border-[#20242C] rounded-md px-3 py-1.5 max-w-md truncate font-mono">
                        <span className="text-white mr-1.5">&gt;</span>
                        {job.progress_message}
                      </div>
                    )}
                  </div>

                  {/* Stage Stepper with colorful segments */}
                  <div className="space-y-2">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Solver Pipeline Progression
                    </div>
                    <div className="grid grid-cols-4 sm:grid-cols-8 gap-1.5">
                      {stages.map((stg, sIdx) => {
                        const isStgActive = stg.key === job.status
                        const isStgDone = stageIdx > sIdx || isDone

                        return (
                          <div key={stg.key} className="space-y-1 text-center">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                isStgActive
                                  ? 'bg-white animate-pulse shadow-sm shadow-white/30'
                                  : isStgDone
                                  ? 'bg-emerald-500'
                                  : 'bg-[#181B21]'
                              }`}
                            />
                            <span
                              className={`text-[10px] block truncate font-medium ${
                                isStgActive
                                  ? 'text-white font-bold'
                                  : isStgDone
                                  ? 'text-emerald-400'
                                  : 'text-slate-500'
                              }`}
                            >
                              {stg.label}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Error display if failed */}
                  {isFailed && job.error_message && (
                    <div className="rounded-lg bg-rose-500/15 border border-rose-500/30 p-3 text-xs text-rose-300 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                      <span>{job.error_message}</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
