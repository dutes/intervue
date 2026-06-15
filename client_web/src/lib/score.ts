// Single source of truth for how a 0-100 score maps to a color.
// Previously the 80/60 thresholds were duplicated across Dashboard and Interview.

export type ScoreTier = "good" | "ok" | "bad";

export function scoreTier(score: number): ScoreTier {
    if (score >= 80) return "good";
    if (score >= 60) return "ok";
    return "bad";
}

// Tailwind text color class per tier (semantic tokens from index.css @theme).
export const scoreTextClass: Record<ScoreTier, string> = {
    good: "text-success",
    ok: "text-warn",
    bad: "text-danger",
};

// Hex stroke per tier for SVG rings (must match the @theme tokens).
export const scoreStroke: Record<ScoreTier, string> = {
    good: "#34d399",
    ok: "#fbbf24",
    bad: "#f87171",
};
