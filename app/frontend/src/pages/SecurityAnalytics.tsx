import React, { useState, useEffect } from 'react';
import { getSecurityAnalytics, getSecurityTrends } from '../services/analyticsApi';
import {
  SecurityAnalytics as SecAnalyticsType,
  TrendResponse,
} from '../types/conversation';
import { ChartSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorState } from '../components/common/ErrorState';
import { LineChart, RefreshCw, Globe, AlertTriangle } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

const RISK_COLORS: Record<string, string> = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#f43f5e',
};

function toSeries(dist: Record<string, number>) {
  return Object.entries(dist).map(([name, value]) => ({ name, value }));
}

export const SecurityAnalytics: React.FC = () => {
  const [data, setData] = useState<SecAnalyticsType | null>(null);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsRes, trendsRes] = await Promise.all([
        getSecurityAnalytics(),
        getSecurityTrends(14).catch(() => null),
      ]);
      setData(analyticsRes);
      setTrends(trendsRes);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch security analytics.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="h-6 w-48 bg-slate-800 rounded animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <ErrorState title="Security Analytics Unavailable" message={error || ''} onRetry={loadData} />
    );
  }

  const CustomDarkTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface-elevated/95 border border-surface-border rounded-xl p-3 shadow-dropdown text-xs backdrop-blur-md">
          <p className="font-mono text-slate-400 mb-1">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p
              key={`item-${index}`}
              className="font-mono text-xs flex items-center justify-between gap-4"
              style={{ color: entry.color }}
            >
              <span>{entry.name}:</span>
              <span className="font-bold text-white">{entry.value}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2 font-sans">
            <LineChart size={22} className="text-rose-400" />
            <span>Security Operations & Threat Analytics</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Threat detection velocity, risk stratification, social engineering technique frequency, and indicator totals from persisted security intelligence.
          </p>
        </div>

        <button
          onClick={loadData}
          className="p-2.5 rounded-xl border border-surface-border bg-surface-card hover:bg-surface-elevated text-slate-400 hover:text-slate-100 transition-all self-start sm:self-auto shadow-sm"
          title="Refresh metrics"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Total Evaluations</span>
          <span className="text-2xl font-bold text-white">{data.total_threats.toLocaleString()}</span>
        </div>
        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Confirmed Threats</span>
          <span className="text-2xl font-bold text-rose-400">{data.threats_detected.toLocaleString()}</span>
        </div>
        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Suspicious URLs</span>
          <span className="text-2xl font-bold text-amber-400">{data.suspicious_url_count.toLocaleString()}</span>
        </div>
        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Suspicious Emails</span>
          <span className="text-2xl font-bold text-amber-400">{data.suspicious_email_count.toLocaleString()}</span>
        </div>
      </div>

      {/* Row 1: trend & risk distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Threat Velocity Over Time (14-Day Trend)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Confirmed threats per UTC day</p>
          </div>

          <div className="h-72 w-full pt-2">
            {trends && trends.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends.trends}>
                  <defs>
                    <linearGradient id="colorThreat" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="count"
                    name="Threats"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorThreat)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-slate-500">
                Not enough data yet — run security analyses to populate trends.
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Active Risk Level Stratification
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Critical vs High vs Medium vs Low distribution</p>
          </div>

          <div className="h-72 w-full pt-2 flex items-center justify-center">
            {Object.keys(data.risk_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={toSeries(data.risk_distribution)}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={95}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {Object.entries(data.risk_distribution).map(([key], index) => (
                      <Cell key={`cell-${index}`} fill={RISK_COLORS[key] || '#6366f1'} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Legend formatter={(value) => <span className="text-xs font-mono text-slate-300">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs font-mono text-slate-500">No risk data yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: threat types & techniques */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Threat Classification Breakdown
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Frequency by classified vector category</p>
          </div>

          <div className="h-72 w-full pt-2">
            {Object.keys(data.threat_type_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={Object.entries(data.threat_type_distribution).map(([name, count]) => ({
                    name,
                    count,
                  }))}
                  layout="vertical"
                  margin={{ left: 20 }}
                >
                  <XAxis type="number" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    width={150}
                  />
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Bar dataKey="count" fill="#3b82f6" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-slate-500">
                No threat classifications recorded yet.
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans flex items-center gap-2">
              <AlertTriangle size={15} className="text-amber-400" />
              <span>Social Engineering Technique Frequency</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Detected manipulation tactics across messages</p>
          </div>

          <div className="space-y-2.5 pt-1 overflow-y-auto max-h-64">
            {Object.entries(data.technique_frequency)
              .sort((a, b) => b[1] - a[1])
              .map(([technique, count], idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-xl bg-surface-elevated/70 border border-surface-border text-xs"
                >
                  <span className="font-mono text-slate-200 truncate">{technique}</span>
                  <span className="text-[11px] font-mono text-amber-300 font-semibold shrink-0 ml-2">
                    {count} detections
                  </span>
                </div>
              ))}
            {Object.keys(data.technique_frequency).length === 0 && (
              <p className="py-6 text-center text-xs font-mono text-slate-500">
                No social engineering techniques detected yet.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: recent critical threats */}
      {data.recent_critical_threats.length > 0 && (
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans flex items-center gap-2">
              <Globe size={15} className="text-rose-400" />
              <span>Recent Critical Threats</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Most recent CRITICAL severity records for review</p>
          </div>

          <div className="space-y-2.5 pt-1">
            {data.recent_critical_threats.map((threat) => (
              <div
                key={threat.threat_id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3.5 rounded-xl bg-surface-elevated/70 border border-rose-500/25 text-xs"
              >
                <div className="min-w-0">
                  <span className="font-mono font-semibold text-rose-300 block truncate">
                    {threat.threat_type || 'UNCATEGORIZED'}
                  </span>
                  {threat.risk_reasons.length > 0 && (
                    <span className="text-[11px] text-slate-500 truncate block">
                      {threat.risk_reasons[0]}
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-mono text-slate-500 shrink-0">
                  {new Date(threat.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
