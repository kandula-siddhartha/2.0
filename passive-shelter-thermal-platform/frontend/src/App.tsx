import React, { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { SimulationStudio } from './pages/SimulationStudio'
import { LiveMonitor } from './pages/LiveMonitor'
import { RecommendationDashboard } from './pages/RecommendationDashboard'
import { MaterialLibrary } from './pages/MaterialLibrary'
import { DesignLibrary } from './pages/DesignLibrary'
import { ReportsPage } from './pages/ReportsPage'
import { AnsysSettingsPage } from './pages/AnsysSettingsPage'

export const App: React.FC = () => {
  const [wsConnected, setWsConnected] = useState(false)
  const [wsLastMessage, setWsLastMessage] = useState<any>(null)

  useEffect(() => {
    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    let ws: WebSocket | null = null

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          setWsConnected(true)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            setWsLastMessage(data)
          } catch {
            // ignore
          }
        }

        ws.onclose = () => {
          setWsConnected(false)
          // Reconnect after 3s
          setTimeout(connect, 3000)
        }

        ws.onerror = () => {
          setWsConnected(false)
        }
      } catch {
        setWsConnected(false)
      }
    }

    connect()

    return () => {
      if (ws) ws.close()
    }
  }, [])

  return (
    <div className="flex min-h-screen bg-[#0B0F17] text-slate-100">
      {/* Fixed Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 overflow-y-auto bg-[#0B0F17]">
          <Routes>
            <Route path="/" element={<SimulationStudio />} />
            <Route path="/monitor" element={<LiveMonitor wsLastMessage={wsLastMessage} />} />
            <Route path="/recommendations" element={<RecommendationDashboard />} />
            <Route path="/materials" element={<MaterialLibrary />} />
            <Route path="/designs" element={<DesignLibrary />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<AnsysSettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
