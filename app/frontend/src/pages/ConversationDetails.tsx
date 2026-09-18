import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConversation, appendMessage } from '../services/conversationApi';
import {
  analyzeConversation,
  getUnifiedAnalysis,
  toCustomerIntelligence,
} from '../services/analysisApi';
import { getSecurityIntelligenceForConversation } from '../services/securityApi';
import {
  ConversationDetail,
  CustomerIntelligence,
  Message,
  SecurityIntelligence,
} from '../types/conversation';
import { SecurityInsightPanel } from '../components/security/SecurityInsightPanel';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { SentimentBadge } from '../components/common/SentimentBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { ErrorState } from '../components/common/ErrorState';
import {
  ChevronLeft,
  RefreshCw,
  User,
  Bot,
  Sparkles,
  CheckCircle2,
  Send,
} from 'lucide-react';

const CHANNEL_LABELS: Record<string, string> = {
  EMAIL: 'Email',
  CHAT: 'Chat',
  TICKET: 'Ticket',
  SOCIAL_MEDIA: 'Social',
  OTHER: 'Other',
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString();
}

export const ConversationDetails: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [customerAi, setCustomerAi] = useState<CustomerIntelligence | null>(null);
  const [securityAi, setSecurityAi] = useState<SecurityIntelligence | null>(null);
  const [recommendedAction, setRecommendedAction] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState('');
  const [isSending, setIsSending] = useState(false);

  const loadAllDetails = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const conv = await getConversation(id);
      setConversation(conv);
      setCustomerAi(toCustomerIntelligence(conv.analysis_records?.[0]));

      // Load persisted intelligence in parallel; absence is not an error.
      const [sec, unified] = await Promise.allSettled([
        getSecurityIntelligenceForConversation(id),
        getUnifiedAnalysis(id),
      ]);
      if (sec.status === 'fulfilled') setSecurityAi(sec.value);
      if (unified.status === 'fulfilled') {
        setRecommendedAction(unified.value.recommended_action);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load conversation details.');
    } finally {
      setIsLoading(false);
    }
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const result = await analyzeConversation(id);
      setCustomerAi(result.customer_intelligence);
      setSecurityAi(result.security_intelligence);
      setRecommendedAction(result.recommended_action);
    } catch (err: any) {
      setError(err.message || 'Analysis failed.');
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
      await appendMessage(id, reply.trim(), 'AGENT', 'Support Agent');
      setReply('');
      await loadAllDetails();
    } catch (err: any) {
      setError(err.message || 'Failed to send message.');
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
        message={error || `Could not find records for ticket ${id}`}
        onRetry={loadAllDetails}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-surface rounded-2xl border border-surface-border shadow-card">
        <div className="flex items-center gap-3.5">
          <button
            onClick={() => navigate('/conversations')}
            className="p-2 rounded-xl border border-surface-border bg-surface-elevated hover:bg-slate-800 text-slate-400 hover:text-white transition-all shadow-sm"
            title="Back to conversations"
          >
            <ChevronLeft size={18} />
          </button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-brand-cyan font-bold px-2.5 py-0.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
                {conversation?.conversation_reference || id}
              </span>
              {conversation && <StatusBadge status={conversation.status} />}
            </div>
            <h1 className="text-lg font-bold text-white mt-1.5 font-sans flex items-center gap-2">
              <span>{conversation?.customer_name || 'Unknown Customer'}</span>
              {conversation && (
                <span className="text-xs font-mono font-normal text-slate-500">
                  ({CHANNEL_LABELS[conversation.channel] || conversation.channel})
                </span>
              )}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={runAnalysis}
            disabled={isAnalyzing}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-brand-cyan to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-mono font-bold uppercase tracking-wider transition-all flex items-center gap-2 shadow-glow-cyan/25 disabled:opacity-50"
          >
            <Sparkles size={14} className={isAnalyzing ? 'animate-pulse' : ''} />
            <span>{isAnalyzing ? 'Analyzing...' : 'Run AI Analysis'}</span>
          </button>

          <button
            onClick={loadAllDetails}
            className="p-2 rounded-xl border border-surface-border bg-surface-elevated hover:bg-slate-800 text-slate-400 hover:text-white transition-all shadow-sm"
            title="Refresh details"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Two-column workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: message timeline */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-surface rounded-2xl border border-surface-border p-5 space-y-4 shadow-card">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 block">
              Communication Timeline
            </span>

            {isLoading ? (
              <div className="py-8 text-center text-slate-500 text-xs font-mono animate-pulse">
                Loading messages...
              </div>
            ) : messages.length === 0 ? (
              <div className="p-8 text-center rounded-2xl border border-surface-border bg-surface-elevated/50 text-slate-500 text-xs font-mono">
                No message history available for this record.
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((msg) => {
                  const isCustomer = msg.sender_type === 'CUSTOMER';
                  return (
                    <div
                      key={msg.id}
                      className={`flex items-start gap-3.5 ${isCustomer ? 'flex-row' : 'flex-row-reverse'}`}
                    >
                      <div
                        className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center text-xs font-bold shadow-sm ${
                          isCustomer
                            ? 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                            : 'bg-cyan-500 text-slate-950 font-mono'
                        }`}
                      >
                        {isCustomer ? <User size={14} /> : <Bot size={14} />}
                      </div>

                      <div className={`max-w-2xl space-y-1.5 ${isCustomer ? 'items-start' : 'items-end'}`}>
                        <div className={`flex items-center gap-2 text-xs ${isCustomer ? 'flex-row' : 'flex-row-reverse'}`}>
                          <span className="font-semibold text-slate-300">
                            {msg.sender_name || msg.sender_type}
                          </span>
                          <span className="text-[11px] text-slate-500">{formatTime(msg.created_at)}</span>
                        </div>

                        <div
                          className={`p-4 rounded-2xl text-xs leading-relaxed shadow-card border ${
                            isCustomer
                              ? 'bg-slate-50 dark:bg-surface-card border-slate-200 dark:border-surface-border text-slate-800 dark:text-slate-200'
                              : 'bg-blue-50 dark:bg-surface-elevated border-blue-100 dark:border-brand-cyan/20 text-blue-950 dark:text-slate-100'
                          }`}
                        >
                          <p className="whitespace-pre-line leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Agent reply composer */}
            <div className="pt-2 border-t border-surface-border space-y-2">
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder="Write an agent reply..."
                rows={2}
                className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan/40 transition-all"
              />
              <div className="flex justify-end">
                <button
                  onClick={sendMessage}
                  disabled={isSending || !reply.trim()}
                  className="px-4 py-2 rounded-xl bg-brand-cyan hover:bg-cyan-400 text-slate-950 text-xs font-mono font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 disabled:opacity-40"
                >
                  <Send size={13} />
                  <span>{isSending ? 'Sending...' : 'Send Reply'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: intelligence panels */}
        <div className="lg:col-span-5 space-y-6">
          {/* Customer intelligence */}
          <div className="bg-surface rounded-2xl border border-surface-border p-5 space-y-5 shadow-card">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div className="flex items-center gap-2 text-brand-cyan">
                <Sparkles size={16} />
                <h2 className="text-xs font-semibold text-white font-sans">
                  Customer Intelligence & NLP Triage
                </h2>
              </div>
              {customerAi && (
                <span className="text-[11px] text-brand-cyan font-mono px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 font-bold uppercase tracking-widest">
                  ANALYZED
                </span>
              )}
            </div>

            {customerAi ? (
              <>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-surface-elevated/60 border border-surface-border">
                    <span className="text-slate-500 text-[11px] font-mono uppercase tracking-widest block mb-1">Category</span>
                    <span className="font-semibold text-slate-200">{customerAi.category}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-elevated/60 border border-surface-border">
                    <span className="text-slate-500 text-[11px] font-mono uppercase tracking-widest block mb-1">Detected Emotion</span>
                    <span className="text-slate-200 font-semibold font-mono">{customerAi.emotion || 'Neutral'}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-elevated/60 border border-surface-border">
                    <span className="text-slate-500 text-[11px] font-mono uppercase tracking-widest block mb-1">Sentiment</span>
                    <SentimentBadge sentiment={customerAi.sentiment} />
                  </div>
                  <div className="p-3 rounded-xl bg-surface-elevated/60 border border-surface-border">
                    <span className="text-slate-500 text-[11px] font-mono uppercase tracking-widest block mb-1">Priority</span>
                    <PriorityBadge priority={customerAi.priority} />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 font-semibold block">
                    Issue Synopsis
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed">{customerAi.issue}</p>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 font-semibold block">
                    Incident Summary
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed bg-surface-elevated/40 p-3.5 rounded-xl border border-surface-border">
                    {customerAi.summary}
                  </p>
                </div>
              </>
            ) : (
              <div className="bg-surface-elevated/40 rounded-xl p-6 text-center text-slate-500 text-xs font-mono">
                No customer intelligence yet. Run AI analysis to generate it.
              </div>
            )}
          </div>

          <SecurityInsightPanel intelligence={securityAi} isLoading={isLoading} />

          {/* Recommended action */}
          {recommendedAction && (
            <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/30 space-y-1.5 shadow-sm">
              <div className="flex items-center gap-2 text-indigo-300 text-[11px] font-mono font-bold uppercase tracking-widest">
                <CheckCircle2 size={14} />
                <span>Recommended Action</span>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{recommendedAction}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
