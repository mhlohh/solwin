import React from "react";

const shimmer = "rounded-md bg-inset animate-pulse";

export const CardSkeleton: React.FC<{ count?: number }> = ({ count = 4 }) => (
  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="surface-card px-4 py-3.5">
        <div className={`h-3 w-24 ${shimmer}`} />
        <div className={`mt-3 h-7 w-16 ${shimmer}`} />
        <div className={`mt-3 h-3 w-32 ${shimmer}`} />
      </div>
    ))}
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 6 }) => (
  <div className="surface-card overflow-hidden">
    <div className="border-b border-line px-4 py-3">
      <div className={`h-3 w-40 ${shimmer}`} />
    </div>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="border-b border-line px-4 py-3.5 last:border-b-0">
        <div className={`h-3.5 ${i % 3 === 1 ? "w-2/3" : "w-1/2"} ${shimmer}`} />
      </div>
    ))}
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div className="surface-card p-5">
    <div className={`h-4 w-48 ${shimmer}`} />
    <div className={`mt-6 h-64 w-full ${shimmer}`} />
  </div>
);

export const LineSkeleton: React.FC<{ className?: string }> = ({ className = "w-56" }) => (
  <div className={`h-5 ${className} ${shimmer}`} />
);
