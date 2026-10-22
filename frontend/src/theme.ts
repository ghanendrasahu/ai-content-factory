import type { Theme } from "./types/job";

export interface Palette {
  background: string;
  surface: string;
  border: string;
  text: string;
  muted: string;
  accent: string;
  danger: string;
  success: string;
}

const light: Palette = {
  background: "#f6f7f9",
  surface: "#ffffff",
  border: "#dfe3e8",
  text: "#111827",
  muted: "#6b7280",
  accent: "#2563eb",
  danger: "#dc2626",
  success: "#16a34a",
};

const dark: Palette = {
  background: "#0b1020",
  surface: "#151a2c",
  border: "#2a3147",
  text: "#e5e7eb",
  muted: "#9aa3b2",
  accent: "#60a5fa",
  danger: "#f87171",
  success: "#4ade80",
};

export function palette(theme: Theme): Palette {
  return theme === "dark" ? dark : light;
}
