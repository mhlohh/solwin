import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import { API_BASE_URL } from '../services/api';
import { Settings as SettingsIcon, Server, Shield, Check, Sun, Moon, Palette } from 'lucide-react';

export const Settings: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState(API_BASE_URL);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('solwin_custom_api_url', apiUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="max-w-4xl space-y-6 mx-auto pb-12">
      <div className="pb-4 border-b border-surface-border">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono uppercase font-bold tracking-wider text-brand-cyan">
            ENVIRONMENT TELEMETRY
          </span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold font-sans tracking-tight text-white flex items-center gap-2">
          <SettingsIcon size={22} className="text-brand-cyan" />
          <span>Platform Configuration & Gateway Settings</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Manage REST API integration endpoints, display themes, and diagnostic telemetry.
        </p>
      </div>

      {/* Theme Selection Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-card space-y-4">
        <div className="flex items-center gap-2 text-white">
          <Palette size={18} className="text-brand-cyan" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
            Interface Theme & Visual Style
          </h2>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          Select between our high-density defense-grade <strong>Dark Mode</strong> (Obsidian SOC theme) or clean <strong>Light Mode</strong> (Minimalist Enterprise theme).
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl pt-1">
          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3.5 ${
              theme === 'dark'
                ? 'bg-slate-900 border-brand-cyan shadow-glow-cyan/20 text-white'
                : 'bg-surface-elevated/70 border-surface-border hover:border-slate-600 text-slate-400'
            }`}
          >
            <div className="p-2 rounded-lg bg-surface-card border border-surface-border text-brand-cyan">
              <Moon size={18} />
            </div>
            <div>
              <div className="font-semibold text-xs text-slate-100">Dark (Obsidian SOC)</div>
              <p className="text-[11px] text-slate-400 mt-0.5">High-contrast tactical dark command center for SOC analysts</p>
              {theme === 'dark' && (
                <span className="text-[10px] font-mono text-brand-cyan mt-2 inline-block font-semibold">
                  ✓ ACTIVE THEME
                </span>
              )}
            </div>
          </button>

          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3.5 ${
              theme === 'light'
                ? 'bg-white border-brand-blue shadow-md text-slate-900'
                : 'bg-surface-elevated/70 border-surface-border hover:border-slate-600 text-slate-400'
            }`}
          >
            <div className="p-2 rounded-lg bg-slate-100 border border-slate-200 text-amber-500">
              <Sun size={18} />
            </div>
            <div>
              <div className="font-semibold text-xs text-slate-900">Light (Minimalist Enterprise)</div>
              <p className="text-[11px] text-slate-500 mt-0.5">Clean, airy, and distraction-free daytime workspace</p>
              {theme === 'light' && (
                <span className="text-[10px] font-mono text-blue-600 mt-2 inline-block font-semibold">
                  ✓ ACTIVE THEME
                </span>
              )}
            </div>
          </button>
        </div>
      </div>

      {/* Backend API Configuration */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-card space-y-4">
        <div className="flex items-center gap-2 text-white">
          <Server size={18} className="text-brand-cyan" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
            Backend REST API Connection
          </h2>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          The SOLWIN frontend communicates strictly with your Python/FastAPI backend over REST. All classification, sentiment, and threat vectors are retrieved live.
        </p>

        <form onSubmit={handleSave} className="space-y-4 max-w-xl">
          <div>
            <label className="text-xs font-mono font-medium text-slate-300 block mb-1">
              Active Gateway Base URL
            </label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs font-mono text-white focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan/40 shadow-sm"
            />
            <span className="text-[11px] text-slate-500 font-mono mt-1.5 block">
              Default: http://localhost:8001/api/v1
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-brand-cyan to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-bold font-mono uppercase tracking-wider shadow-glow-cyan/25 transition-all"
            >
              Update Gateway Endpoint
            </button>
            {saved && (
              <span className="text-xs font-mono text-emerald-400 flex items-center gap-1">
                <Check size={14} /> Saved successfully
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Gateway Diagnostics */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-card space-y-4">
        <div className="flex items-center gap-2 text-white">
          <Shield size={18} className="text-brand-cyan" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
            Connection Diagnostics
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-border">
            <span className="text-[10px] font-mono text-slate-500 block mb-1">Gateway Base URL</span>
            <span className="font-mono text-brand-cyan">{API_BASE_URL}</span>
          </div>

          <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-border">
            <span className="text-[10px] font-mono text-slate-500 block mb-1">Transport</span>
            <span className="font-mono text-slate-300">REST / JSON</span>
          </div>

          <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-border">
            <span className="text-[10px] font-mono text-slate-500 block mb-1">Intelligence Source</span>
            <span className="font-mono text-emerald-400 uppercase font-bold">Backend + ML Pipeline</span>
          </div>

          <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-border">
            <span className="text-[10px] font-mono text-slate-500 block mb-1">Access Mode</span>
            <span className="font-mono text-slate-300">Public (no authentication)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
