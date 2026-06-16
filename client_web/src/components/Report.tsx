import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle, AlertCircle, BarChart2, Award, Briefcase, Download, TrendingUp, CalendarDays, Smile, Scale, Flame, Users, MessageSquareText, ChevronDown } from "lucide-react";
import ScoreRing from "./ScoreRing";
import { scoreTier, scoreTextClass, scoreStroke } from "../lib/score";
import { apiUrl } from "../lib/api";

interface PersonaFeedback {
    persona: string;
    positives: string[];
    concerns: string[];
    next_step: string;
}

interface TranscriptEntry {
    question_id: string;
    question: string;
    round: string;
    competency: string;
    anchor: string;
    answer: string;
    score: number | null;
    star_summary: string;
    strengths: string[];
    improvements: string[];
    rewrite: string;
    delivery_notes?: string[];
    ideal_answer?: string;
}

interface PracticeDay {
    day: string;
    focus: string;
    task: string;
}

interface ReportData {
    session_id: string;
    overall_score: number;
    competency_averages: Record<string, number>;
    transcript?: TranscriptEntry[];
    strengths: string[];
    weaknesses: string[];
    overall_scores: number[];
    persona_averages: Record<string, number>;
    persona_feedback: PersonaFeedback[];
    practice_plan_7_day: PracticeDay[];
    report_paths: {
        competency_radar: string;
        score_over_time: string;
    };
}

const PERSONA_META: Record<string, { label: string; Icon: typeof Smile; color: string; blurb: string }> = {
    positive: { label: "The Supporter", Icon: Smile, color: "#34d399", blurb: "Warm and encouraging — drew out your best." },
    neutral: { label: "The Evaluator", Icon: Scale, color: "#6366f1", blurb: "Balanced and evidence-focused." },
    hostile: { label: "The Challenger", Icon: Flame, color: "#f87171", blurb: "Skeptical and probing — pressure-tested you." },
};

const PERSONA_ORDER = ["positive", "neutral", "hostile"];

function panelInsight(pa: Record<string, number>): string | null {
    const pos = pa.positive;
    const hos = pa.hostile;
    if (pos == null || hos == null) return null;
    const gap = Math.round(pos - hos);
    if (gap >= 15) return `You scored ${gap} points higher with a supportive interviewer than a hostile one — practise staying sharp under pressure.`;
    if (gap <= -15) return `You performed ${Math.abs(gap)} points better under a hostile interviewer than a friendly one — you rise to a challenge.`;
    return "Your performance held steady across friendly and hostile interviewers — a sign of composure under pressure.";
}

// Color the hiring verdict pill. "No Hire" must be checked before "Hire".
function verdictClass(nextStep: string): string {
    const s = (nextStep || "").toLowerCase();
    if (s.includes("no")) return "text-danger border-danger/30 bg-danger/10";
    if (s.includes("hire")) return "text-success border-success/30 bg-success/10";
    return "text-warn border-warn/30 bg-warn/10";
}

