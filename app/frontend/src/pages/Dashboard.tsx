import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  ShieldAlert,
  Clock,
  ChevronRight,
  Flame,
  RefreshCw,
} from 'lucide-react';
import { getDashboardOverview } from '../services/analyticsApi';
import { getConversations } from '../services/conversationApi';
import { getThreats } from '../services/securityApi';
import { DashboardOverview, Conversation, Threat } from '../types/conversation';
import { RiskBadge } from '../components/common/RiskBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { KpiCard } from '../components/dashboard/KpiCard';
import { CardSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorState } from '../components/common/ErrorState';

const CHANNEL_LABELS: Record<string, string> = {
  EMAIL: 'Email',
  CHAT: 'Chat',
  TICKET: 'Ticket',
  SOCIAL_MEDIA: 'Social',
  OTHER: 'Other',
};

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [recentConversations, setRecentConversations] = useState<Conversation[]>([]);
  const [recentThreats, setRecentThreats] = useState<Threat[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [overview, convRes, threatRes] = await Promise.all([
        getDashboardOverview(),
        getConversations({ page: 1, page_size: 4 }),
        getThreats({ page: 1, page_size: 4 }),
      ]);
      setData(overview);
      setRecentConversations(convRes.items);
      setRecentThreats(threatRes.items);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve dashboard data.');
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
        <div className="h-7 w-56 bg-slate-800 rounded-xl animate-pulse" />
        <CardSkeleton count={4} />
      </div>
    );
  }

  if (error || !data) {
    return <ErrorState title="Dashboard telemetry unavailable" message={error || ''} onRetry={loadData} />;
  }

  const totalAnalyzed = Object.values(data.sentiment_distribution).reduce((a, b) => a + b, 0);
  const pct = (n: number) => (totalAnalyzed > 0 ? Math.round((n / totalAnalyzed) * 100) : 0);
  const topCategories = Object.entries(data.category_distribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const maxCategory = topCategories.length > 0 ? topCategories[0][1] : 1;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Platform Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-surface-card border border-surface-border p-5 sm:p-6 shadow-card">
        <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-brand-cyan via-indigo-500 to-rose-500 opacity-60" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
              </span>
              <span className="text-[10px] font-mono uppercase font-bold tracking-widest text-emerald-400">
                LIVE INTELLIGENCE GRID
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-sans">
              Cybersecurity & Support Operations
            </h1>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Unified intelligence grid fusing multi-channel customer inquiries, NLP sentiment extraction, and automated cyber threat detection.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={loadData}
              className="px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border text-xs font-mono font-semibold transition-all flex items-center gap-2 shadow-sm"
              title="Refresh dashboard telemetry"
            >
              <RefreshCw size={14} className="text-brand-cyan" />
              <span>REFRESH DATA</span>
            </button>

            <button
              onClick={() => navigate('/threats')}
              className="px-3.5 py-2 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/35 text-xs font-mono font-semibold transition-all flex items-center gap-2 shadow-glow-rose/20"
            >
              <ShieldAlert size={15} />
              <span>THREAT RADAR</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Omnichannel Inbound"
          value={data.total_conversations}
          icon={MessageSquare}
          trend={{ value: `${data.open_conversations} open`, isPositive: true }}
          subtext="Processed by NLP triage"
          variant="default"
        />
        <KpiCard
          label="Unresolved Queue"
          value={data.unresolved_conversations}
          icon={Clock}
          trend={{ value: `${data.urgent_conversations} urgent`, isPositive: false }}
          subtext="Awaiting resolution"
          variant="warning"
        />
        <KpiCard
          label="Threats Detected"
          value={data.threats_detected}
          icon={ShieldAlert}
          trend={{ value: `${data.in_progress_conversations} in progress`, isPositive: false }}
          subtext="Security intelligence engine"
          variant="danger"
        />
        <KpiCard
          label="Critical Threats"
          value={data.critical_threats}
          icon={Flame}
          trend={{ value: 'Requires immediate action', isPositive: false }}
          subtext="High urgency escalations"
          variant="info"
        />
      </div>

      {/* Main Grid: Recent conversations vs threat watchlist */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Recent conversations */}
        <div className="lg:col-span-7 rounded-2xl border border-surface-border bg-surface-card p-5 sm:p-6 space-y-4 shadow-card">
          <div className="flex items-center justify-between pb-3.5 border-b border-surface-border">
            <div>
              <h2 className="text-sm font-bold text-slate-100 tracking-tight font-sans flex items-center gap-2">
                <MessageSquare size={16} className="text-brand-cyan" />
                <span>Inbound Telemetry Stream</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Latest tickets ingested and triaged</p>
            </div>
            <button
              onClick={() => navigate('/conversations')}
              className="text-xs font-mono text-brand-cyan hover:text-cyan-300 font-semibold flex items-center gap-1 transition-colors px-2.5 py-1 rounded-lg bg-surface-elevated border border-surface-border"
            >
              <span>View all tickets</span>
              <ChevronRight size={13} />
            </button>
          </div>

          <div className="divide-y divide-surface-border">
            {recentConversations.length === 0 && (
              <p className="py-6 text-center text-xs font-mono text-slate-500">
                No conversations yet. Create one to see live intelligence.
              </p>
            )}
            {recentConversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => navigate(`/conversations/${conv.id}`)}
                className="py-3.5 first:pt-1 last:pb-1 flex items-start justify-between gap-4 cursor-pointer group hover:bg-surface-elevated/60 -mx-2 px-3 rounded-xl transition-all"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs text-slate-200 group-hover:text-brand-cyan transition-colors">
                      {conv.customer_name || 'Unknown Customer'}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-elevated text-slate-400 border border-surface-border uppercase">
                      {CHANNEL_LABELS[conv.channel] || conv.channel}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">• {timeAgo(conv.updated_at)}</span>
                  </div>
                  <p className="text-xs text-slate-400 truncate max-w-md">
                    {conv.subject || conv.conversation_reference}
                  </p>
                  <div className="flex items-center gap-2 pt-0.5">
                    <StatusBadge status={conv.status} />
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-2 pt-1">
                  <span className="font-mono text-[10px] text-slate-500">{conv.conversation_reference}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Threat watchlist */}
        <div className="lg:col-span-5 rounded-2xl border border-surface-border bg-surface-card p-5 sm:p-6 space-y-4 shadow-card">
          <div className="flex items-center justify-between pb-3.5 border-b border-surface-border">
            <div>
              <h2 className="text-sm font-bold text-slate-100 tracking-tight font-sans flex items-center gap-2">
                <ShieldAlert size={16} className="text-rose-400" />
                <span>Threat Watchlist</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Most recent persisted threat records</p>
            </div>
            <button
              onClick={() => navigate('/threats')}
              className="text-xs font-mono text-rose-300 hover:text-white font-semibold flex items-center gap-1 transition-colors px-2.5 py-1 rounded-lg bg-rose-500/15 border border-rose-500/30"
            >
              <span>Directory</span>
              <ChevronRight size={13} />
            </button>
          </div>

          <div className="space-y-3">
            {recentThreats.length === 0 && (
              <p className="py-6 text-center text-xs font-mono text-slate-500">
                No threat records persisted yet.
              </p>
            )}
            {recentThreats.map((threat) => (
              <div
                key={threat.id}
                onClick={() => navigate(`/threats/${threat.id}`)}
                className="p-3.5 rounded-xl border border-surface-border bg-surface-elevated/60 hover:bg-surface-elevated hover:border-slate-700 cursor-pointer transition-all space-y-2 group shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-rose-300 group-hover:text-rose-200 transition-colors">
                    {threat.threat_type || 'UNCATEGORIZED'}
                  </span>
                  <RiskBadge level={threat.risk_level || 'LOW'} size="sm" />
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span className="truncate text-slate-400">{timeAgo(threat.created_at)}</span>
                  <span className="uppercase text-slate-400">
                    {threat.social_engineering_detected ? 'Social Eng.' : 'Technical'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dual analytical panels: sentiment + categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border">
            <div>
              <h2 className="text-sm font-bold text-slate-100 tracking-tight font-sans">
                Customer Sentiment Breakdown
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">NLP sentiment distribution across analyzed tickets</p>
            </div>
            <button
              onClick={() => navigate('/insights/customer')}
              className="text-xs font-mono text-brand-cyan hover:text-cyan-300 font-medium flex items-center gap-1 transition-colors px-2 py-1 rounded-lg bg-surface-elevated border border-surface-border"
            >
              <span>Trends</span>
              <ChevronRight size={12} />
            </button>
          </div>

          <div className="space-y-4 pt-1">
            {(['POSITIVE', 'NEUTRAL', 'NEGATIVE'] as const).map((label) => {
              const value = data.sentiment_distribution[label] || 0;
              const styles =
                label === 'POSITIVE'
                  ? { text: 'text-emerald-400', bar: 'bg-emerald-500' }
                  : label === 'NEUTRAL'
                  ? { text: 'text-slate-300', bar: 'bg-slate-500' }
                  : { text: 'text-rose-400', bar: 'bg-rose-500' };
              const name =
                label === 'POSITIVE' ? 'Positive' : label === 'NEUTRAL' ? 'Neutral' : 'Negative';
              return (
                <div key={label}>
                  <div className="flex justify-between text-xs mb-1.5 font-mono">
                    <span className={`${styles.text} font-semibold`}>{name}</span>
                    <span className="text-slate-300 font-bold">{pct(value)}%</span>
                  </div>
                  <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden">
                    <div className={`${styles.bar} h-full rounded-full`} style={{ width: `${pct(value)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-surface-card border border-surface-border rounded-2xl p-5 sm:p-6 space-y-4 shadow-card">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border">
            <div>
              <h2 className="text-sm font-bold text-slate-100 tracking-tight font-sans">
                Top Issue Categories
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Ticket volume grouped by canonical category</p>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-elevated text-brand-cyan border border-surface-border font-bold">
              {data.total_conversations.toLocaleString()} TOTAL
            </span>
          </div>

          <div className="space-y-3.5 pt-1">
            {topCategories.length === 0 && (
              <p className="py-6 text-center text-xs font-mono text-slate-500">
                Run an analysis to populate category distribution.
              </p>
            )}
            {topCategories.map(([category, count]) => {
              const pct = Math.round((count / maxCategory) * 100);
              return (
                <div key={category} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium">{category}</span>
                    <span className="text-slate-500 font-mono text-[11px]">{count.toLocaleString()} cases</span>
                  </div>
                  <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-brand-cyan to-blue-500 h-full rounded-full shadow-glow-cyan/50"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
