import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle, AlertCircle, BarChart2, Award, Briefcase, Download } from "lucide-react";

interface PersonaFeedback {
    persona: string;
    positives: string[];
    concerns: string[];
    next_step: string;
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
    report_paths: {
        competency_radar: string;
        score_over_time: string;
        persona_comparison: string;
    };
}

export default function InterviewReport() {
    const { id } = useParams<{ id: string }>();
    const [report, setReport] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;
        fetchReport();
    }, [id]);

    const fetchReport = async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/sessions/${id}/report`);
            if (!res.ok) throw new Error("Failed to load report");
            const data = await res.json();
            setReport(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-12 text-center text-slate-400">Generatng Interview Report...</div>;
    if (error) return <div className="p-12 text-center text-red-400">{error}</div>;
    if (!report) return null;

    // Helper to get image URL
    const getChartUrl = (filename: string) => {
        // Filename is absolute path from server, e.g. "data/reports/session_id/chart.png"
        // We mounted "/reports" to "data/reports".
        // So we need to construct "/reports/{session_id}/{filename_basename}"
        const basename = filename.split(/[\\/]/).pop();
        return `http://127.0.0.1:8000/reports/${id}/${basename}`;
    };

    return (
        <div className="max-w-4xl mx-auto pb-20 space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex justify-between items-end mb-4">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Interview Report</h1>
                    <p className="text-slate-400">Session ID: <span className="font-mono text-slate-500">{id?.slice(0, 8)}</span></p>
                </div>
                <div className="text-right">
                    <div className="text-sm text-slate-400 uppercase tracking-wider font-medium mb-1">Overall Score</div>
                    <div className={`text-5xl font-bold ${report.overall_score >= 80 ? 'text-emerald-400' : report.overall_score >= 60 ? 'text-indigo-400' : 'text-amber-400'}`}>
                        {report.overall_score}
                    </div>
                </div>
            </div>

            {/* Executive Summary Cards */}
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

            {/* Visual Analytics */}
            <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <h3 className="text-slate-200 font-medium mb-4 flex items-center gap-2">
                        <BarChart2 className="w-5 h-5 text-indigo-400" /> Competency Breakdown
                    </h3>
                    <div className="bg-white/5 rounded-xl p-4 flex items-center justify-center">
                        <img src={getChartUrl(report.report_paths.competency_radar)} alt="Competency Radar" className="max-h-64 object-contain" />
                    </div>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <h3 className="text-slate-200 font-medium mb-4 flex items-center gap-2">
                        <Briefcase className="w-5 h-5 text-indigo-400" /> Performance Over Time
                    </h3>
                    <div className="bg-white/5 rounded-xl p-4 flex items-center justify-center">
                        <img src={getChartUrl(report.report_paths.score_over_time)} alt="Score Trend" className="max-h-64 object-contain" />
                    </div>
                </div>
            </div>

            {/* Detailed Feedback */}
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

            <div className="flex justify-between pt-8 border-t border-slate-800">
                <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                    Back to Dashboard
                </Link>
                <button onClick={() => window.print()} className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg font-medium transition-colors">
                    <Download className="w-4 h-4" /> Save Report
                </button>
            </div>
        </div>
    );
}
