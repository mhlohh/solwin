import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  ShieldAlert,
  Users,
  LineChart,
  Settings,
  X,
  LucideIcon,
} from "lucide-react";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

const SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Overview",
    items: [{ label: "Dashboard", to: "/dashboard", icon: LayoutDashboard }],
  },
  {
    title: "Support",
    items: [{ label: "Conversations", to: "/conversations", icon: MessageSquare }],
  },
  {
    title: "Security",
    items: [
      { label: "Threats", to: "/threats", icon: ShieldAlert },
      { label: "Security analytics", to: "/analytics/security", icon: LineChart },
    ],
  },
  {
    title: "Analytics",
    items: [{ label: "Customer insights", to: "/insights/customer", icon: Users }],
  },
  {
    title: "System",
    items: [{ label: "Settings", to: "/settings", icon: Settings }],
  },
];

const NavLinks: React.FC<{ onNavigate?: () => void }> = ({ onNavigate }) => (
  <nav className="flex-1 overflow-y-auto px-3 py-4">
    {SECTIONS.map((section) => (
      <div key={section.title} className="mb-5">
        <p className="section-label mb-1.5 px-2.5">{section.title}</p>
        <div className="space-y-px">
          {section.items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                    isActive
                      ? "bg-accent-weak font-medium text-accent"
                      : "text-text-2 hover:bg-elevated hover:text-text-1"
                  }`
                }
              >
                <Icon size={16} className="shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>
      </div>
    ))}
  </nav>
);

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => (
  <>
    <aside className="sticky top-12 hidden h-[calc(100vh-3rem)] w-60 shrink-0 border-r border-line bg-card lg:block">
      <NavLinks />
    </aside>

    {isOpen && (
      <div className="fixed inset-0 z-40 lg:hidden">
        <div className="fixed inset-0 bg-black/40" onClick={onClose} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-card shadow-2">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <span className="text-sm font-semibold">Navigation</span>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-text-2 hover:bg-elevated hover:text-text-1"
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
          </div>
          <NavLinks onNavigate={onClose} />
        </div>
      </div>
    )}
  </>
);
