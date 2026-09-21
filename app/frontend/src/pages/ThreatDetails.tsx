import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getThreat } from "../services/securityApi";
import { Threat } from "../types/conversation";
import { RiskBadge } from "../components/common/RiskBadge";
import { ErrorState } from "../components/common/ErrorState";
import { ChevronLeft, MessageSquare } from "lucide-react";

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString();
}

export const ThreatDetails: React.FC = () => {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [threat, setThreat] = useState<Threat | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setIsLoading(true);
    setError(null);
    try {
      setThreat(await getThreat(id));
    } catch (err: any) {
      setError(err.message || "Failed to load threat details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if ((error && !isLoading && !threat) || (!isLoading && !threat)) {
    return (
      <ErrorState
        title="Threat record unavailable"
        message={error || `Threat record ${id} was not found.`}
        onRetry={load}
      />
    );
  }

  const hasIndicators =
    (threat?.risk_reasons?.length || 0) > 0 ||
    (threat?.techniques?.length || 0) > 0 ||
    (threat?.suspicious_urls?.length || 0) > 0 ||
    (threat?.suspicious_emails?.length || 0) > 0;

  return (
    <div className="space-y-5 pb-10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/threats")}
            className="rounded-lg border border-line bg-card p-1.5 text-text-2 hover:bg-elevated hover:text-text-1"
            aria-label="Back to threats"
          >
            <ChevronLeft size={16} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold tracking-tight">
                {threat?.threat_type === "NONE" || !threat?.threat_type
                  ? "Clean scan — no security signals"
                  : threat?.threat_type.replace(/_/g, " ")}
              </h1>
              {threat && <RiskBadge level={threat.risk_level || "LOW"} />}
            </div>
            <p className="mt-0.5 font-mono text-xs text-text-3">
              {threat?.id || id}
            </p>
          </div>
        </div>

        {threat?.conversation_id && (
          <button
            onClick={() => navigate(`/conversations/${threat.conversation_id}`)}
            className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-2 text-sm font-medium text-text-1 hover:bg-elevated"
          >
            <MessageSquare size={14} />
            View source conversation
          </button>
        )}
      </div>

      {/* Facts */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="surface-card px-4 py-3.5">
          <div className="section-label">Threat confirmed</div>
          <div
            className={`mt-1 text-sm font-semibold ${
              threat?.threat_detected ? "text-danger" : "text-ok"
            }`}
          >
            {threat?.threat_detected ? "Yes" : "No"}
          </div>
        </div>
        <div className="surface-card px-4 py-3.5">
          <div className="section-label">Social engineering</div>
          <div
            className={`mt-1 text-sm font-semibold ${
              threat?.social_engineering_detected ? "text-warn" : "text-text-2"
            }`}
          >
            {threat?.social_engineering_detected ? "Detected" : "None"}
          </div>
        </div>
        <div className="surface-card px-4 py-3.5">
          <div className="section-label">Detected at</div>
          <div className="mt-1 text-sm text-text-1">
            {threat?.created_at ? formatTime(threat.created_at) : "—"}
          </div>
        </div>
      </div>

      {threat?.risk_reasons && threat.risk_reasons.length > 0 && (
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">Findings</h2>
          </div>
          <ul className="space-y-1.5 px-4 py-4">
            {threat.risk_reasons.map((reason, i) => (
              <li key={i} className="text-sm leading-relaxed text-text-1">
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {threat?.techniques && threat.techniques.length > 0 && (
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">Tactics observed</h2>
          </div>
          <div className="flex flex-wrap gap-1.5 px-4 py-4">
            {threat.techniques.map((t, i) => (
              <span
                key={i}
                className="rounded-full border border-warn-line bg-warn-weak px-2.5 py-1 font-mono text-xs text-warn"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {threat?.suspicious_urls && threat.suspicious_urls.length > 0 && (
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">
              Suspicious URLs ({threat.suspicious_urls.length})
            </h2>
          </div>
          <div className="space-y-1.5 px-4 py-4">
            {threat.suspicious_urls.map((url, i) => (
              <div
                key={i}
                className="break-all rounded-lg border border-danger-line bg-danger-weak px-3 py-2 font-mono text-xs text-danger"
              >
                {url}
              </div>
            ))}
          </div>
        </div>
      )}

      {threat?.suspicious_emails && threat.suspicious_emails.length > 0 && (
        <div className="surface-card">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold">
              Suspicious addresses ({threat.suspicious_emails.length})
            </h2>
          </div>
          <div className="space-y-1.5 px-4 py-4">
            {threat.suspicious_emails.map((email, i) => (
              <div
                key={i}
                className="break-all rounded-lg border border-warn-line bg-warn-weak px-3 py-2 font-mono text-xs text-warn"
              >
                {email}
              </div>
            ))}
          </div>
        </div>
      )}

      {threat?.recommended_action && (
        <div className="surface-card p-4">
          <div className="section-label">Recommended action</div>
          <p className="mt-1.5 text-sm leading-relaxed text-text-1">
            {threat.recommended_action}
          </p>
        </div>
      )}

      {threat && !hasIndicators && (
        <p className="py-6 text-center text-sm text-text-3">
          This record contains no stored indicators.
        </p>
      )}
    </div>
  );
};
