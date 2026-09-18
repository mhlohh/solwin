import React from 'react';
import {
  SecurityIntelligence,
} from '../../types/conversation';
import { RiskBadge } from '../common/RiskBadge';
import { ShieldAlert, ShieldCheck, AlertOctagon } from 'lucide-react';

interface SecurityInsightPanelProps {
  intelligence: SecurityIntelligence | null;
  isLoading?: boolean;
}

export const SecurityInsightPanel: React.FC<SecurityInsightPanelProps> = ({
  intelligence,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="bg-surface rounded-2xl border border-surface-border p-5 animate-pulse space-y-4 shadow-card">
        <div className="h-4 w-40 bg-slate-200 dark:bg-slate-800 rounded-md" />
        <div className="h-16 bg-slate-100 dark:bg-slate-800/40 rounded-xl" />
      </div>
    );
  }

  if (!intelligence) {
    return (
      <div className="bg-surface rounded-2xl border border-surface-border p-6 text-center text-slate-500 text-xs font-mono shadow-card">
        No security telemetry recorded for this session.
      </div>
    );
  }

  const isThreat = Boolean(intelligence.threat_detected);

  return (
    <div
      className={`rounded-2xl p-5 space-y-5 transition-all ${
        isThreat
          ? 'bg-rose-50 dark:bg-surface-card border border-rose-200 dark:border-rose-500/30 shadow-sm'
          : 'bg-surface rounded-2xl border border-surface-border shadow-card'
      }`}
    >
      {/* Header */}
      <div className={`flex items-center justify-between pb-3 border-b ${
        isThreat ? 'border-rose-200 dark:border-surface-border' : 'border-surface-border'
      }`}>
        <div className="flex items-center gap-2">
          <ShieldAlert size={16} className={isThreat ? 'text-rose-700 dark:text-rose-400' : 'text-slate-500'} />
          <h2 className={`text-xs font-semibold font-sans ${
            isThreat ? 'text-rose-700 dark:text-white font-bold' : 'text-slate-900 dark:text-white'
          }`}>
            Security Telemetry & Threat Scan
          </h2>
        </div>
        <RiskBadge level={intelligence.risk_level} />
      </div>

      {/* Threat Status Summary */}
      <div className={`grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 rounded-xl border ${
        isThreat
          ? 'bg-white/80 dark:bg-surface-elevated/70 border-rose-200/80 dark:border-surface-border'
          : 'bg-slate-50 dark:bg-surface-elevated/70 border-slate-200/80 dark:border-surface-border'
      }`}>
        <div>
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 block mb-1">Threat Detected</span>
          {intelligence.threat_detected ? (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 dark:text-rose-400">
              <ShieldAlert size={13} /> Yes
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
              <ShieldCheck size={13} /> None
            </span>
          )}
        </div>

        <div>
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 block mb-1">Classification</span>
          <span className={`text-xs font-medium block truncate ${isThreat ? 'text-rose-700 dark:text-slate-200 font-semibold' : 'text-slate-800 dark:text-slate-200'}`} title={intelligence.threat_type || 'None'}>
            {intelligence.threat_type || 'Benign'}
          </span>
        </div>

        <div>
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 block mb-1">Social Eng.</span>
          <span className={`text-xs font-medium ${intelligence.social_engineering_detected ? 'text-amber-700 dark:text-amber-300 font-semibold' : 'text-slate-500'}`}>
            {intelligence.social_engineering_detected ? 'Confirmed' : 'None'}
          </span>
        </div>
      </div>

      {/* Risk Reasons */}
      {intelligence.risk_reasons && intelligence.risk_reasons.length > 0 && (
        <div className={`rounded-xl p-3.5 space-y-2 border ${
          isThreat
            ? 'bg-white/90 dark:bg-surface-elevated/50 border-rose-200 dark:border-surface-border'
            : 'bg-slate-50 dark:bg-surface-elevated/50 border-slate-200 dark:border-surface-border'
        }`}>
          <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500 font-semibold block">
            Risk Engine Indicators
          </span>
          <ul className="space-y-1.5 pt-1">
            {intelligence.risk_reasons.map((reason, idx) => (
              <li key={idx} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-1.5">
                <span className="text-rose-400 mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Observed Techniques */}
      {intelligence.techniques && intelligence.techniques.length > 0 && (
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 font-semibold block">
            Observed Social Engineering Tactics
          </span>
          <div className="flex flex-wrap gap-1.5">
            {intelligence.techniques.map((t, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-500/25 text-xs font-mono font-medium"
              >
                • {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Suspicious URLs */}
      {intelligence.suspicious_urls && intelligence.suspicious_urls.length > 0 && (
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 font-semibold block">
            Suspicious URLs ({intelligence.suspicious_urls.length})
          </span>
          <div className="space-y-1.5">
            {intelligence.suspicious_urls.map((url, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-surface-elevated/70 border border-surface-border font-mono text-xs text-rose-300 truncate"
                title={url}
              >
                {url}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suspicious Email Indicators */}
      {intelligence.suspicious_emails && intelligence.suspicious_emails.length > 0 && (
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 font-semibold block">
            Suspicious Email Addresses ({intelligence.suspicious_emails.length})
          </span>
          <div className="space-y-1.5">
            {intelligence.suspicious_emails.map((email, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-surface-elevated/70 border border-surface-border font-mono text-xs text-amber-300 truncate"
                title={email}
              >
                {email}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Action */}
      {isThreat && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 space-y-1.5 shadow-sm">
          <div className="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-mono text-[11px] font-bold uppercase tracking-widest">
            <AlertOctagon size={15} />
            <span>Security Review Required</span>
          </div>
          <p className="text-xs text-rose-800 dark:text-rose-200 leading-relaxed font-sans font-medium">
            Verify sender authenticity before taking any action described in customer content. Do not click links or provide credentials.
          </p>
        </div>
      )}
    </div>
  );
};
