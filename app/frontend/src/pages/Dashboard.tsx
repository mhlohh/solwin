import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { getDashboardOverview } from "../services/analyticsApi";
import { getConversations } from "../services/conversationApi";
import { getThreats } from "../services/securityApi";
import {
  DashboardOverview,
  Conversation,
  IngestedFeedbackStats,
  Threat,
} from "../types/conversation";
import { RiskBadge } from "../components/common/RiskBadge";
import { StatusBadge } from "../components/common/StatusBadge";
import { KpiCard } from "../components/dashboard/KpiCard";
import { CardSkeleton, TableSkeleton } from "../components/common/LoadingSkeleton";
import { ErrorState } from "../components/common/ErrorState";

const CHANNEL_LABELS: Record<string, string> = {
  EMAIL: "Email",
  CHAT: "Chat",
  TICKET: "Ticket",
  SOCIAL_MEDIA: "Social",
  OTHER: "Other",
};

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

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

const PRIORITY_TIER_META = [
  { key: "CRITICAL", label: "Critical", bar: "bg-danger" },
  { key: "HIGH", label: "High", bar: "bg-warn" },
  { key: "MEDIUM", label: "Medium", bar: "bg-accent" },
  { key: "LOW", label: "Low", bar: "bg-line-strong" },
];

const IngestedStatRow: React.FC<{
  label: string;
  value: string;
  tone?: "neutral" | "warn" | "danger";
}> = ({ label, value, tone = "neutral" }) => {
  const color =
    tone === "danger"
      ? "text-danger"
      : tone === "warn"
      ? "text-warn"
      : "text-text-1";
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="text-sm text-text-2">{label}</span>
      <span className={`text-lg font-semibold tabular-nums ${color}`}>
        {value}
      </span>
    </div>
  );
};

