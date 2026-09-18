import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getConversations } from '../services/conversationApi';
import {
  Conversation,
  ConversationFilterParams,
  ChannelType,
  ConversationStatusType,
} from '../types/conversation';
import { SearchBar } from '../components/common/SearchBar';
import { StatusBadge } from '../components/common/StatusBadge';
import { TableSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import {
  MessageSquare,
  Mail,
  ArrowRight,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';

const CHANNEL_OPTIONS: { value: ChannelType | ''; label: string }[] = [
  { value: '', label: 'Channel (All)' },
  { value: 'EMAIL', label: 'Email' },
  { value: 'CHAT', label: 'Chat' },
  { value: 'TICKET', label: 'Ticket' },
  { value: 'SOCIAL_MEDIA', label: 'Social Media' },
  { value: 'OTHER', label: 'Other' },
];

const STATUS_OPTIONS: { value: ConversationStatusType | ''; label: string }[] = [
  { value: '', label: 'Status (All)' },
  { value: 'OPEN', label: 'Open' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'RESOLVED', label: 'Resolved' },
  { value: 'CLOSED', label: 'Closed' },
];

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

export const Conversations: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [channel, setChannel] = useState<ChannelType | ''>(
    (searchParams.get('channel') as ChannelType) || ''
  );
  const [status, setStatus] = useState<ConversationStatusType | ''>(
    (searchParams.get('status') as ConversationStatusType) || ''
  );

  const loadConversations = async () => {
    setIsLoading(true);
    try {
      const params: ConversationFilterParams = {
        search: search || undefined,
        channel: channel || undefined,
        status: status || undefined,
        page,
        page_size: 10,
      };

      const res = await getConversations(params);
      setConversations(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
      if (res.items.length > 0 && !selectedConv) {
        setSelectedConv(res.items[0]);
      }
    } catch (err: any) {
      setConversations([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [search, channel, status, page]);

  const hasActiveFilters = channel || status || search;

  const resetFilters = () => {
    setChannel('');
    setStatus('');
    setSearch('');
    setPage(1);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2 font-sans">
            <MessageSquare size={22} className="text-brand-cyan" />
            <span>Conversations & Support Triage</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Multi-channel ticket stream triaged with automated sentiment detection and zero-trust security scanning.
          </p>
        </div>

        <button
          onClick={loadConversations}
          className="p-2.5 rounded-xl border border-surface-border bg-surface-card hover:bg-surface-elevated text-slate-400 hover:text-slate-100 transition-all self-start sm:self-auto shadow-sm"
          title="Refresh ticket queue"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-3 shadow-card">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="flex-1 max-w-md">
            <SearchBar
              placeholder="Search by customer name, reference, or subject..."
              value={search}
              onChange={(val) => {
                setSearch(val);
                setPage(1);
              }}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as ConversationStatusType | '');
                setPage(1);
              }}
              className="bg-surface-elevated border border-surface-border hover:border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-cyan/50 cursor-pointer font-sans"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <select
              value={channel}
              onChange={(e) => {
                setChannel(e.target.value as ChannelType | '');
                setPage(1);
              }}
              className="bg-surface-elevated border border-surface-border hover:border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-cyan/50 cursor-pointer font-sans"
            >
              {CHANNEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="px-3 py-2 rounded-xl text-xs font-mono text-brand-cyan hover:text-cyan-300 transition-colors"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left list */}
        <div className="lg:col-span-7 rounded-2xl border border-surface-border bg-surface-card p-5 space-y-4 shadow-card">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border">
            <span className="font-mono text-xs font-semibold uppercase text-slate-400">
              Active Queue ({total} Inquiries)
            </span>
            <span className="text-[11px] font-mono text-slate-500">Page {page} of {totalPages || 1}</span>
          </div>

          {isLoading ? (
            <TableSkeleton rows={5} />
          ) : conversations.length === 0 ? (
            <EmptyState
              title="No tickets match active filters"
              description="Try adjusting your search criteria or resetting filters to view inbound inquiries."
              action={{ label: 'Clear Filters', onClick: resetFilters }}
            />
          ) : (
            <div className="divide-y divide-surface-border">
              {conversations.map((conv) => {
                const isSelected = selectedConv?.id === conv.id;
                return (
                  <div
                    key={conv.id}
                    onClick={() => setSelectedConv(conv)}
                    className={`py-3.5 px-3 rounded-xl cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-surface-elevated border-l-2 border-l-brand-cyan shadow-sm'
                        : 'hover:bg-surface-elevated/60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1.5 min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-slate-200">
                            {conv.customer_name || 'Unknown Customer'}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">• {conv.conversation_reference}</span>
                          <span className="text-[10px] font-mono text-slate-500">• {timeAgo(conv.updated_at)}</span>
                        </div>

                        <p className="text-xs text-slate-300 font-medium truncate">
                          {conv.subject || '(no subject)'}
                        </p>

                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-elevated text-slate-400 border border-surface-border uppercase">
                            {conv.channel}
                          </span>
                        </div>
                      </div>

                      <div className="shrink-0 pt-0.5">
                        <StatusBadge status={conv.status} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pt-3 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
              <span className="font-mono text-[11px]">
                Showing {conversations.length} of {total}
              </span>
              <div className="flex gap-1.5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 rounded-lg border border-surface-border bg-surface-elevated text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-colors"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 rounded-lg border border-surface-border bg-surface-elevated text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right preview */}
        <div className="lg:col-span-5 rounded-2xl border border-surface-border bg-surface-card p-5 sm:p-6 space-y-5 shadow-card sticky top-24">
          {selectedConv ? (
            <>
              <div className="flex items-start justify-between gap-3 pb-3.5 border-b border-surface-border">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-brand-cyan font-bold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/30">
                      {selectedConv.conversation_reference}
                    </span>
                    <StatusBadge status={selectedConv.status} />
                  </div>
                  <h2 className="text-base font-bold text-white mt-1.5 font-sans">
                    {selectedConv.customer_name || 'Unknown Customer'}
                  </h2>
                  {selectedConv.customer_email && (
                    <span className="text-xs font-mono text-slate-400">{selectedConv.customer_email}</span>
                  )}
                </div>

                <button
                  onClick={() => navigate(`/conversations/${selectedConv.id}`)}
                  className="px-3 py-1.5 rounded-xl bg-brand-cyan hover:bg-cyan-400 text-slate-950 text-xs font-mono font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 shadow-glow-cyan/30"
                >
                  <span>Open Ticket</span>
                  <ExternalLink size={12} />
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3.5 rounded-xl bg-surface-elevated/80 border border-surface-border space-y-1.5">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-semibold block">
                    Subject
                  </span>
                  <p className="text-slate-200 leading-relaxed">
                    {selectedConv.subject || '(no subject)'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-3 rounded-xl bg-surface-elevated/60 border border-surface-border">
                    <span className="text-[10px] font-mono text-slate-500 block mb-1">Channel</span>
                    <span className="font-mono uppercase text-slate-200">{selectedConv.channel}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-elevated/60 border border-surface-border">
                    <span className="text-[10px] font-mono text-slate-500 block mb-1">Created</span>
                    <span className="font-mono text-slate-200">{timeAgo(selectedConv.created_at)}</span>
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => navigate(`/conversations/${selectedConv.id}`)}
                  className="w-full py-2.5 rounded-xl bg-surface-elevated hover:bg-slate-800 border border-surface-border text-slate-200 hover:text-white text-xs font-mono font-semibold flex items-center justify-center gap-2 transition-all shadow-sm"
                >
                  <Mail size={14} className="text-brand-cyan" />
                  <span>Inspect Full Communication Timeline</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-slate-500 text-xs font-mono">
              Select a conversation to preview details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
