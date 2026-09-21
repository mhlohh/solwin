import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  statusCode?: number | string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message = "Please try again, or check that the backend service is running.",
  statusCode,
  onRetry,
}) => (
  <div className="surface-card mx-auto my-8 max-w-lg p-8 text-center">
    <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg border border-danger-line bg-danger-weak text-danger">
      <AlertCircle size={19} />
    </div>
    <h3 className="mt-3 text-sm font-semibold text-text-1">{title}</h3>
    {statusCode && (
      <div className="mt-1 font-mono text-xs text-text-3">HTTP {statusCode}</div>
    )}
    <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-text-2">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="mt-5 inline-flex items-center gap-2 rounded-lg border border-line bg-card px-3.5 py-2 text-sm font-medium text-text-1 hover:bg-elevated"
      >
        <RefreshCw size={14} />
        Retry
      </button>
    )}
  </div>
);
