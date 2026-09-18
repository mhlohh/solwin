import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getThreats } from '../services/securityApi';
import { Threat, ThreatFilterParams } from '../types/conversation';
import { DataTable, Column } from '../components/common/DataTable';
import { RiskBadge } from '../components/common/RiskBadge';
import { SearchBar } from '../components/common/SearchBar';
import { ShieldAlert, ArrowRight, Terminal, RefreshCw } from 'lucide-react';

const RISK_OPTIONS = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString();
}

export const Threats: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [threats, setThreats] = useState<Threat[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [riskLevel, setRiskLevel] = useState(searchParams.get('risk') || '');

  const loadThreats = async () => {
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
    } catch (err: any) {
      setThreats([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadThreats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, riskLevel, page]);

  const columns: Column<Threat>[] = [
    {
      key: 'threat_type',
      header: 'Threat Classification',
      render: (item) => (
        <span className="font-mono text-xs font-bold text-rose-300 flex items-center gap-1.5">
          <Terminal size={12} className="text-slate-500" />
          {item.threat_type || 'UNCATEGORIZED'}
        </span>
      ),
    },
    {
      key: 'threat_detected',
      header: 'Confirmed',
      render: (item) => (
        <span
          className={`text-xs font-mono ${
            item.threat_detected ? 'text-rose-300 font-semibold' : 'text-slate-500'
          }`}
        >
          {item.threat_detected ? 'Yes' : 'No'}
        </span>
      ),
    },
    {
      key: 'social_engineering_detected',
      header: 'Social Eng.',
      render: (item) => (
        <span
          className={`text-xs font-mono ${
            item.social_engineering_detected ? 'text-amber-300 font-semibold' : 'text-slate-500'
          }`}
        >
          {item.social_engineering_detected ? 'Confirmed' : 'None'}
        </span>
      ),
    },
    {
      key: 'risk_level',
      header: 'Assessed Risk',
      render: (item) => <RiskBadge level={item.risk_level || 'LOW'} size="sm" />,
    },
    {
      key: 'techniques',
      header: 'Techniques',
      render: (item) => (
        <span className="text-xs text-slate-400 truncate block max-w-[220px]" title={(item.techniques || []).join(', ')}>
          {item.techniques && item.techniques.length > 0
            ? item.techniques.slice(0, 2).join(', ') + (item.techniques.length > 2 ? ` +${item.techniques.length - 2}` : '')
            : '—'}
        </span>
      ),
    },
    {
      key: 'conversation_id',
      header: 'Source Ticket',
      render: (item) => (
        <span className="text-[11px] font-mono text-slate-500">
          {item.conversation_id ? `${item.conversation_id.slice(0, 8)}...` : '—'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Timestamp',
      render: (item) => (
        <span className="text-[11px] font-mono text-slate-500">{formatTime(item.created_at)}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Forensics',
      render: (item) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/threats/${item.id}`);
          }}
          className="p-1.5 rounded-lg bg-surface-elevated hover:bg-slate-800 text-slate-300 hover:text-white border border-surface-border transition-colors"
          title="Inspect threat"
        >
          <ArrowRight size={13} />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2 font-sans">
            <ShieldAlert size={22} className="text-rose-400" />
            <span>Cyber Threat Directory</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Forensic index of persisted threat records: phishing lures, impersonation attacks, lookalike domains, and social engineering vectors.
          </p>
        </div>

        <button
          onClick={loadThreats}
          className="p-2.5 rounded-xl border border-surface-border bg-surface-card hover:bg-surface-elevated text-slate-400 hover:text-slate-100 transition-all self-start sm:self-auto shadow-sm"
          title="Refresh threat directory"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-3 shadow-card">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="flex-1 max-w-md">
            <SearchBar
              placeholder="Search by threat type or risk indicator..."
              value={search}
              onChange={(val) => {
                setSearch(val);
                setPage(1);
              }}
            />
          </div>

          <select
            value={riskLevel}
            onChange={(e) => {
              setRiskLevel(e.target.value);
              setPage(1);
            }}
            className="bg-surface-elevated border border-surface-border hover:border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-rose-500/50 cursor-pointer font-sans"
          >
            {RISK_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === '' ? 'Risk Level (All)' : `${opt} Risk`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Threats Table */}
      <DataTable
        columns={columns}
        data={threats}
        isLoading={isLoading}
        emptyTitle="No threat records in current scope"
        emptyDescription="No threats have been persisted by the security intelligence engine yet."
        currentPage={page}
        totalPages={totalPages}
        onPageChange={(p) => setPage(p)}
        onRowClick={(item) => navigate(`/threats/${item.id}`)}
      />
    </div>
  );
};