const IngestedFeedbackPanel: React.FC<{ stats: IngestedFeedbackStats }> = ({
  stats,
}) => {
  const total = stats.total_records || 1;
  const critical = stats.priority_counts["CRITICAL"] || 0;
  const high = stats.priority_counts["HIGH"] || 0;
  const topIntents = stats.top_intents.slice(0, 5);
  const maxIntent = topIntents[0]?.count || 1;

  return (
    <div className="surface-card">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold">Ingested feedback dataset</h2>
        <Link
          to="/inbox"
          className="text-sm font-medium text-accent hover:underline"
        >
          Open inbox
        </Link>
      </div>
      <div className="grid gap-6 px-4 py-4 lg:grid-cols-3">
        <div className="space-y-3">
          <IngestedStatRow
            label="Records ingested"
            value={stats.total_records.toLocaleString()}
          />
          <IngestedStatRow
            label="Flagged phishing"
            value={stats.phishing_flagged.toLocaleString()}
            tone="danger"
          />
          <IngestedStatRow
            label="Needs attention (critical + high)"
            value={(critical + high).toLocaleString()}
            tone="warn"
          />
        </div>
        <div>
          <p className="section-label mb-2.5">Priority tiers</p>
          <div className="space-y-2.5">
            {PRIORITY_TIER_META.map(({ key, label, bar }) => {
              const count = stats.priority_counts[key] || 0;
              const width = Math.round((count / total) * 100);
              return (
                <div key={key}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="text-text-2">{label}</span>
                    <span className="font-medium tabular-nums text-text-1">
                      {count.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-inset">
                    <div
                      className={`h-full rounded-full ${bar}`}
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div>
          <p className="section-label mb-2.5">Top intents</p>
          <div className="space-y-2.5">
            {topIntents.length === 0 && (
              <p className="py-4 text-center text-sm text-text-3">
                No intent data available.
              </p>
            )}
            {topIntents.map(({ issue, count }) => {
              const width = Math.round((count / maxIntent) * 100);
              return (
                <div key={issue}>
                  <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                    <span className="truncate text-text-2">{issue}</span>
                    <span className="font-medium tabular-nums text-text-1">
                      {count.toLocaleString()}
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
      </div>
    </div>
  );
};

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [recent, setRecent] = useState<Conversation[]>([]);
  const [threats, setThreats] = useState<Threat[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [overview, convRes, threatRes] = await Promise.all([
        getDashboardOverview(),
        getConversations({ page: 1, page_size: 6 }),
        getThreats({ page: 1, page_size: 5 }),
      ]);
      setData(overview);
      setRecent(convRes.items);
      setThreats(threatRes.items);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <CardSkeleton count={4} />
        <TableSkeleton rows={6} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Dashboard unavailable"
        message={error || ""}
        onRetry={loadData}
      />
    );
  }

  const totalAnalyzed = Object.values(data.sentiment_distribution).reduce(
    (a, b) => a + b,
    0
  );
  const pct = (n: number) =>
    totalAnalyzed > 0 ? Math.round((n / totalAnalyzed) * 100) : 0;
  const topCategories = Object.entries(data.category_distribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const maxCategory = topCategories.length > 0 ? topCategories[0][1] : 1;

  return (
    <div className="space-y-6 pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-text-2">
            Support queue health and security signals at a glance.
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

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <KpiCard
          label="Conversations"
          value={data.total_conversations}
          detail={`${data.open_conversations} open`}
        />
        <KpiCard
          label="Unresolved"
          value={data.unresolved_conversations}
          detail="Awaiting resolution"
          tone="warn"
        />
        <KpiCard
          label="Urgent"
          value={data.urgent_conversations}
          detail="High priority"
          tone="warn"
        />
        <KpiCard
          label="In progress"
          value={data.in_progress_conversations}
          detail="Being worked on"
        />
        <KpiCard
          label="Threats detected"
          value={data.threats_detected}
          detail={`${data.critical_threats} critical`}
          tone={data.threats_detected > 0 ? "danger" : "neutral"}
        />
      </div>

      {data.ingested_feedback && (
        <IngestedFeedbackPanel stats={data.ingested_feedback} />
      )}

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-3">
        {/* Recent conversations */}
        <div className="surface-card lg:col-span-2">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">Latest conversations</h2>
            <Link
              to="/conversations"
              className="text-sm font-medium text-accent hover:underline"
            >
              View all
            </Link>
          </div>
          <div>
            {recent.length === 0 && (
              <p className="px-4 py-10 text-center text-sm text-text-3">
                No conversations yet.
              </p>
            )}
            {recent.map((conv) => (
              <Link
                key={conv.id}
                to={`/conversations/${conv.id}`}
                className="flex items-center justify-between gap-4 border-b border-line px-4 py-3 last:border-b-0 hover:bg-elevated"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-text-1">
                      {conv.subject || "(no subject)"}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1.5 text-xs text-text-3">
                    <span>{conv.customer_name || "Unknown"}</span>
                    <span>·</span>
                    <span>{CHANNEL_LABELS[conv.channel] || conv.channel}</span>
                    <span>·</span>
                    <span>{conv.conversation_reference}</span>
                    <span>·</span>
                    <span>{timeAgo(conv.updated_at)}</span>
                  </div>
                </div>
                <StatusBadge status={conv.status} />
              </Link>
            ))}
          </div>
        </div>

        {/* Threats */}
        <div className="surface-card">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">Recent threats</h2>
            <Link
              to="/threats"
              className="text-sm font-medium text-accent hover:underline"
            >
              View all
            </Link>
          </div>
          <div>
            {threats.length === 0 && (
              <p className="px-4 py-10 text-center text-sm text-text-3">
                No threat records yet.
              </p>
            )}
            {threats.map((threat) => (
              <Link
                key={threat.id}
                to={`/threats/${threat.id}`}
                className="block border-b border-line px-4 py-3 last:border-b-0 hover:bg-elevated"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-text-1">
                    {threat.threat_type === "NONE" || !threat.threat_type
                      ? "No threat classified"
                      : threat.threat_type}
                  </span>
                  <RiskBadge level={threat.risk_level || "LOW"} size="sm" />
                </div>
                <div className="mt-0.5 text-xs text-text-3">
                  {timeAgo(threat.created_at)}
                  {threat.social_engineering_detected && " · social engineering"}
                  {threat.techniques && threat.techniques.length > 0 && (
                    <> · {threat.techniques[0].toLowerCase().replace(/_/g, " ")}</>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
        {/* Sentiment */}
        <div className="surface-card">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">Customer sentiment</h2>
            <Link
              to="/insights/customer"
              className="text-sm font-medium text-accent hover:underline"
            >
              Insights
            </Link>
          </div>
          <div className="space-y-3.5 px-4 py-4">
            {(["POSITIVE", "NEUTRAL", "NEGATIVE"] as const).map((label) => {
              const value = data.sentiment_distribution[label] || 0;
              const bar =
                label === "POSITIVE"
                  ? "bg-ok"
                  : label === "NEGATIVE"
                  ? "bg-danger"
                  : "bg-line-strong";
              const name =
                label === "POSITIVE"
                  ? "Positive"
                  : label === "NEUTRAL"
                  ? "Neutral"
                  : "Negative";
              return (
                <div key={label}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-text-2">{name}</span>
                    <span className="font-medium tabular-nums text-text-1">
                      {pct(value)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-inset">
                    <div
                      className={`h-full rounded-full ${bar}`}
                      style={{ width: `${pct(value)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Categories */}
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">Top issue categories</h2>
          </div>
          <div className="space-y-3 px-4 py-4">
            {topCategories.length === 0 && (
              <p className="py-6 text-center text-sm text-text-3">
                Run an analysis to populate categories.
              </p>
            )}
            {topCategories.map(([category, count]) => {
              const width = Math.round((count / maxCategory) * 100);
              return (
                <div key={category}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="text-text-2">
                      {CATEGORY_LABELS[category] || category}
                    </span>
                    <span className="font-medium tabular-nums text-text-1">
                      {count}
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
      </div>
    </div>
  );
};
