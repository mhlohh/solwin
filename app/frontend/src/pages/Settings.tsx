import React, { useState } from "react";
import { useTheme } from "../context/ThemeContext";
import { API_BASE_URL } from "../services/api";
import { Check, Moon, Sun } from "lucide-react";

export const Settings: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState(API_BASE_URL);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem("solwin_custom_api_url", apiUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="max-w-2xl space-y-6 pb-10">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-text-2">
          Appearance and backend connection.
        </p>
      </div>

      {/* Appearance */}
      <section className="surface-card">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">Appearance</h2>
        </div>
        <div className="px-4 py-4">
          <div className="grid max-w-md grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTheme("light")}
              className={`rounded-lg border p-3.5 text-left transition-colors ${
                theme === "light"
                  ? "border-accent bg-accent-weak"
                  : "border-line hover:bg-elevated"
              }`}
            >
              <Sun size={16} className="text-text-2" />
              <div className="mt-2 text-sm font-medium text-text-1">Light</div>
              <p className="mt-0.5 text-xs text-text-2">
                Bright and neutral, best for daytime
              </p>
            </button>
            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={`rounded-lg border p-3.5 text-left transition-colors ${
                theme === "dark"
                  ? "border-accent bg-accent-weak"
                  : "border-line hover:bg-elevated"
              }`}
            >
              <Moon size={16} className="text-text-2" />
              <div className="mt-2 text-sm font-medium text-text-1">Dark</div>
              <p className="mt-0.5 text-xs text-text-2">
                Low-glare, comfortable at night
              </p>
            </button>
          </div>
        </div>
      </section>

      {/* API connection */}
      <section className="surface-card">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">Backend connection</h2>
        </div>
        <form onSubmit={handleSave} className="space-y-3 px-4 py-4">
          <label className="section-label" htmlFor="api-url">
            API base URL
          </label>
          <input
            id="api-url"
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full rounded-lg border border-line bg-card px-3 py-2 font-mono text-sm text-text-1 focus:border-accent focus:outline-none"
          />
          <p className="text-xs text-text-3">
            Default: <code className="font-mono">http://localhost:8001/api/v1</code>.
            Requires a page reload to take effect.
          </p>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="rounded-lg bg-accent px-3.5 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Save
            </button>
            {saved && (
              <span className="inline-flex items-center gap-1 text-sm text-ok">
                <Check size={14} /> Saved
              </span>
            )}
          </div>
        </form>
      </section>

      {/* Connection facts */}
      <section className="surface-card">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">Connection details</h2>
        </div>
        <dl className="divide-y divide-line text-sm">
          {[
            ["Active base URL", API_BASE_URL],
            ["Transport", "REST / JSON"],
            ["Intelligence source", "Backend + ML pipeline"],
            ["Access mode", "Public (no authentication)"],
          ].map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-4 px-4 py-2.5"
            >
              <dt className="text-text-2">{label}</dt>
              <dd className="truncate font-mono text-xs text-text-1">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
};