export default function InterviewReport() {
    const { id } = useParams<{ id: string }>();
    const [report, setReport] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    const [openQuestions, setOpenQuestions] = useState<Record<string, boolean>>({});
    const [transcriptOpen, setTranscriptOpen] = useState(false);

    const toggleQuestion = (qid: string) =>
        setOpenQuestions((prev) => ({ ...prev, [qid]: !prev[qid] }));

    useEffect(() => {
        if (!id) return;
        fetchReport();
    }, [id]);

    const fetchReport = async () => {
        try {
            const res = await fetch(apiUrl(`/sessions/${id}/report`));
            if (!res.ok) throw new Error("Failed to load report");
            const data = await res.json();
            setReport(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-12 text-center text-slate-400">Generating Interview Report...</div>;
    if (error) return <div className="p-12 text-center text-red-400">{error}</div>;
    if (!report) return null;

    const getChartUrl = (filename: string) => {
        const basename = filename.split(/[\\/]/).pop();
        return apiUrl(`/reports/${id}/${basename}`);
    };

    return (
        <div className="max-w-4xl mx-auto pb-20 space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end mb-4">
                <div>
                    <h1 className="font-display text-4xl font-bold tracking-tight text-white mb-2">Interview Report</h1>
                    <p className="text-slate-400">Session ID: <span className="font-mono text-slate-500">{id?.slice(0, 8)}</span></p>
                </div>
                <div className="flex flex-col items-center">
                    <div className="text-sm text-slate-400 uppercase tracking-wider font-medium mb-2">Overall Score</div>
                    <ScoreRing value={report.overall_score} size={96} stroke={8} caption="/ 100" />
                </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <h3 className="text-emerald-400 font-medium mb-4 flex items-center gap-2">
                        <Award className="w-5 h-5" /> Top Strengths
                    </h3>
                    <ul className="space-y-3">
                        {report.strengths.map((s, i) => (
                            <li key={i} className="flex gap-3 text-slate-300 text-sm">
                                <CheckCircle className="w-4 h-4 text-emerald-500/50 flex-shrink-0 mt-0.5" />
                                {s}
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <h3 className="text-amber-400 font-medium mb-4 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" /> Opportunity Areas
                    </h3>
                    <ul className="space-y-3">
                        {report.weaknesses.map((w, i) => (
                            <li key={i} className="flex gap-3 text-slate-300 text-sm">
                                <AlertCircle className="w-4 h-4 text-amber-500/50 flex-shrink-0 mt-0.5" />
                                {w}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <h3 className="text-slate-200 font-medium mb-4 flex items-center gap-2">
                        <BarChart2 className="w-5 h-5 text-indigo-400" /> Competency Radar
                    </h3>
                    <div
                        className="bg-white/5 rounded-xl p-4 flex items-center justify-center cursor-pointer hover:bg-white/10 transition-colors"
                        onClick={() => setSelectedImage(getChartUrl(report.report_paths.competency_radar))}
                    >
                        <img src={getChartUrl(report.report_paths.competency_radar)} alt="Competency Radar" className="max-h-64 object-contain" />
                    </div>
                    <p className="print:hidden text-xs text-center text-slate-500 mt-2">Click to expand</p>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <h3 className="text-slate-200 font-medium mb-4 flex items-center gap-2">
                        <Briefcase className="w-5 h-5 text-indigo-400" /> Performance Over Time
                    </h3>
                    <div
                        className="bg-white/5 rounded-xl p-4 flex items-center justify-center cursor-pointer hover:bg-white/10 transition-colors"
                        onClick={() => setSelectedImage(getChartUrl(report.report_paths.score_over_time))}
                    >
                        <img src={getChartUrl(report.report_paths.score_over_time)} alt="Score Trend" className="max-h-64 object-contain" />
                    </div>
                    <p className="print:hidden text-xs text-center text-slate-500 mt-2">Click to expand</p>
                </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-white font-medium mb-1 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-indigo-400" /> Competency Breakdown
                </h3>
                <p className="text-xs text-slate-500 mb-4">Your average score per competency, strongest first.</p>
                <div className="grid gap-3">
                    {Object.entries(report.competency_averages || {})
                        .sort(([, a], [, b]) => b - a)
                        .map(([name, score]) => {
                            const tier = scoreTier(score);
                            return (
                                <div key={name} className="flex items-center gap-3">
                                    <span className="text-sm text-slate-300 w-56 shrink-0 truncate" title={name}>{name}</span>
                                    <div className="flex-1 h-2.5 rounded-full bg-slate-800 overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all duration-700"
                                            style={{ width: `${Math.max(0, Math.min(100, score))}%`, backgroundColor: scoreStroke[tier] }}
                                        />
                                    </div>
                                    <span className={`text-sm font-semibold w-10 text-right ${scoreTextClass[tier]}`}>{Math.round(score)}</span>
                                </div>
                            );
                        })}
                </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-white font-medium mb-1 flex items-center gap-2">
                    <Users className="w-5 h-5 text-indigo-400" /> How You Handled the Panel
                </h3>
                <p className="text-xs text-slate-500 mb-4">Your average score with each interviewer style.</p>
                <div className="grid sm:grid-cols-3 gap-4">
                    {PERSONA_ORDER.filter((p) => report.persona_averages?.[p] != null).map((p) => {
                        const meta = PERSONA_META[p];
                        const score = report.persona_averages[p];
                        const Icon = meta.Icon;
                        return (
                            <div key={p} className="border border-slate-800 rounded-xl p-4 bg-slate-950/40 flex flex-col items-center text-center">
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: `${meta.color}1a` }}>
                                        <Icon className="w-4 h-4" style={{ color: meta.color }} />
                                    </span>
                                    <span className="text-sm font-semibold text-slate-200">{meta.label}</span>
                                </div>
                                <ScoreRing value={score} caption="/ 100" />
                                <p className="text-xs text-slate-500 mt-3 leading-relaxed">{meta.blurb}</p>
                            </div>
                        );
                    })}
                </div>
                {panelInsight(report.persona_averages || {}) && (
                    <div className="mt-4 text-sm text-slate-300 bg-indigo-500/10 border border-indigo-500/20 rounded-xl px-4 py-3">
                        {panelInsight(report.persona_averages || {})}
                    </div>
                )}

                {report.persona_feedback && report.persona_feedback.length > 0 && (
                    <div className="mt-6 pt-6 border-t border-slate-800">
                        <h4 className="text-sm font-semibold text-slate-200 mb-1">Hiring verdict</h4>
                        <p className="text-xs text-slate-500 mb-3">The interviewer's recommendation and any remaining concerns.</p>
                        <div className="grid gap-3">
                            {report.persona_feedback.map((feedback, idx) => (
                                <div key={idx} className="border border-slate-800 rounded-xl p-4 bg-slate-950/40">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 bg-indigo-500/10 px-2 py-1 rounded">{feedback.persona}</span>
                                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${verdictClass(feedback.next_step)}`}>{feedback.next_step}</span>
                                    </div>
                                    {feedback.concerns.length > 0 && (
                                        <ul className="text-sm text-slate-300 space-y-1 mt-3">
                                            {feedback.concerns.map((c, i) => <li key={i}>• {c}</li>)}
                                        </ul>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                    <CalendarDays className="w-5 h-5 text-indigo-400" /> 7-Day Practice Plan
                </h3>
                <div className="grid gap-3">
                    {(report.practice_plan_7_day || []).map((item, idx) => (
                        <div key={idx} className="border border-slate-800 rounded-xl p-4 bg-slate-950/40">
                            <div className="flex items-center justify-between">
                                <p className="text-sm text-slate-200 font-medium">{item.day}</p>
                                <p className="text-xs text-indigo-300">{item.focus}</p>
                            </div>
                            <p className="text-sm text-slate-400 mt-2">{item.task}</p>
                        </div>
                    ))}
                </div>
            </div>

            {report.transcript && report.transcript.length > 0 && (
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden">
                    <button
                        type="button"
                        onClick={() => setTranscriptOpen((o) => !o)}
                        className="w-full flex items-center justify-between gap-3 px-6 py-4 text-left hover:bg-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
                    >
                        <span className="flex items-center gap-2 text-white font-medium">
                            <MessageSquareText className="w-5 h-5 text-indigo-400" /> Interview Transcript
                            <span className="text-xs text-slate-500 font-normal">({report.transcript.length} questions)</span>
                        </span>
                        <ChevronDown className={`print:hidden w-5 h-5 text-slate-500 transition-transform ${transcriptOpen ? "rotate-180" : ""}`} />
                    </button>
                    <div className={`${transcriptOpen ? "block" : "hidden"} print:block px-6 pb-6`}>
                        <p className="text-xs text-slate-500 mb-4">Your answers with per-question feedback and a suggested rewrite.</p>
                        <div className="space-y-3">
                            {report.transcript.map((t, idx) => {
                                const open = !!openQuestions[t.question_id];
                                const tier = t.score != null ? scoreTier(t.score) : null;
                                return (
                                    <div key={t.question_id} className="border border-slate-800 rounded-xl bg-slate-950/40 overflow-hidden break-inside-avoid">
                                        <button
                                            type="button"
                                            onClick={() => toggleQuestion(t.question_id)}
                                            className="w-full flex items-center gap-3 text-left px-4 py-3 hover:bg-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
                                        >
                                            <span className="text-xs font-mono text-slate-500 w-7 shrink-0">Q{idx + 1}</span>
                                            <span className="flex-1 text-sm text-slate-200">{t.question}</span>
                                            {t.score != null && tier && (
                                                <span className={`text-sm font-semibold ${scoreTextClass[tier]}`}>{Math.round(t.score)}</span>
                                            )}
                                            <ChevronDown className={`print:hidden w-4 h-4 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`} />
                                        </button>
                                        <div className={`${open ? "block" : "hidden"} print:block px-4 pb-4 pt-4 space-y-4 border-t border-slate-800/60`}>
                                            {(t.competency || t.anchor) && (
                                                <div className="flex flex-wrap items-center gap-2">
                                                    {t.competency && (
                                                        <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">{t.competency}</span>
                                                    )}
                                                    {t.anchor && <span className="text-xs text-slate-500 italic">Probing: “{t.anchor}”</span>}
                                                </div>
                                            )}
                                            <div>
                                                <p className="text-xs uppercase text-slate-500 mb-1">Your answer</p>
                                                <p className="text-sm text-slate-300 whitespace-pre-wrap">{t.answer}</p>
                                            </div>
                                            {t.star_summary && <p className="text-xs text-slate-400">STAR: {t.star_summary}</p>}
                                            {t.delivery_notes && t.delivery_notes.length > 0 && (
                                                <div>
                                                    <p className="text-xs uppercase text-sky-400 mb-1">Delivery</p>
                                                    <ul className="text-sm text-slate-300 space-y-1">
                                                        {t.delivery_notes.map((n, i) => <li key={i}>• {n}</li>)}
                                                    </ul>
                                                </div>
                                            )}
                                            <div className="grid md:grid-cols-2 gap-4">
                                                {t.strengths.length > 0 && (
                                                    <div>
                                                        <p className="text-xs uppercase text-emerald-400 mb-1">Strengths</p>
                                                        <ul className="text-sm text-slate-300 space-y-1">
                                                            {t.strengths.map((s, i) => <li key={i}>• {s}</li>)}
                                                        </ul>
                                                    </div>
                                                )}
                                                {t.improvements.length > 0 && (
                                                    <div>
                                                        <p className="text-xs uppercase text-amber-400 mb-1">Improve</p>
                                                        <ul className="text-sm text-slate-300 space-y-1">
                                                            {t.improvements.map((s, i) => <li key={i}>• {s}</li>)}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            {t.rewrite && (
                                                <div>
                                                    <p className="text-xs uppercase text-indigo-400 mb-1">Your answer, rewritten</p>
                                                    <pre className="text-xs whitespace-pre-wrap font-sans bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-300">{t.rewrite}</pre>
                                                </div>
                                            )}
                                            {t.ideal_answer && (
                                                <div>
                                                    <p className="text-xs uppercase text-emerald-400 mb-1">Model answer</p>
                                                    <pre className="text-xs whitespace-pre-wrap font-sans bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-300">{t.ideal_answer}</pre>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            <div className="print:hidden flex justify-between pt-8 border-t border-slate-800">
                <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                    Back to Dashboard
                </Link>
                <button onClick={() => window.print()} className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg font-medium transition-colors">
                    <Download className="w-4 h-4" /> Save Report
                </button>
            </div>

            {selectedImage && (
                <div
                    className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200"
                    onClick={() => setSelectedImage(null)}
                >
                    <div className="relative max-w-5xl max-h-screen">
                        <img
                            src={selectedImage}
                            alt="Expanded view"
                            className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl"
                        />
                        <button
                            className="absolute -top-10 right-0 text-white hover:text-slate-300"
                            onClick={() => setSelectedImage(null)}
                        >
                            Close
                        </button>
                        <div className="absolute top-2 right-2 bg-black/50 text-white px-2 py-1 rounded text-xs pointer-events-none">
                            Click anywhere to close
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
