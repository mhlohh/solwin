# Skill: SOC Enterprise UI Design System

## Core Aesthetic
You are designing a top-tier Cybersecurity Operations Center (SOC) interface. The aesthetic is strictly "Dark Mode Enterprise" with high information density, deep backgrounds, and high-contrast status indicators.

## Typography & Layout Constraints
1. **Fonts:** Use `font-sans` for all standard text and `font-mono` exclusively for metadata, timestamps, IDs, and statuses.
2. **Spacing Grid:** Strictly adhere to Tailwind's 4px grid (`p-4`, `gap-6`, `mb-2`). Never use arbitrary pixel values (e.g., `h-[43px]`).
3. **Borders & Separation:** Use `border-surface-border` to define structural areas. Do not rely on varying background shades alone for separation.

## Interaction & "Antigravity" Styling Constraints
1. **Glass & Depth:** Background panels must use `bg-surface/40` or `bg-surface/60` combined with `backdrop-blur-md` for floating elements (headers, modals).
2. **Status Glows:** When indicating risk or active states, use the custom shadows defined in the config: `shadow-glow-sm`, `shadow-glow-lg`, or `shadow-glow-danger`.
3. **Transitions:** EVERY interactive element (button, link, table row) MUST have a smooth transition. Append `transition-colors duration-200` and explicit hover states (e.g., `hover:bg-surface-lighter/50`).
4. **Data Visualization:** Use the semantic risk colors strictly for their defined purpose: `text-emerald-400` (Low/Safe), `text-amber-500` (Medium/Warning), `text-rose-500` (Critical/Threat).

## Component Rules
- Never use inline styles. Use Tailwind utility classes exclusively.
- Use `lucide-react` for all icons. Size them consistently (usually `w-4 h-4` or `w-5 h-5`).
- Buttons must have focus states (`focus:outline-none focus:ring-2`).