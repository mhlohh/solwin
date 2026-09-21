import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getThreats } from "../services/securityApi";
import {
  listPhishingTickets,
  InboxTicket,
  getFacets,
  InboxFacets,
} from "../services/inboxApi";
import { Threat, ThreatFilterParams } from "../types/conversation";
import { DataTable, Column } from "../components/common/DataTable";
import { RiskBadge } from "../components/common/RiskBadge";
import { SearchBar } from "../components/common/SearchBar";
import { RefreshCw, ShieldAlert } from "lucide-react";

const RISK_OPTIONS = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

const RISK_LABELS: Record<string, string> = {
  "": "All risk levels",
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

function formatTime(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

type Source = "engine" | "dataset";

export const Threats: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [source, setSource] = useState<Source>(
    searchParams.get("source") === "dataset" ? "dataset" : "engine"
  );

  // Engine detections (Backend security engine)
  const [threats, setThreats] = useState<Threat[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Dataset phishing records (Data API)
  const [phishingRows, setPhishingRows] = useState<InboxTicket[]>([]);
  const [dTotal, setDTotal] = useState(0);
  const [dPage, setDPage] = useState(1);
  const [dTotalPages, setDTotalPages] = useState(1);
  const [facets, setFacets] = useState<InboxFacets | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [riskLevel, setRiskLevel] = useState(searchParams.get("risk") || "");

  useEffect(() => {
    getFacets()
      .then(setFacets)
      .catch(() => setFacets(null));
  }, []);

  const load = async () => {
    setIsLoading(true);
    try {
      if (source === "engine") {
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
      } else {
        const res = await listPhishingTickets({
          skip: (dPage - 1) * 10,
          limit: 10,
          search: search || undefined,
        });
        setPhishingRows(res.items);
        setDTotal(res.total);
        setDTotalPages(Math.max(1, Math.ceil(res.total / 10)));
      }
    } catch {
      if (source === "engine") {
        setThreats([]);
        setTotal(0);
      } else {
        setPhishingRows([]);
        setDTotal(0);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, riskLevel, page, dPage, source]);

  const switchSource = (next: Source) => {
    setSource(next);
    setPage(1);
    setDPage(1);
  };

  const engineColumns: Column<Threat>[] = [
    {
      key: "threat_type",
      header: "Classification",
      render: (item) => (
        <span className="text-sm font-medium text-text-1">
          {item.threat_type === "NONE" || !item.threat_type
            ? "Clean scan — no security signals"
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

  const datasetColumns: Column<InboxTicket>[] = [
    {
      key: "subject",
      header: "Message",
      render: (item) => (
        <div className="max-w-[380px]">
          <div className="truncate text-sm font-medium text-text-1">
            {item.subject || "(no subject)"}
          </div>
          <div className="truncate text-xs text-text-3" title={item.message}>
            {item.message}
          </div>
        </div>
      ),
    },
    {
      key: "intent",
      header: "Intent",
      render: (item) => (
        <span className="text-sm text-text-2">{item.intent || "—"}</span>
      ),
    },
    {
      key: "technique",
      header: "Technique",
      render: (item) => (
        <span
          className="block max-w-[200px] truncate text-sm text-warn"
          title={item.technique || ""}
        >
          {item.technique || "—"}
        </span>
      ),
    },
    {
      key: "sender",
      header: "Sender",
      render: (item) => (
        <span className="block max-w-[180px] truncate text-sm text-text-2" title={item.sender}>
          {item.sender || "—"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Ingested",
      render: (item) => (
        <span className="whitespace-nowrap text-sm text-text-2">
          {formatTime(item.created_at)}
        </span>
      ),
    },
  ];

  const isEngine = source === "engine";

  return (
    <div className="space-y-4 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Threats</h1>
          <p className="text-sm text-text-2">
            {isEngine
              ? `${total} record${total === 1 ? "" : "s"} from the security engine`
              : `${(facets?.phishing ?? dTotal).toLocaleString()} phishing record${
                  (facets?.phishing ?? dTotal) === 1 ? "" : "s"
                } in the ingested dataset`}
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

      {/* Source toggle */}
      <div className="flex w-fit rounded-lg border border-line bg-card p-0.5">
        <button
          onClick={() => switchSource("engine")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            isEngine ? "bg-accent-weak text-accent" : "text-text-2 hover:text-text-1"
          }`}
        >
          Engine detections
          <span className="ml-1.5 text-xs text-text-3">{total.toLocaleString()}</span>
        </button>
        <button
          onClick={() => switchSource("dataset")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            !isEngine ? "bg-accent-weak text-accent" : "text-text-2 hover:text-text-1"
          }`}
        >
          <ShieldAlert size={14} className={!isEngine ? "text-danger" : "text-text-3"} />
          Dataset phishing
          <span className="ml-0.5 text-xs text-text-3">
            {(facets?.phishing ?? 0).toLocaleString()}
          </span>
        </button>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchBar
          placeholder={
            isEngine ? "Search threat records…" : "Search phishing messages…"
          }
          value={search}
          onChange={(val) => {
            setSearch(val);
            setPage(1);
            setDPage(1);
          }}
          className="sm:max-w-sm sm:flex-1"
        />
        {isEngine && (
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
        )}
      </div>

      <DataTable<Threat | InboxTicket>
        columns={(isEngine ? engineColumns : datasetColumns) as Column<Threat | InboxTicket>[]}
        data={(isEngine ? threats : phishingRows) as (Threat | InboxTicket)[]}
        isLoading={isLoading}
        emptyTitle={isEngine ? "No threat records" : "No phishing records match"}
        emptyDescription={
          isEngine
            ? "Records appear here after the security engine analyzes conversations."
            : "Try a different search term."
        }
        currentPage={isEngine ? page : dPage}
        totalPages={isEngine ? totalPages : dTotalPages}
        totalItems={isEngine ? total : dTotal}
        onPageChange={(p) => (isEngine ? setPage(p) : setDPage(p))}
        onRowClick={
          isEngine
            ? (item) => navigate(`/threats/${item.id}`)
            : (item) => navigate(`/inbox?ticket=${item.id}`)
        }
      />
    </div>
  );
};
