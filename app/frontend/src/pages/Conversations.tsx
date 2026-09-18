import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getConversations } from "../services/conversationApi";
import {
  Conversation,
  ConversationFilterParams,
  ChannelType,
  ConversationStatusType,
} from "../types/conversation";
import { SearchBar } from "../components/common/SearchBar";
import { StatusBadge } from "../components/common/StatusBadge";
import { TableSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";
import { RefreshCw } from "lucide-react";

const CHANNEL_OPTIONS: { value: ChannelType | ""; label: string }[] = [
  { value: "", label: "All channels" },
  { value: "EMAIL", label: "Email" },
  { value: "CHAT", label: "Chat" },
  { value: "TICKET", label: "Ticket" },
  { value: "SOCIAL_MEDIA", label: "Social media" },
  { value: "OTHER", label: "Other" },
];

const STATUS_OPTIONS: { value: ConversationStatusType | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "OPEN", label: "Open" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "RESOLVED", label: "Resolved" },
  { value: "CLOSED", label: "Closed" },
];

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

export const Conversations: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [channel, setChannel] = useState<ChannelType | "">(
    (searchParams.get("channel") as ChannelType) || ""
  );
  const [status, setStatus] = useState<ConversationStatusType | "">(
    (searchParams.get("status") as ConversationStatusType) || ""
  );

  const load = async () => {
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
      setSelected((prev) =>
        prev && res.items.some((c) => c.id === prev.id)
          ? prev
          : res.items[0] || null
      );
    } catch {
      setConversations([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, channel, status, page]);

  const hasFilters = channel || status || search;

  return (
    <div className="space-y-4 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Conversations</h1>
          <p className="text-sm text-text-2">
            {total} conversation{total === 1 ? "" : "s"} in the queue
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

      {/* Filters */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchBar
          placeholder="Search customer, reference, or subject…"
          value={search}
          onChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          className="sm:max-w-sm sm:flex-1"
        />
        <div className="flex items-center gap-2">
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as ConversationStatusType | "");
              setPage(1);
            }}
            className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm text-text-1 hover:border-line-strong focus:border-accent focus:outline-none"
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
              setChannel(e.target.value as ChannelType | "");
              setPage(1);
            }}
            className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm text-text-1 hover:border-line-strong focus:border-accent focus:outline-none"
          >
            {CHANNEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {hasFilters && (
            <button
              onClick={() => {
                setChannel("");
                setStatus("");
                setSearch("");
                setPage(1);
              }}
              className="rounded-lg px-2.5 py-2 text-sm font-medium text-accent hover:bg-accent-weak"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-5">
        {/* List */}
        <div className="lg:col-span-3">
          {isLoading ? (
            <TableSkeleton rows={6} />
          ) : conversations.length === 0 ? (
            <div className="surface-card">
              <EmptyState
                title="No conversations match"
                description="Try different search terms or clear the filters."
                action={
                  hasFilters
                    ? {
                        label: "Clear filters",
                        onClick: () => {
                          setChannel("");
                          setStatus("");
                          setSearch("");
                          setPage(1);
                        },
                      }
                    : undefined
                }
              />
            </div>
          ) : (
            <div className="surface-card overflow-hidden">
              {conversations.map((conv) => {
                const isSel = selected?.id === conv.id;
                return (
                  <button
                    key={conv.id}
                    onClick={() => setSelected(conv)}
                    onDoubleClick={() => navigate(`/conversations/${conv.id}`)}
                    className={`block w-full border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 ${
                      isSel ? "bg-accent-weak" : "hover:bg-elevated"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="min-w-0 truncate text-sm font-medium text-text-1">
                        {conv.subject || "(no subject)"}
                      </span>
                      <StatusBadge status={conv.status} />
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-xs text-text-3">
                      <span className="font-medium text-text-2">
                        {conv.customer_name || "Unknown"}
                      </span>
                      <span>·</span>
                      <span>{conv.conversation_reference}</span>
                      <span>·</span>
                      <span>{timeAgo(conv.updated_at)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {totalPages > 1 && (
            <div className="mt-3 flex items-center justify-between text-sm text-text-2">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-1.5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded-lg border border-line bg-card px-3 py-1.5 font-medium text-text-1 hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="rounded-lg border border-line bg-card px-3 py-1.5 font-medium text-text-1 hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Preview pane */}
        <div className="surface-card sticky top-16 lg:col-span-2">
          {selected ? (
            <div className="p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-text-3">
                  {selected.conversation_reference}
                </span>
                <StatusBadge status={selected.status} />
              </div>
              <h2 className="mt-2 text-base font-semibold text-text-1">
                {selected.customer_name || "Unknown customer"}
              </h2>
              {selected.customer_email && (
                <p className="text-sm text-text-2">{selected.customer_email}</p>
              )}

              <dl className="mt-4 space-y-2.5 text-sm">
                <div>
                  <dt className="section-label">Subject</dt>
                  <dd className="mt-0.5 text-text-1">
                    {selected.subject || "(no subject)"}
                  </dd>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <dt className="section-label">Channel</dt>
                    <dd className="mt-0.5 text-text-1">
                      {CHANNEL_OPTIONS.find((o) => o.value === selected.channel)
                        ?.label || selected.channel}
                    </dd>
                  </div>
                  <div>
                    <dt className="section-label">Created</dt>
                    <dd className="mt-0.5 text-text-1">
                      {timeAgo(selected.created_at)}
                    </dd>
                  </div>
                </div>
              </dl>

              <button
                onClick={() => navigate(`/conversations/${selected.id}`)}
                className="mt-5 w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Open conversation
              </button>
            </div>
          ) : (
            <p className="px-4 py-12 text-center text-sm text-text-3">
              Select a conversation to preview it here.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
