import React from "react";
import { SecurityIntelligence } from "../../types/conversation";
import { RiskBadge } from "../common/RiskBadge";

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
      <div className="surface-card p-4">
        <div className="h-4 w-40 animate-pulse rounded-md bg-inset" />
        <div className="mt-3 h-16 animate-pulse rounded-lg bg-inset" />
      </div>
    );
  }

  if (!intelligence) {
    return (
      <div className="surface-card px-4 py-8 text-center text-sm text-text-3">
        No security analysis recorded.
      </div>
    );
  }

  const isThreat = Boolean(intelligence.threat_detected);

  return (
    <div
      className={`surface-card overflow-hidden ${
        isThreat ? "border-danger-line" : ""
      }`}
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold">Security scan</h2>
        <RiskBadge level={intelligence.risk_level} />
      </div>

      <div className="space-y-4 px-4 py-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="section-label">Threat detected</div>
            <div
              className={`mt-1 font-medium ${
                intelligence.threat_detected ? "text-danger" : "text-ok"
              }`}
            >
              {intelligence.threat_detected ? "Yes" : "No"}
            </div>
          </div>
          <div>
            <div className="section-label">Classification</div>
            <div className="mt-1 font-medium text-text-1">
              {intelligence.threat_type && intelligence.threat_type !== "NONE"
                ? intelligence.threat_type
                : "None"}
            </div>
          </div>
          <div>
            <div className="section-label">Social engineering</div>
            <div
              className={`mt-1 font-medium ${
                intelligence.social_engineering_detected ? "text-warn" : "text-text-2"
              }`}
            >
              {intelligence.social_engineering_detected ? "Detected" : "None"}
            </div>
          </div>
        </div>

        {intelligence.risk_reasons && intelligence.risk_reasons.length > 0 && (
          <div>
            <div className="section-label mb-1.5">Findings</div>
            <ul className="space-y-1.5">
              {intelligence.risk_reasons.map((reason, idx) => (
                <li
                  key={idx}
                  className="rounded-lg border border-line bg-elevated px-3 py-2 text-sm text-text-1"
                >
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {intelligence.techniques && intelligence.techniques.length > 0 && (
          <div>
            <div className="section-label mb-1.5">Tactics observed</div>
            <div className="flex flex-wrap gap-1.5">
              {intelligence.techniques.map((t, idx) => (
                <span
                  key={idx}
                  className="rounded-full border border-warn-line bg-warn-weak px-2 py-0.5 font-mono text-xs text-warn"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}

        {intelligence.suspicious_urls && intelligence.suspicious_urls.length > 0 && (
          <div>
            <div className="section-label mb-1.5">
              Suspicious URLs ({intelligence.suspicious_urls.length})
            </div>
            <div className="space-y-1.5">
              {intelligence.suspicious_urls.map((url, idx) => (
                <div
                  key={idx}
                  className="break-all rounded-lg border border-danger-line bg-danger-weak px-3 py-2 font-mono text-xs text-danger"
                  title={url}
                >
                  {url}
                </div>
              ))}
            </div>
          </div>
        )}

        {intelligence.suspicious_emails && intelligence.suspicious_emails.length > 0 && (
          <div>
            <div className="section-label mb-1.5">
              Suspicious addresses ({intelligence.suspicious_emails.length})
            </div>
            <div className="space-y-1.5">
              {intelligence.suspicious_emails.map((email, idx) => (
                <div
                  key={idx}
                  className="break-all rounded-lg border border-warn-line bg-warn-weak px-3 py-2 font-mono text-xs text-warn"
                  title={email}
                >
                  {email}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
