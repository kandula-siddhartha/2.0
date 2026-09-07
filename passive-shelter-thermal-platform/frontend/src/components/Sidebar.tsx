import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  Award,
  Layers,
  Box,
  Settings,
  Compass
} from 'lucide-react'
import brandLogo from '../assets/brand-logo.png'

export const Sidebar: React.FC = () => {
  const links = [
    { to: '/', label: 'Simulation Studio', icon: Compass, exact: true },
    { to: '/recommendations', label: 'Results & Rec.', icon: Award },
    { to: '/materials', label: 'Material Library', icon: Layers },
    { to: '/designs', label: 'Shelter Designs', icon: Box },
    { to: '/settings', label: 'ANSYS Setup', icon: Settings },
  ]

  return (
    <aside className="w-60 flex flex-col justify-between shrink-0 h-screen sticky top-0 bg-[#FFFFFF] border-r border-[#E4E4E7]">
      <div>
        {/* Brand Header */}
        <div className="p-4 flex items-center gap-3 border-b border-[#E4E4E7]">
          <div className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center shrink-0 p-1">
            <img
              src={brandLogo}
              alt="ThermoAdapt Emblem"
              className="w-full h-full object-contain filter grayscale contrast-125"
            />
          </div>
          <div>
            <h1 className="font-bold text-sm text-zinc-900 leading-tight">
              ThermoAdapt
            </h1>
            <span className="text-[11px] text-zinc-500 font-mono">
              PyAnsys · v26.1
            </span>
          </div>
        </div>

        {/* Section Label */}
        <div className="px-4 pt-4 pb-2">
          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
            Navigation
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="px-2 space-y-1">
          {links.map((link) => {
            const Icon = link.icon
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.exact}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'active' : ''}`
                }
              >
                <Icon size={16} strokeWidth={1.8} className="shrink-0" />
                <span>{link.label}</span>
              </NavLink>
            )
          })}
        </nav>
      </div>
    </aside>
  )
}
