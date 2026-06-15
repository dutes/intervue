import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle, AlertCircle, BarChart2, Award, Briefcase, Download, TrendingUp, CalendarDays, Smile, Scale, Flame, Users } from "lucide-react";
import ScoreRing from "./ScoreRing";
import { scoreTier, scoreTextClass, scoreStroke } from "../lib/score";
import { apiUrl } from "../lib/api";

interface PersonaFeedback {
    persona: string;
    positives: string[];
    concerns: string[];
    next_step: string;
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

export default function InterviewReport() {
    const { id } = useParams<{ id: string }>();
    const [report, setReport] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

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

            <div className="space-y-6">
                <h3 className="text-xl font-bold text-white">Interviewer Feedback</h3>
                <div className="grid gap-6">
                    {report.persona_feedback.map((feedback, idx) => (
                        <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded">
                                        {feedback.persona}
                                    </span>
                                    <div className="text-slate-400 text-sm mt-2">{feedback.next_step}</div>
                                </div>
                            </div>

                            <div className="grid md:grid-cols-2 gap-6 mt-4">
                                <div>
                                    <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Positives</h4>
                                    <ul className="space-y-1">
                                        {feedback.positives.map((p, i) => (
                                            <li key={i} className="text-sm text-slate-300">• {p}</li>
                                        ))}
                                    </ul>
                                </div>
                                <div>
                                    <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Concerns</h4>
                                    <ul className="space-y-1">
                                        {feedback.concerns.map((c, i) => (
                                            <li key={i} className="text-sm text-slate-300">• {c}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

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
