import React, { useState, useEffect } from "react";
import { getCustomerAnalytics, getCustomerTrends } from "../services/analyticsApi";
import { getDatasetStats, DatasetStats } from "../services/inboxApi";
import { CustomerAnalytics, TrendResponse } from "../types/conversation";
import { ChartSkeleton } from "../components/common/LoadingSkeleton";
import { ErrorState } from "../components/common/ErrorState";
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

const PRIORITY_COLORS: Record<string, string> = {
  LOW: "#9a9fa6",
  MEDIUM: "#d29a44",
  HIGH: "#c47b18",
  CRITICAL: "#b42318",
};

const SENTIMENT_COLORS: Record<string, string> = {
  POSITIVE: "#57a86b",
  NEUTRAL: "#9a9fa6",
  NEGATIVE: "#b42318",
};

const SERIES_COLORS = ["#3b6fd4", "#57a86b", "#d29a44", "#b45cd1", "#c47b18", "#6f727a", "#4f9dc4"];

const CATEGORY_LABELS: Record<string, string> = {
  ACCOUNT_ACCESS: "Account access",
  PAYMENT_BILLING: "Payment & billing",
  TECHNICAL_ISSUE: "Technical issue",
  SERVICE_REQUEST: "Service request",
  OTHER: "Other",
  PAYMENT_TRANSACTION_ISSUE: "Payment transaction",
  ACCOUNT_LOGIN_PROBLEM: "Login problem",
  PRODUCT_ISSUE: "Product issue",
  DELIVERY_SHIPPING_PROBLEM: "Delivery & shipping",
  REFUND_REQUEST: "Refund request",
  SUBSCRIPTION_ISSUE: "Subscription",
  TECHNICAL_PROBLEM: "Technical problem",
  SERVICE_QUALITY: "Service quality",
  BILLING_PROBLEM: "Billing problem",
  SECURITY_CONCERN: "Security concern",
};

