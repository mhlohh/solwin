import React, { useState, useEffect } from 'react';
import { getCustomerAnalytics, getCustomerTrends } from '../services/analyticsApi';
import { CustomerAnalytics, TrendResponse } from '../types/conversation';
import { ChartSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorState } from '../components/common/ErrorState';
import { Users, RefreshCw } from 'lucide-react';
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

const PRIORITY_COLORS: Record<string, string> = {
  LOW: '#64748b',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#f43f5e',
};

const SENTIMENT_COLORS: Record<string, string> = {
  POSITIVE: '#10b981',
  NEUTRAL: '#94a3b8',
  NEGATIVE: '#f43f5e',
};

const RESOLUTION_COLORS: Record<string, string> = {
  RESOLVED: '#10b981',
  UNRESOLVED: '#f43f5e',
  PARTIALLY_RESOLVED: '#f59e0b',
  UNKNOWN: '#64748b',
};

function toSeries(dist: Record<string, number>, nameKey = 'name'): { [k: string]: string | number }[] {
  return Object.entries(dist).map(([key, count]) => ({ [nameKey]: key, count }));
}

export const CustomerInsights: React.FC = () => {
  const [data, setData] = useState<CustomerAnalytics | null>(null);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsRes, trendsRes] = await Promise.all([
        getCustomerAnalytics(),
        getCustomerTrends(14).catch(() => null),
      ]);
      setData(analyticsRes);
      setTrends(trendsRes);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch customer insights.');
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
    return <ErrorState title="Insights Unavailable" message={error || ''} onRetry={loadData} />;
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
            <Users size={22} className="text-brand-cyan" />
            <span>Customer Support Intelligence</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Sentiment distribution, problem category clusters, priority stratification, and resolution efficacy — all computed from persisted analysis records.
          </p>
        </div>

        <button
          onClick={loadData}
          className="p-2.5 rounded-xl border border-surface-border bg-surface-card hover:bg-surface-elevated text-slate-400 hover:text-slate-100 transition-all self-start sm:self-auto shadow-sm"
          title="Refresh analytics"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* Row 1: Trends & categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Conversation Volume Trend (14-Day)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Ingested conversations per UTC day</p>
          </div>

          <div className="h-72 w-full pt-2">
            {trends && trends.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends.trends}>
                  <defs>
                    <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="count"
                    name="Conversations"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorVol)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-slate-500">
                Not enough data yet — trends appear once conversations exist.
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Issue Category Distribution
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Inquiries classified by the NLP intent engine</p>
          </div>

          <div className="h-72 w-full pt-2">
            {data.most_frequently_reported_issues.length > 0 ||
            Object.keys(data.category_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={Object.entries(data.category_distribution).map(([category, count]) => ({
                    category,
                    count,
                  }))}
                  layout="vertical"
                  margin={{ left: 20 }}
                >
                  <XAxis type="number" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <YAxis
                    dataKey="category"
                    type="category"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    width={170}
                  />
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Bar dataKey="count" fill="#06b6d4" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-slate-500">
                Run analyses to populate category distribution.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: priority & resolution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Triage Priority Stratification
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Automated urgency weighting distribution</p>
          </div>

          <div className="h-64 w-full pt-2 flex items-center justify-center">
            {Object.keys(data.priority_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={toSeries(data.priority_distribution)}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="count"
                  >
                    {Object.entries(data.priority_distribution).map(([key], index) => (
                      <Cell key={`cell-${index}`} fill={PRIORITY_COLORS[key] || '#3b82f6'} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Legend formatter={(value) => <span className="text-xs font-mono text-slate-300">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs font-mono text-slate-500">No priority data yet.</div>
            )}
          </div>
        </div>

        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Sentiment & Resolution Status
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {data.unresolved_complaint_count} unresolved · {data.urgent_complaint_count} urgent
            </p>
          </div>

          <div className="h-64 w-full pt-2 flex items-center justify-center">
            {Object.keys(data.sentiment_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={toSeries(data.sentiment_distribution)}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="count"
                  >
                    {Object.entries(data.sentiment_distribution).map(([key], index) => (
                      <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[key] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomDarkTooltip />} />
                  <Legend formatter={(value) => <span className="text-xs font-mono text-slate-300">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs font-mono text-slate-500">No sentiment data yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Top issues */}
      {data.most_frequently_reported_issues.length > 0 && (
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="pb-2 border-b border-surface-border">
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Most Frequently Reported Issues
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Top recurring issue summaries by frequency</p>
          </div>
          <div className="space-y-2.5 pt-1">
            {data.most_frequently_reported_issues.slice(0, 8).map((issue, idx) => {
              const maxVal = data.most_frequently_reported_issues[0]?.count || 1;
              const pct = Math.round((issue.count / maxVal) * 100);
              return (
                <div key={idx} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium truncate max-w-lg" title={issue.issue}>
                      {issue.issue}
                    </span>
                    <span className="text-slate-500 font-mono text-[11px]">{issue.count} reports</span>
                  </div>
                  <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-brand-cyan to-blue-500 h-full rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
