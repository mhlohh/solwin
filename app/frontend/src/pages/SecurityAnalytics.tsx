import React, { useState, useEffect } from "react";
import { getSecurityAnalytics, getSecurityTrends } from "../services/analyticsApi";
import {
  SecurityAnalytics as SecAnalyticsType,
  TrendResponse,
} from "../types/conversation";
import { ChartSkeleton } from "../components/common/LoadingSkeleton";
import { ErrorState } from "../components/common/ErrorState";
import { KpiCard } from "../components/dashboard/KpiCard";
import { RefreshCw } from "lucide-react";
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
} from "recharts";

const RISK_COLORS: Record<string, string> = {
  LOW: "#57a86b",
  MEDIUM: "#d29a44",
  HIGH: "#c47b18",
  CRITICAL: "#b42318",
};

function toSeries(dist: Record<string, number>) {
  return Object.entries(dist).map(([name, value]) => ({ name, value }));
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="surface-card">
      <div className="border-b border-line px-4 py-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-text-3">{subtitle}</p>}
      </div>
      <div className="px-2 py-4">{children}</div>
    </div>
  );
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
      setError(err.message || "Failed to fetch security analytics.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="surface-card px-4 py-3.5">
              <div className="h-3 w-24 animate-pulse rounded-md bg-inset" />
              <div className="mt-3 h-7 w-14 animate-pulse rounded-md bg-inset" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Security analytics unavailable"
        message={error || ""}
        onRetry={loadData}
      />
    );
  }

  const tooltipStyle = {
    backgroundColor: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 12,
    color: "var(--text-1)",
    boxShadow: "var(--shadow-2)",
  };

  const topTechniques = Object.entries(data.technique_frequency)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const maxTechnique = topTechniques.length > 0 ? topTechniques[0][1] : 1;

  return (
    <div className="space-y-5 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Security analytics</h1>
          <p className="text-sm text-text-2">
            Signals from the security engine across all analyzed conversations.
          </p>
        </div>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 text-sm font-medium hover:bg-elevated"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Evaluations" value={data.total_threats} />
        <KpiCard
          label="Threats confirmed"
          value={data.threats_detected}
          tone={data.threats_detected > 0 ? "danger" : "neutral"}
        />
        <KpiCard
          label="Suspicious URLs"
          value={data.suspicious_url_count}
          tone={data.suspicious_url_count > 0 ? "warn" : "neutral"}
        />
        <KpiCard
          label="Suspicious addresses"
          value={data.suspicious_email_count}
          tone={data.suspicious_email_count > 0 ? "warn" : "neutral"}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard title="Threats over time" subtitle="Confirmed threats per day, last 14 days">
          <div className="h-64">
            {trends && trends.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends.trends}>
                  <XAxis dataKey="date" tickMargin={8} />
                  <YAxis allowDecimals={false} width={28} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: "var(--border-strong)" }} />
                  <Area
                    type="monotone"
                    dataKey="count"
                    name="Threats"
                    stroke="var(--danger)"
                    strokeWidth={1.5}
                    fill="var(--danger-weak)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                Not enough data yet — run security analyses.
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard title="Risk distribution" subtitle="Across all evaluated records">
          <div className="h-64">
            {Object.keys(data.risk_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={toSeries(data.risk_distribution)}
                    cx="50%"
                    cy="50%"
                    innerRadius={52}
                    outerRadius={78}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {Object.entries(data.risk_distribution).map(([key], index) => (
                      <Cell key={index} fill={RISK_COLORS[key] || "#6f727a"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend
                    formatter={(value) => (
                      <span style={{ color: "var(--text-2)", fontSize: 12 }}>
                        {String(value).toLowerCase()} risk
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                No risk data yet.
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard title="Threat classifications" subtitle="Frequency by classified type">
          <div className="h-64">
            {Object.keys(data.threat_type_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={Object.entries(data.threat_type_distribution).map(
                    ([name, count]) => ({ name: name.replace(/_/g, " "), count })
                  )}
                  layout="vertical"
                  margin={{ left: 8, right: 16 }}
                >
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis dataKey="name" type="category" width={120} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--inset)" }} />
                  <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                No classifications recorded yet.
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard
          title="Social engineering tactics"
          subtitle="Detected manipulation techniques by frequency"
        >
          <div className="space-y-3 px-2 py-1">
            {topTechniques.length === 0 && (
              <p className="py-10 text-center text-sm text-text-3">
                No social engineering techniques detected yet.
              </p>
            )}
            {topTechniques.map(([technique, count]) => (
              <div key={technique}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-mono text-xs text-text-1">
                    {technique.replace(/_/g, " ")}
                  </span>
                  <span className="tabular-nums text-text-2">{count}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-inset">
                  <div
                    className="h-full rounded-full bg-warn"
                    style={{ width: `${Math.round((count / maxTechnique) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {data.recent_critical_threats.length > 0 && (
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold">Recent critical threats</h3>
          </div>
          <div>
            {data.recent_critical_threats.map((threat) => (
              <div
                key={threat.threat_id}
                className="flex items-center justify-between gap-4 border-b border-line px-4 py-3 last:border-b-0"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-text-1">
                    {threat.threat_type?.replace(/_/g, " ") || "Uncategorized"}
                  </div>
                  {threat.risk_reasons.length > 0 && (
                    <div className="mt-0.5 truncate text-xs text-text-2">
                      {threat.risk_reasons[0]}
                    </div>
                  )}
                </div>
                <span className="shrink-0 text-xs text-text-3">
                  {new Date(threat.created_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
