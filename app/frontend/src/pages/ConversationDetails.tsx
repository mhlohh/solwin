import React, { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getConversation, appendMessage } from "../services/conversationApi";
import {
  analyzeConversation,
  getUnifiedAnalysis,
  toCustomerIntelligence,
} from "../services/analysisApi";
import { getSecurityIntelligenceForConversation } from "../services/securityApi";
import {
  ConversationDetail,
  CustomerIntelligence,
  Message,
  SecurityIntelligence,
} from "../types/conversation";
import { SecurityInsightPanel } from "../components/security/SecurityInsightPanel";
import { PriorityBadge } from "../components/common/PriorityBadge";
import { SentimentBadge } from "../components/common/SentimentBadge";
import { StatusBadge } from "../components/common/StatusBadge";
import { ErrorState } from "../components/common/ErrorState";
import {
  ChevronLeft,
  RefreshCw,
  Sparkles,
  Send,
  User,
  Headset,
} from "lucide-react";

const CHANNEL_LABELS: Record<string, string> = {
  EMAIL: "Email",
  CHAT: "Chat",
  TICKET: "Ticket",
  SOCIAL_MEDIA: "Social",
  OTHER: "Other",
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

export const ConversationDetails: React.FC = () => {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [customerAi, setCustomerAi] = useState<CustomerIntelligence | null>(null);
  const [securityAi, setSecurityAi] = useState<SecurityIntelligence | null>(null);
  const [recommendedAction, setRecommendedAction] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [isSending, setIsSending] = useState(false);

  const loadAllDetails = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const conv = await getConversation(id);
      setConversation(conv);
      setCustomerAi(toCustomerIntelligence(conv.analysis_records?.[0]));

      const [sec, unified] = await Promise.allSettled([
        getSecurityIntelligenceForConversation(id),
        getUnifiedAnalysis(id),
      ]);
      if (sec.status === "fulfilled") setSecurityAi(sec.value);
      if (unified.status === "fulfilled")
        setRecommendedAction(unified.value.recommended_action);
    } catch (err: any) {
      setError(err.message || "Failed to load conversation details.");
    } finally {
      setIsLoading(false);
    }
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setError(null);
    try {
      const result = await analyzeConversation(id);
      setCustomerAi(result.customer_intelligence);
      setSecurityAi(result.security_intelligence);
      setRecommendedAction(result.recommended_action);
    } catch (err: any) {
      setError(err.message || "Analysis failed. Is the backend running?");
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    loadAllDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const sendMessage = async () => {
    if (!reply.trim() || !conversation) return;
    setIsSending(true);
    try {
      await appendMessage(id, reply.trim(), "AGENT", "Support Agent");
      setReply("");
      await loadAllDetails();
    } catch (err: any) {
      setError(err.message || "Failed to send message.");
    } finally {
      setIsSending(false);
    }
  };

  const messages: Message[] = useMemo(
    () => conversation?.messages || [],
    [conversation]
  );

  if (error && !isLoading && !conversation) {
    return (
      <ErrorState
        title="Conversation not found"
        message={error}
        onRetry={loadAllDetails}
      />
    );
  }

  return (
    <div className="space-y-5 pb-10">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/conversations")}
            className="rounded-lg border border-line bg-card p-1.5 text-text-2 hover:bg-elevated hover:text-text-1"
            aria-label="Back to conversations"
          >
            <ChevronLeft size={16} />
          </button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-semibold tracking-tight">
                {conversation?.subject || "Conversation"}
              </h1>
              {conversation && <StatusBadge status={conversation.status} />}
            </div>
            <p className="mt-0.5 text-sm text-text-2">
              {conversation?.customer_name || "Unknown customer"}
              {conversation?.customer_email && ` · ${conversation.customer_email}`}
              {conversation &&
                ` · ${CHANNEL_LABELS[conversation.channel] || conversation.channel} · ${
                  conversation.conversation_reference
                }`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={runAnalysis}
            disabled={isAnalyzing}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            <Sparkles size={14} className={isAnalyzing ? "animate-pulse" : ""} />
            {isAnalyzing ? "Analyzing…" : "Run AI analysis"}
          </button>
          <button
            onClick={loadAllDetails}
            className="rounded-lg border border-line bg-card p-2 text-text-2 hover:bg-elevated hover:text-text-1"
            aria-label="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {error && conversation && (
        <div className="rounded-lg border border-danger-line bg-danger-weak px-4 py-2.5 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-5">
        {/* Thread */}
        <div className="lg:col-span-3">
          <div className="surface-card">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-sm font-semibold">Messages</h2>
            </div>

            {isLoading ? (
              <div className="px-4 py-10 text-center text-sm text-text-3">
                Loading…
              </div>
            ) : messages.length === 0 ? (
              <p className="px-4 py-10 text-center text-sm text-text-3">
                No messages in this conversation.
              </p>
            ) : (
              <div className="space-y-4 px-4 py-4">
                {messages.map((msg) => {
                  const isCustomer = msg.sender_type === "CUSTOMER";
                  return (
                    <div key={msg.id} className="flex items-start gap-3">
                      <div
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${
                          isCustomer
                            ? "border-line bg-elevated text-text-2"
                            : "border-accent-line bg-accent-weak text-accent"
                        }`}
                        title={msg.sender_name || msg.sender_type}
                      >
                        {isCustomer ? <User size={13} /> : <Headset size={13} />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-baseline gap-2">
                          <span className="text-sm font-medium text-text-1">
                            {msg.sender_name || msg.sender_type}
                          </span>
                          <span className="text-xs text-text-3">
                            {formatTime(msg.created_at)}
                          </span>
                        </div>
                        <p className="mt-1 whitespace-pre-line rounded-lg rounded-tl-none border border-line bg-elevated px-3 py-2.5 text-sm leading-relaxed text-text-1">
                          {msg.content}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Reply composer */}
            <div className="border-t border-line px-4 py-3">
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder="Write a reply as agent…"
                rows={2}
                className="w-full resize-y rounded-lg border border-line bg-card px-3 py-2 text-sm text-text-1 placeholder:text-text-3 focus:border-accent focus:outline-none"
              />
              <div className="mt-2 flex justify-end">
                <button
                  onClick={sendMessage}
                  disabled={isSending || !reply.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
                >
                  <Send size={13} />
                  {isSending ? "Sending…" : "Send reply"}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Intelligence */}
        <div className="space-y-5 lg:col-span-2">
          <div className="surface-card">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="text-sm font-semibold">AI triage</h2>
              {customerAi && (
                <span className="rounded-full border border-ok-line bg-ok-weak px-2 py-0.5 text-xs font-medium text-ok">
                  Analyzed
                </span>
              )}
            </div>

            {customerAi ? (
              <div className="space-y-4 px-4 py-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="section-label">Category</div>
                    <div className="mt-1 text-sm font-medium text-text-1">
                      {customerAi.category
                        .toLowerCase()
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (c) => c.toUpperCase())}
                    </div>
                  </div>
                  <div>
                    <div className="section-label">Emotion</div>
                    <div className="mt-1 text-sm font-medium text-text-1">
                      {customerAi.emotion || "Neutral"}
                    </div>
                  </div>
                  <div>
                    <div className="section-label">Sentiment</div>
                    <div className="mt-1">
                      <SentimentBadge sentiment={customerAi.sentiment} />
                    </div>
                  </div>
                  <div>
                    <div className="section-label">Priority</div>
                    <div className="mt-1">
                      <PriorityBadge priority={customerAi.priority} />
                    </div>
                  </div>
                </div>

                <div>
                  <div className="section-label">Issue</div>
                  <p className="mt-1 text-sm leading-relaxed text-text-1">
                    {customerAi.issue}
                  </p>
                </div>

                <div>
                  <div className="section-label">Summary</div>
                  <p className="mt-1 text-sm leading-relaxed text-text-2">
                    {customerAi.summary}
                  </p>
                </div>
              </div>
            ) : (
              <div className="px-4 py-8 text-center text-sm text-text-3">
                Not analyzed yet. Run AI analysis to generate triage.
              </div>
            )}
          </div>

          <SecurityInsightPanel intelligence={securityAi} isLoading={isLoading} />

          {recommendedAction && (
            <div className="surface-card p-4">
              <div className="section-label">Recommended action</div>
              <p className="mt-1.5 text-sm leading-relaxed text-text-1">
                {recommendedAction}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
