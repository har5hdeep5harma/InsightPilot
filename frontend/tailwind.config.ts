import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./types/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif"
        ],
        mono: [
          "JetBrains Mono",
          "SFMono-Regular",
          "Consolas",
          "Liberation Mono",
          "monospace"
        ]
      },
      fontSize: {
        "display-lg": ["3.5rem", { lineHeight: "1", letterSpacing: "0" }],
        "display-md": ["2.75rem", { lineHeight: "1.05", letterSpacing: "0" }],
        "heading-lg": ["2rem", { lineHeight: "1.15", letterSpacing: "0" }],
        "heading-md": ["1.5rem", { lineHeight: "1.25", letterSpacing: "0" }],
        "heading-sm": ["1.125rem", { lineHeight: "1.35", letterSpacing: "0" }],
        body: ["0.9375rem", { lineHeight: "1.7", letterSpacing: "0" }],
        "body-sm": ["0.8125rem", { lineHeight: "1.6", letterSpacing: "0" }],
        caption: ["0.75rem", { lineHeight: "1.45", letterSpacing: "0" }]
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))"
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))"
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))"
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))"
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))"
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))"
        },
        surface: {
          DEFAULT: "hsl(var(--surface))",
          raised: "hsl(var(--surface-raised))",
          subtle: "hsl(var(--surface-subtle))",
          inverse: "hsl(var(--surface-inverse))"
        },
        graphite: {
          950: "hsl(var(--graphite-950))",
          900: "hsl(var(--graphite-900))",
          800: "hsl(var(--graphite-800))"
        },
        insight: {
          low: "hsl(var(--insight-low))",
          medium: "hsl(var(--insight-medium))",
          high: "hsl(var(--insight-high))"
        }
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)"
      },
      boxShadow: {
        hairline: "0 0 0 1px hsl(var(--border))",
        panel: "0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.035)",
        "panel-hover":
          "0 1px 2px rgba(15, 23, 42, 0.05), 0 12px 36px rgba(15, 23, 42, 0.06)"
      },
      transitionTimingFunction: {
        productive: "cubic-bezier(0.2, 0, 0, 1)"
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
};

export default config;
