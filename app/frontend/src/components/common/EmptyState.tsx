import React from "react";
import { Inbox, LucideIcon } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = Inbox,
  action,
}) => (
  <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-elevated text-text-3">
      <Icon size={19} />
    </div>
    <h3 className="mt-3 text-sm font-semibold text-text-1">{title}</h3>
    <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-text-2">
      {description}
    </p>
    {action && (
      <button
        onClick={action.onClick}
        className="mt-5 rounded-lg border border-line bg-card px-3.5 py-2 text-sm font-medium text-text-1 hover:bg-elevated"
      >
        {action.label}
      </button>
    )}
  </div>
);
