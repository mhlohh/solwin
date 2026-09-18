import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Inbox as InboxIcon,
  MailOpen,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import {
  getFacets,
  getTicket,
  listTickets,
  getApiErrorMessage,
  InboxFacets,
  InboxTicket,
} from '../services/inboxApi';
import { LineSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorState } from '../components/common/ErrorState';

const PAGE_SIZE = 20;

const CHANNELS = ['All channels', 'Email', 'Chat', 'Call', 'Web Form'];

const PRIORITIES = ['All priorities', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const;

const PRIORITY_STYLES: Record<string, string> = {
  CRITICAL: 'text-danger border-danger-line bg-danger-weak',
  HIGH: 'text-warn border-warn-line bg-warn-weak',
  MEDIUM: 'text-accent border-accent-line bg-accent-weak',
  LOW: 'text-text-2 border-line bg-elevated',
};

function PriorityChip({ tier }: { tier: string }) {
  const cls = PRIORITY_STYLES[tier] ?? PRIORITY_STYLES.LOW;
  return (
    <span className={`shrink-0 whitespace-nowrap rounded border px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      {tier}
    </span>
  );
}

function relativeTime(iso: string): string {
  const then = new Date(iso + 'Z').getTime();
  if (Number.isNaN(then)) return '—';
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso + 'Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function timeHM(iso: string): string {
  const d = new Date(iso + 'Z');
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function senderName(email: string): string {
  const at = email.indexOf('@');
  return at > 0 ? email.slice(0, at) : email || 'Unknown sender';
}

export const Inbox: React.FC = () => {
  const [tickets, setTickets] = useState<InboxTicket[]>([]);
  const [total, setTotal] = useState(0);
  const [facets, setFacets] = useState<InboxFacets | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState<'all' | 'phishing'>('all');
  const [channel, setChannel] = useState('All channels');
  const [priority, setPriority] = useState('All priorities');
  const [intent, setIntent] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<InboxTicket | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const fetchPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = {
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      };
      if (tab === 'phishing') params.phishing = true;
      if (channel !== 'All channels') params.channel = channel;
      if (priority !== 'All priorities') params.priority = priority;
      if (intent) params.intent = intent;
      if (search) params.search = search;
      const data = await listTickets(params);
      setTickets(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Could not load the feedback inbox.'));
    } finally {
      setLoading(false);
    }
  }, [page, tab, channel, priority, intent, search]);

  useEffect(() => {
    fetchPage();
  }, [fetchPage]);

  useEffect(() => {
    getFacets()
      .then(setFacets)
      .catch(() => setFacets(null));
  }, []);

  // NOTE: dataset channel values vary ("Email", "email_chat"…) so channel
  // filtering is done client-side per page; server supports search/intent/phishing.
  const visibleTickets = useMemo(
    () =>
      channel === 'All channels'
        ? tickets
        : tickets.filter((t) => (t.channel || '').toLowerCase() === channel.toLowerCase()),
    [tickets, channel]
  );

  useEffect(() => {
    setSelectedId(null);
    setSelected(null);
  }, [page, tab, channel, priority, intent, search]);

  const openTicket = useCallback(async (id: number) => {
    setSelectedId(id);
    setSelectedLoading(true);
    try {
      setSelected(await getTicket(id));
    } catch {
      setSelected(null);
    } finally {
      setSelectedLoading(false);
    }
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, total);
  const shown = visibleTickets.length;

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col">
      {/* Toolbar */}
      <div className="border-b border-line px-4 py-3 lg:px-6">
        <div className="flex flex-wrap items-center gap-2">
          {/* Tabs */}
          <div className="mr-1 flex rounded-lg border border-line bg-card p-0.5">
            <button
              onClick={() => { setTab('all'); setPage(1); }}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === 'all' ? 'bg-accent-weak text-accent' : 'text-text-2 hover:text-text-1'
              }`}
            >
              All
              {facets && (
                <span className="ml-1.5 text-xs text-text-3">{facets.total.toLocaleString()}</span>
              )}
            </button>
            <button
              onClick={() => { setTab('phishing'); setPage(1); }}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === 'phishing' ? 'bg-accent-weak text-accent' : 'text-text-2 hover:text-text-1'
              }`}
            >
              <ShieldAlert size={14} className={tab === 'phishing' ? 'text-danger' : 'text-text-3'} />
              Phishing
              {facets && <span className="ml-0.5 text-xs text-text-3">{facets.phishing}</span>}
            </button>
          </div>

          {/* Search */}
          <form
            className="flex min-w-52 flex-1 items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setPage(1);
              setSearch(searchInput.trim());
            }}
          >
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-3" />
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search subject, message, or issue…"
                className="w-full rounded-lg border border-line bg-card py-2 pl-9 pr-3 text-sm text-text-1 placeholder:text-text-3 hover:border-line-strong focus:border-accent focus:outline-none"
              />
            </div>
            <button type="submit" className="inline-flex items-center rounded-lg border border-line bg-card px-3 py-1.5 text-sm font-medium hover:bg-elevated">Search</button>
          </form>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={15} className="text-text-3" aria-hidden />
            <select
              value={channel}
              onChange={(e) => { setChannel(e.target.value); setPage(1); }}
              className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm text-text-1 hover:border-line-strong focus:border-accent focus:outline-none"
              aria-label="Filter by channel"
            >
              {CHANNELS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select
              value={priority}
              onChange={(e) => { setPriority(e.target.value); setPage(1); }}
              className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm text-text-1 hover:border-line-strong focus:border-accent focus:outline-none"
              aria-label="Filter by priority"
            >
              {PRIORITIES.map((p) => {
                const count = p === 'All priorities' ? null : facets?.priority_counts?.[p];
                return (
                  <option key={p} value={p}>
                    {p === 'All priorities' ? p : `${p} (${count ?? 0})`}
                  </option>
                );
              })}
            </select>
            <select
              value={intent}
              onChange={(e) => { setIntent(e.target.value); setPage(1); }}
              className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm text-text-1 hover:border-line-strong focus:border-accent focus:outline-none"
              aria-label="Filter by intent"
            >
              <option value="">All intents</option>
              {(facets?.intents ?? []).map((i) => (
                <option key={i} value={i}>{i}</option>
              ))}
            </select>
            <button
              onClick={fetchPage}
              className="rounded-lg p-2 text-text-2 hover:bg-elevated hover:text-text-1"
              aria-label="Refresh"
              title="Refresh"
            >
              <RefreshCw size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* Count + pager header */}
      <div className="flex items-center justify-between border-b border-line px-4 py-2 text-xs text-text-2 lg:px-6">
        <span>
          {loading ? 'Loading…' : total === 0
            ? 'No messages'
            : `${start.toLocaleString()}–${end.toLocaleString()} of ${total.toLocaleString()}`}
          {search && <span> · for “{search}”</span>}
          {intent && <span> · {intent}</span>}
        </span>
        <div className="flex items-center gap-1">
          <span>Page {page} of {totalPages.toLocaleString()}</span>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md p-1.5 hover:bg-elevated disabled:opacity-40"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md p-1.5 hover:bg-elevated disabled:opacity-40"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Body */}
      {error ? (
        <div className="p-6">
          <ErrorState message={error} onRetry={fetchPage} />
        </div>
      ) : loading ? (
        <div className="space-y-2 p-4 lg:p-6">
          {Array.from({ length: 10 }).map((_, i) => (
            <LineSkeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : shown === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
          <InboxIcon size={36} className="text-text-3" />
          <div>
            <p className="font-medium text-text-1">Nothing here</p>
            <p className="mt-1 text-sm text-text-2">
              No messages match the current filters.
            </p>
          </div>
          <button
            onClick={() => { setTab('all'); setChannel('All channels'); setPriority('All priorities'); setIntent(''); setSearch(''); setSearchInput(''); setPage(1); }}
            className="inline-flex items-center rounded-lg border border-line bg-card px-3 py-1.5 text-sm font-medium hover:bg-elevated"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1">
          {/* Message list */}
          <div ref={listRef} className={`min-w-0 flex-1 overflow-y-auto ${selected ? 'hidden xl:block' : ''}`}>
            {visibleTickets.map((t) => {
              const isSel = selectedId === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => openTicket(t.id)}
                  className={`flex w-full items-start gap-3 border-b border-line px-4 py-2.5 text-left transition-colors lg:px-6 ${
                    isSel ? 'bg-accent-weak' : 'hover:bg-elevated'
                  }`}
                >
                  <div className="mt-0.5 flex w-5 shrink-0 justify-center">
                    {t.phishing ? (
                      <ShieldAlert size={15} className="text-danger" aria-label="Flagged as phishing" />
                    ) : (
                      <ShieldCheck size={15} className="text-text-3" aria-label="No phishing flag" />
                    )}
                  </div>
                  <span className="w-36 shrink-0 truncate text-sm text-text-1" title={t.sender}>
                    {senderName(t.sender)}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm">
                    {t.subject ? (
                      <>
                        <span className="font-medium text-text-1">{t.subject}</span>
                        <span className="text-text-2"> — {t.message}</span>
                      </>
                    ) : (
                      <span className="text-text-2">{t.message}</span>
                    )}
                  </span>
                  <span className="hidden shrink-0 rounded px-1.5 py-0.5 text-xs text-text-2 bg-elevated md:inline">
                    {t.intent || 'Unclassified'}
                  </span>
                  <PriorityChip tier={t.priority} />
                  <span className="w-16 shrink-0 text-right text-xs text-text-3">
                    {relativeTime(t.created_at)}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Reading pane */}
          {selected && (
            <aside className="fixed inset-x-0 bottom-0 top-12 z-30 overflow-y-auto border-l border-line bg-card xl:static xl:z-auto xl:w-[26rem] xl:shrink-0 2xl:w-[30rem]">
              <div className="border-b border-line px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-base font-semibold leading-snug text-text-1">
                    {selected.subject || '(no subject)'}
                  </h2>
                  <button
                    onClick={() => { setSelected(null); setSelectedId(null); }}
                    className="rounded-lg p-1.5 text-text-2 hover:bg-elevated hover:text-text-1"
                    aria-label="Close reading pane"
                  >
                    <MailOpen size={16} />
                  </button>
                </div>
                <p className="mt-1 text-sm text-text-2">
                  <span className="text-text-1">{selected.sender || 'Unknown sender'}</span>
                  {selected.domain && <span> · {selected.domain}</span>}
                  <span> · {timeHM(selected.created_at)}</span>
                </p>
              </div>

              <div className="space-y-4 px-5 py-4">
                {selected.phishing === true && (
                  <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
                    Flagged as phishing in the source dataset
                    {selected.technique ? <> — technique: <strong>{selected.technique}</strong></> : null}
                    {selected.label ? <> · label: {selected.label}</> : null}
                  </div>
                )}

                <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-1">
                  {selected.message || '(empty message)'}
                </p>

                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-line pt-4 text-sm">
                  <div>
                    <dt className="text-xs text-text-3">Channel</dt>
                    <dd className="text-text-1">{selected.channel || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-3">Intent</dt>
                    <dd className="text-text-1">{selected.intent || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-3">Priority</dt>
                    <dd><PriorityChip tier={selected.priority} /></dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-3">Issue</dt>
                    <dd className="text-text-1">{selected.issue || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-3">Record ID</dt>
                    <dd className="text-text-1">#{selected.id}</dd>
                  </div>
                </dl>
              </div>
            </aside>
          )}
        </div>
      )}
    </div>
  );
};

export default Inbox;
