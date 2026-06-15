import { Loader2, Brain, MessageSquareText } from "lucide-react";

export type ThinkingPhase = "evaluating" | "generating";

const CONFIG: Record<ThinkingPhase, { Icon: typeof Brain; label: string; sub: string }> = {
    evaluating: {
        Icon: Brain,
        label: "Evaluating your answer",
        sub: "Scoring it against the rubric…",
    },
    generating: {
        Icon: MessageSquareText,
        label: "Preparing the next question",
        sub: "Tailoring it to what you just said…",
    },
};

function Dots() {
    return (
        <span className="inline-flex gap-0.5">
            {[0, 1, 2].map((i) => (
                <span
                    key={i}
                    className="w-1 h-1 rounded-full bg-indigo-400 animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }}
                />
            ))}
        </span>
    );
}

export default function ThinkingIndicator({ phase }: { phase: ThinkingPhase }) {
    const cfg = CONFIG[phase];
    const Icon = cfg.Icon;
    return (
        <div className="flex flex-col items-center justify-center gap-5 py-4 animate-in fade-in duration-300">
            <div className="relative w-16 h-16 flex items-center justify-center">
                <Loader2 className="w-16 h-16 absolute animate-spin text-indigo-500/25" />
                <span className="absolute w-16 h-16 rounded-full bg-indigo-500/10 animate-ping" />
                <Icon className="w-7 h-7 text-indigo-400" />
            </div>
            <div className="text-center">
                <p className="font-display text-lg text-slate-200 flex items-center justify-center gap-1.5">
                    {cfg.label}
                    <Dots />
                </p>
                <p className="text-xs text-slate-500 mt-1">{cfg.sub}</p>
            </div>
        </div>
    );
}