function toSeries(dist: Record<string, number>) {
  return Object.entries(dist).map(([name, count]) => ({ name, count }));
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

export const CustomerInsights: React.FC = () => {
  const [data, setData] = useState<CustomerAnalytics | null>(null);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [dataset, setDataset] = useState<DatasetStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsRes, trendsRes, datasetRes] = await Promise.all([
        getCustomerAnalytics(),
        getCustomerTrends(14).catch(() => null),
        getDatasetStats().catch(() => null),
      ]);
      setData(analyticsRes);
      setTrends(trendsRes);
      setDataset(datasetRes);
    } catch (err: any) {
      setError(err.message || "Failed to fetch customer insights.");
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
        <ChartSkeleton />
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
        title="Insights unavailable"
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

  const channelEntries = dataset
    ? Object.entries(dataset.channel_counts).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <div className="space-y-5 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Customer insights</h1>
          <p className="text-sm text-text-2">
            {dataset
              ? <>
                  {dataset.total_records.toLocaleString()} records ingested ·{" "}
                  {data.total_conversations} AI-analyzed in the live queue
                </>
              : <>
                  {data.total_conversations} conversations analyzed ·{" "}
                  {data.unresolved_complaint_count} unresolved ·{" "}
                  {data.urgent_complaint_count} urgent
                </>}
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

      {/* Ingested dataset overview (Data API) */}
      {dataset && (
        <div className="surface-card">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold">Ingested feedback dataset</h3>
            <a
              href="/inbox"
              className="text-sm font-medium text-accent hover:underline"
            >
              Open inbox
            </a>
          </div>
          <div className="grid gap-6 px-4 py-4 lg:grid-cols-3">
            <div>
              <p className="section-label mb-2.5">Priority mix</p>
              <div className="space-y-2.5">
                {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((tier) => {
                  const count = dataset.priority_counts[tier] || 0;
                  const pct =
                    dataset.total_records > 0
                      ? Math.round((count / dataset.total_records) * 100)
                      : 0;
                  const bar =
                    tier === "CRITICAL"
                      ? "bg-danger"
                      : tier === "HIGH"
                      ? "bg-warn"
                      : tier === "MEDIUM"
                      ? "bg-accent"
                      : "bg-line-strong";
                  return (
                    <div key={tier}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="text-text-2">
                          {tier.charAt(0) + tier.slice(1).toLowerCase()}
                        </span>
                        <span className="font-medium tabular-nums text-text-1">
                          {count.toLocaleString()} · {pct}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-inset">
                        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="h-64">
              <p className="section-label mb-2.5">Feedback volume by intent</p>
              {dataset.top_intents.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={dataset.top_intents.map(({ issue, count }) => ({
                      issue,
                      count,
                    }))}
                    layout="vertical"
                    margin={{ left: 8, right: 16 }}
                  >
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis dataKey="issue" type="category" width={150} />
                    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--inset)" }} />
                    <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-text-3">
                  No intent data available.
                </div>
              )}
            </div>
            <div className="h-64">
              <p className="section-label mb-2.5">Channel mix</p>
              {channelEntries.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={channelEntries.slice(0, 7).map(([channel, count]) => ({
                      channel,
                      count,
                    }))}
                    layout="vertical"
                    margin={{ left: 8, right: 16 }}
                  >
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis dataKey="channel" type="category" width={120} />
                    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--inset)" }} />
                    <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-text-3">
                  No channel data available.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard
          title="Conversation volume"
          subtitle="Live support queue per day, last 14 days (6 AI-analyzed conversations)"
        >
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
                    name="Conversations"
                    stroke="var(--accent)"
                    strokeWidth={1.5}
                    fill="var(--accent-weak)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                Not enough data yet.
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard
          title="Issue categories"
          subtitle="Live support queue — Gemini-classified category per conversation"
        >
          <div className="h-64">
            {Object.keys(data.category_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={Object.entries(data.category_distribution).map(
                    ([category, count]) => ({
                      category: CATEGORY_LABELS[category] || category,
                      count,
                    })
                  )}
                  layout="vertical"
                  margin={{ left: 8, right: 16 }}
                >
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis dataKey="category" type="category" width={130} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--inset)" }} />
                  <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                Run analyses to populate categories.
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard
          title="Queue priority mix"
          subtitle="Live support queue — automated triage of AI-analyzed conversations"
        >
          <div className="h-56">
            {Object.keys(data.priority_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={toSeries(data.priority_distribution)}
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={2}
                    dataKey="count"
                  >
                    {Object.entries(data.priority_distribution).map(([key], index) => (
                      <Cell key={index} fill={PRIORITY_COLORS[key] || "#6f727a"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend
                    formatter={(value) => (
                      <span style={{ color: "var(--text-2)", fontSize: 12 }}>
                        {String(value).toLowerCase().replace(/_/g, " ")}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                No priority data yet.
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard
          title="Queue sentiment mix"
          subtitle="Live support queue — Gemini sentiment per analyzed conversation"
        >
          <div className="h-56">
            {Object.keys(data.sentiment_distribution).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={toSeries(data.sentiment_distribution)}
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={2}
                    dataKey="count"
                  >
                    {Object.entries(data.sentiment_distribution).map(([key], index) => (
                      <Cell key={index} fill={SENTIMENT_COLORS[key] || "#6f727a"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend
                    formatter={(value) => (
                      <span style={{ color: "var(--text-2)", fontSize: 12 }}>
                        {String(value).toLowerCase()}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-3">
                No sentiment data yet.
              </div>
            )}
          </div>
        </ChartCard>
      </div>

      {data.most_frequently_reported_issues.length > 0 && (
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold">Most reported issues</h3>
            <p className="mt-0.5 text-xs text-text-3">
              Live support queue — AI-extracted issue statements (one per conversation)
            </p>
          </div>
          <div className="space-y-3 px-4 py-4">
            {data.most_frequently_reported_issues.slice(0, 8).map((issue, idx) => {
              const maxVal = data.most_frequently_reported_issues[0]?.count || 1;
              const width = Math.round((issue.count / maxVal) * 100);
              return (
                <div key={idx}>
                  <div className="mb-1 flex items-center justify-between gap-4 text-sm">
                    <span className="truncate text-text-1" title={issue.issue}>
                      {issue.issue}
                    </span>
                    <span className="shrink-0 tabular-nums text-text-2">
                      {issue.count} report{issue.count === 1 ? "" : "s"}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-inset">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${width}%` }}
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
