import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Bell, Menu, Activity, AlertTriangle, Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { SearchBar } from '../common/SearchBar';

interface NavbarProps {
  onToggleSidebar: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar }) => {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [defconLevel, setDefconLevel] = useState<'NORMAL' | 'ELEVATED' | 'CRITICAL'>('NORMAL');
  const [showAlertsPopover, setShowAlertsPopover] = useState(false);

  const handleGlobalSearch = (query: string) => {
    if (!query.trim()) return;
    navigate(`/conversations?search=${encodeURIComponent(query)}`);
  };

  const cycleDefcon = () => {
    if (defconLevel === 'NORMAL') setDefconLevel('ELEVATED');
    else if (defconLevel === 'ELEVATED') setDefconLevel('CRITICAL');
    else setDefconLevel('NORMAL');
  };

  return (
    <header className="h-16 border-b border-surface-border bg-surface-card/90 backdrop-blur-xl sticky top-0 z-30 px-4 lg:px-6 flex items-center justify-between shadow-card transition-colors duration-200">
      {/* Brand & SOC Indicator */}
      <div className="flex items-center gap-3.5">
        <button
          onClick={onToggleSidebar}
          className="p-2 text-slate-400 hover:text-slate-200 rounded-xl hover:bg-surface-elevated lg:hidden transition-colors border border-transparent hover:border-surface-border"
          aria-label="Toggle navigation"
        >
          <Menu size={18} />
        </button>

        <div
          className="flex items-center gap-3 cursor-pointer select-none group"
          onClick={() => navigate('/dashboard')}
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-glow-cyan group-hover:scale-105 transition-transform">
            <Shield size={18} className="stroke-[2.5]" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-sm font-sans">SOLWIN</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-500 border border-cyan-500/30 font-semibold tracking-wider">
                SOC-AI
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono hidden sm:inline leading-none mt-0.5">
              Defense Intelligence v2.4
            </span>
          </div>
        </div>
      </div>

      {/* Global search with hotkey hint */}
      <div className="flex-1 max-w-lg mx-6 hidden md:block">
        <div className="relative group">
          <SearchBar
            placeholder="Search tickets, threat vectors, IOC domains..."
            onChange={handleGlobalSearch}
            className="w-full"
          />
        </div>
      </div>

      {/* Right controls & Telemetry status */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Interactive Defcon Trigger for Hackathon Demo */}
        <button
          onClick={cycleDefcon}
          className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-mono transition-all shadow-sm ${
            defconLevel === 'NORMAL'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/20'
              : defconLevel === 'ELEVATED'
              ? 'bg-amber-500/15 border-amber-500/40 text-amber-500 hover:bg-amber-500/25 shadow-glow-amber'
              : 'bg-rose-500/20 border-rose-500/50 text-rose-500 hover:bg-rose-500/30 shadow-glow-rose animate-pulse'
          }`}
          title="Click to toggle simulated SOC Defcon level"
        >
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              defconLevel === 'NORMAL' ? 'bg-emerald-400' : defconLevel === 'ELEVATED' ? 'bg-amber-400' : 'bg-rose-400'
            }`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${
              defconLevel === 'NORMAL' ? 'bg-emerald-500' : defconLevel === 'ELEVATED' ? 'bg-amber-500' : 'bg-rose-500'
            }`}></span>
          </span>
          <span className="text-[11px] font-bold">DEFCON: {defconLevel}</span>
        </button>

        {/* Theme Switcher Button (Dark / Light) */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl border border-surface-border bg-surface-elevated/70 hover:bg-surface-elevated text-slate-400 hover:text-slate-100 transition-all shadow-sm flex items-center justify-center group"
          title={`Switch to ${theme === 'dark' ? 'Light (Minimalist)' : 'Dark (Obsidian SOC)'} Mode`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun size={17} className="text-amber-400 group-hover:rotate-45 transition-transform" />
          ) : (
            <Moon size={17} className="text-indigo-600 group-hover:-rotate-12 transition-transform" />
          )}
        </button>

        {/* Security Alerts Bell with Popover */}
        <div className="relative">
          <button
            onClick={() => setShowAlertsPopover(!showAlertsPopover)}
            className="relative p-2 text-slate-400 hover:text-slate-200 rounded-xl hover:bg-surface-elevated border border-surface-border transition-all"
            title="Active security threats"
          >
            <Bell size={17} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-surface-card shadow-glow-rose" />
          </button>

          {showAlertsPopover && (
            <div className="absolute right-0 mt-2 w-80 bg-surface-card border border-surface-border rounded-2xl shadow-dropdown p-3.5 z-50 animate-in fade-in space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
                  <AlertTriangle size={13} /> High Priority Alerts
                </span>
                <span className="text-[10px] font-mono text-slate-500">Live feed</span>
              </div>
              <button
                onClick={() => {
                  setShowAlertsPopover(false);
                  navigate('/threats');
                }}
                className="w-full py-1.5 rounded-lg bg-surface-elevated hover:bg-slate-800 text-xs font-mono text-center block transition-colors border border-surface-border"
              >
                View all active threats →
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
