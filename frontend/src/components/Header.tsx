import { useEffect, useState } from "react";

import { getSettings } from "../api/client";
import { useTheme } from "../context/ThemeContext";
import { palette } from "../theme";
import type { AppSettings } from "../types/job";

function Header() {
  const { theme, toggleTheme } = useTheme();
  const colors = palette(theme);
  const [settings, setSettings] = useState<AppSettings | null>(null);

  useEffect(() => {
    let active = true;

    getSettings()
      .then((data) => {
        if (active) setSettings(data);
      })
      .catch(() => {
        // The settings endpoint is optional - the UI works without it.
      });

    return () => {
      active = false;
    };
  }, []);

  const badges: string[] = [];
  if (settings) {
    badges.push(`engine: ${settings.pipeline.engine}`);
    if (settings.features.subtitles) badges.push(`captions: ${settings.media.subtitle_format}`);
    if (settings.features.thumbnails) badges.push(`thumbnail: ${settings.media.thumbnail_template}`);
    if (settings.integrations.youtube_configured) badges.push("youtube: ready");
  }

  return (
    <div style={{ marginBottom: 30 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <h1 style={{ color: colors.text, margin: 0 }}>AI Content Factory</h1>

        <button
          onClick={toggleTheme}
          aria-label="Toggle dark mode"
          style={{
            padding: "8px 14px",
            borderRadius: 6,
            border: `1px solid ${colors.border}`,
            background: colors.surface,
            color: colors.text,
            cursor: "pointer",
          }}
        >
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </div>

      <p style={{ color: colors.muted }}>
        Generate YouTube Shorts automatically using AI.
      </p>

      {badges.length > 0 ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {badges.map((badge) => (
            <span
              key={badge}
              style={{
                fontSize: 12,
                padding: "3px 8px",
                borderRadius: 999,
                border: `1px solid ${colors.border}`,
                color: colors.muted,
                background: colors.surface,
              }}
            >
              {badge}
            </span>
          ))}
        </div>
      ) : null}

      <hr style={{ borderColor: colors.border }} />
    </div>
  );
}

export default Header;
