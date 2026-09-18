import React, { useState, useEffect } from "react";
import { Search, X } from "lucide-react";

interface SearchBarProps {
  placeholder?: string;
  value?: string;
  onChange: (value: string) => void;
  debounceMs?: number;
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = "Search…",
  value: initialValue = "",
  onChange,
  debounceMs = 300,
  className = "",
}) => {
  const [query, setQuery] = useState(initialValue);

  useEffect(() => {
    setQuery(initialValue);
  }, [initialValue]);

  useEffect(() => {
    const handler = setTimeout(() => {
      if (query !== initialValue) onChange(query);
    }, debounceMs);
    return () => clearTimeout(handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, debounceMs]);

  return (
    <div className={`relative ${className}`}>
      <Search
        size={15}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-3"
      />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-line bg-card py-2 pl-9 pr-8 text-sm text-text-1 placeholder:text-text-3 focus:border-accent focus:outline-none"
      />
      {query && (
        <button
          onClick={() => {
            setQuery("");
            onChange("");
          }}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-text-3 hover:text-text-1"
          aria-label="Clear search"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};
