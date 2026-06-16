import { X, FileText, ListChecks, Users, MessageSquareText, ClipboardList, Info } from "lucide-react";

const STEPS = [
    {
        Icon: FileText,
        title: "You provide the job spec and your CV",
        body: "Paste the role description and your résumé, and pick which round to start from.",
    },
    {
        Icon: ListChecks,
        title: "We build a tailored hiring rubric",
        body: "Intervue reads both and derives the competencies that actually matter for this role, weighted by importance.",
    },
    {
        Icon: Users,
        title: "A three-person panel interviews you",
        body: "A supportive, a neutral, and a challenging interviewer ask questions specific to your background and score each answer against the rubric. If an answer is thin, they probe deeper with a follow-up.",
    },
    {
        Icon: MessageSquareText,
        title: "You get instant coaching on every answer",
        body: "What worked, what to fix, a rewrite of your own answer, a model answer to aim for, and delivery feedback (length, pace, hedging).",
    },
    {
        Icon: ClipboardList,
        title: "A full report at the end",
        body: "Overall score, strengths and opportunities (with evidence from your answers), how you handled each interviewer, a competency breakdown, a 7-day plan, and the full transcript — exportable to PDF.",
    },
];

export default function HowItWorks({ open, onClose }: { open: boolean; onClose: () => void }) {
    if (!open) return null;
    return (
        <div
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto animate-in fade-in duration-200"
            onClick={onClose}
        >
            <div
                className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full my-8 p-6 md:p-8 animate-in slide-in-from-bottom-4 duration-300"
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    aria-label="Close"
                    className="absolute top-4 right-4 p-2 text-slate-500 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>

                <h2 className="font-display text-2xl font-bold tracking-tight text-white mb-1">How Intervue works</h2>
                <p className="text-sm text-slate-400 mb-6">A simulated interview panel that listens, probes, and coaches.</p>

                <ol className="space-y-4">
                    {STEPS.map(({ Icon, title, body }, i) => (
                        <li key={i} className="flex gap-4">
                            <span className="shrink-0 w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                                <Icon className="w-5 h-5 text-indigo-400" />
                            </span>
                            <div>
                                <p className="text-slate-100 font-medium">{i + 1}. {title}</p>
                                <p className="text-sm text-slate-400 mt-0.5 leading-relaxed">{body}</p>
                            </div>
                        </li>
                    ))}
                </ol>

                <div className="mt-6 pt-5 border-t border-slate-800 space-y-3">
                    <p className="text-sm text-slate-400">
                        <span className="text-slate-200 font-medium">Bring your own model.</span> Choose OpenAI, Anthropic (Claude),
                        Google (Gemini), a local model, or Mock. Your API key is used only for your session and never leaves your machine.
                    </p>
                    <p className="text-xs text-slate-500 flex items-start gap-2">
                        <Info className="w-4 h-4 shrink-0 mt-0.5 text-slate-500" />
                        Scores and feedback are AI estimates to guide your practice — not a real hiring decision.
                    </p>
                </div>
            </div>
        </div>
    );
}
