import React from "react";
import { useNavigate } from "react-router-dom";
import { Menu, Moon, Sun } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { SearchBar } from "../common/SearchBar";

interface TopbarProps {
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleGlobalSearch = (query: string) => {
    if (!query.trim()) return;
    navigate(`/conversations?search=${encodeURIComponent(query)}`);
  };

  return (
    <header className="sticky top-0 z-30 flex h-12 items-center gap-3 border-b border-line bg-card px-4 sm:px-6">
      <button
        onClick={onToggleSidebar}
        className="rounded-lg p-1.5 text-text-2 hover:bg-elevated hover:text-text-1 lg:hidden"
        aria-label="Toggle navigation"
      >
        <Menu size={18} />
      </button>

      <button
        onClick={() => navigate("/dashboard")}
        className="flex items-center gap-2 select-none"
      >
        <span className="text-sm font-semibold tracking-tight text-text-1">Solwin</span>
        <span className="hidden rounded border border-line bg-elevated px-1.5 py-0.5 text-[11px] text-text-2 sm:inline">
          Support intelligence
        </span>
      </button>

      <div className="mx-auto w-full max-w-md flex-1 px-2">
        <SearchBar
          placeholder="Search conversations…"
          onChange={handleGlobalSearch}
        />
      </div>

      <button
        onClick={toggleTheme}
        className="rounded-lg p-2 text-text-2 hover:bg-elevated hover:text-text-1"
        aria-label="Toggle theme"
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  );
};
