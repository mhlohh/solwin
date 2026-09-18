import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getThreats } from "../services/securityApi";
import { Threat, ThreatFilterParams } from "../types/conversation";
import { DataTable, Column } from "../components/common/DataTable";
import { RiskBadge } from "../components/common/RiskBadge";
import { SearchBar } from "../components/common/SearchBar";
import { RefreshCw } from "lucide-react";

const RISK_OPTIONS = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

const RISK_LABELS: Record<string, string> = {
  "": "All risk levels",
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export const Threats: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [threats, setThreats] = useState<Threat[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [riskLevel, setRiskLevel] = useState(searchParams.get("risk") || "");

  const load = async () => {
    setIsLoading(true);
    try {
      const params: ThreatFilterParams = {
        risk_level: (riskLevel as any) || undefined,
        search: search || undefined,
        page,
        page_size: 10,
      };
      const res = await getThreats(params);
      setThreats(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch {
      setThreats([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, riskLevel, page]);

  const columns: Column<Threat>[] = [
    {
      key: "threat_type",
      header: "Classification",
      render: (item) => (
        <span className="text-sm font-medium text-text-1">
          {item.threat_type === "NONE" || !item.threat_type
            ? "No threat classified"
            : item.threat_type.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      key: "risk_level",
      header: "Risk",
      render: (item) => <RiskBadge level={item.risk_level || "LOW"} size="sm" />,
    },
    {
      key: "social_engineering_detected",
      header: "Social engineering",
      render: (item) => (
        <span
          className={`text-sm ${
            item.social_engineering_detected ? "font-medium text-warn" : "text-text-3"
          }`}
        >
          {item.social_engineering_detected ? "Detected" : "—"}
        </span>
      ),
    },
    {
      key: "techniques",
      header: "Tactics",
      render: (item) => (
        <span
          className="block max-w-[220px] truncate text-sm text-text-2"
          title={(item.techniques || []).join(", ")}
        >
          {item.techniques && item.techniques.length > 0
            ? item.techniques
                .slice(0, 2)
                .map((t) => t.toLowerCase().replace(/_/g, " "))
                .join(", ") + (item.techniques.length > 2 ? ` +${item.techniques.length - 2}` : "")
            : "—"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Detected",
      render: (item) => (
        <span className="whitespace-nowrap text-sm text-text-2">
          {formatTime(item.created_at)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Threats</h1>
          <p className="text-sm text-text-2">
            {total} record{total === 1 ? "" : "s"} from the security engine
          </p>
        </div>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-1.5 text-sm font-medium hover:bg-elevated"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchBar
          placeholder="Search threat records…"
          value={search}
          onChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          className="sm:max-w-sm sm:flex-1"
        />
        <select
          value={riskLevel}
          onChange={(e) => {
            setRiskLevel(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm text-text-1 hover:border-line-strong focus:border-accent focus:outline-none"
        >
          {RISK_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {RISK_LABELS[opt]}
            </option>
          ))}
        </select>
      </div>

      <DataTable
        columns={columns}
        data={threats}
        isLoading={isLoading}
        emptyTitle="No threat records"
        emptyDescription="Records appear here after the security engine analyzes conversations."
        currentPage={page}
        totalPages={totalPages}
        totalItems={total}
        onPageChange={(p) => setPage(p)}
        onRowClick={(item) => navigate(`/threats/${item.id}`)}
      />
    </div>
  );
};
