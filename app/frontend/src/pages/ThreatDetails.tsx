import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getThreat } from '../services/securityApi';
import { Threat } from '../types/conversation';
import { RiskBadge } from '../components/common/RiskBadge';
import { ErrorState } from '../components/common/ErrorState';
import {
  ChevronLeft,
  ShieldAlert,
  MessageSquare,
  AlertOctagon,
  ExternalLink,
  Terminal,
} from 'lucide-react';

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString();
}

export const ThreatDetails: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [threat, setThreat] = useState<Threat | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadThreatDetails = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getThreat(id);
      setThreat(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load threat details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadThreatDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if ((error && !isLoading && !threat) || (!isLoading && !threat)) {
    return (
      <ErrorState
        title="Threat Record Unavailable"
        message={error || `Threat telemetry record ${id} was not found.`}
        onRetry={loadThreatDetails}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/threats')}
            className="p-2 rounded-xl border border-surface-border bg-surface-card text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors shadow-sm"
          >
            <ChevronLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-rose-400 flex items-center gap-1.5">
                <Terminal size={14} />
                {threat?.threat_type || 'UNCATEGORIZED'}
              </span>
              {threat && <RiskBadge level={threat.risk_level || 'LOW'} />}
            </div>
            <p className="text-xs font-mono text-slate-500 mt-1">
              Record ID: {threat?.id || id}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {threat?.conversation_id && (
            <button
              onClick={() => navigate(`/conversations/${threat.conversation_id}`)}
              className="px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border text-xs font-mono transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <MessageSquare size={14} className="text-brand-cyan" />
              <span>Inspect Source Ticket</span>
              <ExternalLink size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Threat Confirmed</span>
          <span className={`text-sm font-semibold ${threat?.threat_detected ? 'text-rose-400' : 'text-emerald-400'}`}>
            {threat?.threat_detected ? 'YES' : 'NO'}
          </span>
        </div>

        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Social Engineering</span>
          <span className={`text-sm font-semibold ${threat?.social_engineering_detected ? 'text-amber-400' : 'text-slate-400'}`}>
            {threat?.social_engineering_detected ? 'CONFIRMED' : 'NONE'}
          </span>
        </div>

        <div className="p-5 rounded-2xl bg-surface-card border border-surface-border shadow-card">
          <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Detection Time</span>
          <span className="text-sm font-mono text-slate-300">
            {threat?.created_at ? formatTime(threat.created_at) : '—'}
          </span>
        </div>
      </div>

      {/* Risk Engine Indicators */}
      {threat?.risk_reasons && threat.risk_reasons.length > 0 && (
        <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-card space-y-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 block">
            Risk Engine Indicators
          </span>
          <ul className="space-y-2 pt-1">
            {threat.risk_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                <span className="text-rose-400 mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Social Engineering Tactics */}
      {threat?.techniques && threat.techniques.length > 0 && (
        <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-card space-y-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 block">
            Observed Social Engineering Tactics
          </span>
          <div className="flex flex-wrap gap-2">
            {threat.techniques.map((t, i) => (
              <span
                key={i}
                className="px-3 py-1 rounded-xl bg-amber-500/10 text-amber-300 border border-amber-500/25 text-xs font-medium font-mono"
              >
                • {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Suspicious URLs */}
      {threat?.suspicious_urls && threat.suspicious_urls.length > 0 && (
        <div className="space-y-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 block">
            Suspicious Indicators: Malicious URLs ({threat.suspicious_urls.length})
          </span>
          <div className="space-y-2">
            {threat.suspicious_urls.map((url, i) => (
              <div
                key={i}
                className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-border font-mono text-xs text-rose-300 break-all"
                title={url}
              >
                {url}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suspicious Emails */}
      {threat?.suspicious_emails && threat.suspicious_emails.length > 0 && (
        <div className="space-y-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 block">
            Suspicious Indicators: Email Addresses ({threat.suspicious_emails.length})
          </span>
          <div className="space-y-2">
            {threat.suspicious_emails.map((email, i) => (
              <div
                key={i}
                className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-border font-mono text-xs text-amber-300 break-all"
                title={email}
              >
                {email}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Action */}
      {threat?.recommended_action && (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 space-y-2 shadow-glow-rose/15">
          <div className="flex items-center gap-2 text-rose-300 font-mono text-xs font-bold uppercase">
            <AlertOctagon size={16} />
            <span>Recommended Incident Mitigation Protocol</span>
          </div>
          <p className="text-xs text-rose-100 leading-relaxed font-sans">{threat.recommended_action}</p>
        </div>
      )}

      {/* Empty fallback when record has no indicators */}
      {threat &&
        !threat.risk_reasons?.length &&
        !threat.techniques?.length &&
        !threat.suspicious_urls?.length &&
        !threat.suspicious_emails?.length && (
          <div className="p-8 rounded-2xl border border-surface-border bg-surface-card text-center text-xs font-mono text-slate-500">
            <ShieldAlert size={20} className="mx-auto mb-2 text-slate-600" />
            This threat record contains no stored indicators.
          </div>
        )}
    </div>
  );
};
