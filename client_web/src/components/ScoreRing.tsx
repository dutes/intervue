import { scoreTier, scoreStroke } from "../lib/score";

interface ScoreRingProps {
    /** Score on a 0-100 scale. */
    value: number;
    /** Outer diameter in px. */
    size?: number;
    /** Stroke thickness in px. */
    stroke?: number;
    /** Optional caption shown under the number (e.g. "/ 100"). */
    caption?: string;
}

export default function ScoreRing({ value, size = 64, stroke = 6, caption }: ScoreRingProps) {
    const clamped = Math.max(0, Math.min(100, value));
    const radius = (size - stroke) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - clamped / 100);
    const color = scoreStroke[scoreTier(clamped)];

    return (
        <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="-rotate-90">
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={stroke}
                    className="text-slate-800"
                />
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke={color}
                    strokeWidth={stroke}
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    style={{ transition: "stroke-dashoffset 600ms ease" }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
                <span className="font-display font-bold text-slate-100" style={{ fontSize: size * 0.3 }}>
                    {Math.round(clamped)}
                </span>
                {caption && <span className="text-[9px] text-slate-500 mt-0.5">{caption}</span>}
            </div>
        </div>
    );
}
