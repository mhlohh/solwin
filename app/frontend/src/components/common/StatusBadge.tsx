import React from 'react';
import { ConversationStatusType } from '../../types/conversation';

interface StatusBadgeProps {
  status: ConversationStatusType | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const norm = (status || 'Unresolved').toLowerCase();

  let styles = 'bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700/80';
  let dotColor = 'bg-slate-400';

  if (norm === 'resolved') {
    styles = 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30';
    dotColor = 'bg-emerald-500 dark:bg-emerald-400';
  } else if (norm === 'closed') {
    styles = 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30';
    dotColor = 'bg-emerald-500 dark:bg-emerald-400';
  } else if (norm === 'in_progress') {
    styles = 'bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/35';
    dotColor = 'bg-amber-500 dark:bg-amber-400';
  } else if (norm === 'open') {
    styles = 'bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-500/30';
    dotColor = 'bg-cyan-500 dark:bg-cyan-400';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-mono border font-medium ${styles}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span className="uppercase tracking-wider">{status}</span>
    </span>
  );
};
