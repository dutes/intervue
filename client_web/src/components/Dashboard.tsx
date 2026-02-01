
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Play, Calendar, CheckCircle, ArrowRight } from "lucide-react";

interface Session {
    session_id: string;
    created_at: number;
    job_spec: string;
    status: string;
    overall_score?: number;
}

export default function Dashboard() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8000/sessions")
            .then((res) => res.json())
            .then((data) => {
                setSessions(data);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch sessions", err);
                setLoading(false);
            });
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <header className="flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">My Interviews</h1>
                    <p className="text-slate-400">Track your progress and review past performance.</p>
                </div>
                <Link
                    to="/new"
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 shadow-lg shadow-indigo-500/20"
                >
                    <Play className="w-4 h-4 fill-current" />
                    Start Practice
                </Link>
            </header>

            {sessions.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl bg-slate-900/30">
                    <div className="bg-slate-800/50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Play className="w-8 h-8 text-slate-400 ml-1" />
                    </div>
                    <h3 className="text-lg font-medium text-white mb-1">No sessions yet</h3>
                    <p className="text-slate-500 mb-6">Start your first interview practice today.</p>
                    <Link to="/new" className="text-indigo-400 hover:text-indigo-300 font-medium">Start now &rarr;</Link>
                </div>
            ) : (
                <div className="grid gap-4">
                    {sessions.map((session) => (
                        <Link
                            key={session.session_id}
                            to={`/session/${session.session_id}`}
                            className="group block bg-slate-900/50 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-5 transition-all"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex gap-4 items-start">
                                    <div className={`mt-1 w-10 h-10 rounded-full flex items-center justify-center ${session.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'
                                        }`}>
                                        {session.status === 'completed' ? <CheckCircle className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white text-lg group-hover:text-indigo-400 transition-colors">
                                            {session.job_spec || "Untitled Position"}
                                        </h3>
                                        <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                                            <span className="flex items-center gap-1.5">
                                                <Calendar className="w-3.5 h-3.5" />
                                                {new Date(session.created_at * 1000).toLocaleDateString()}
                                            </span>
                                            <span>•</span>
                                            <span className="capitalize">{session.status}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-6">
                                    {session.overall_score && (
                                        <div className="text-right">
                                            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-0.5">Score</p>
                                            <p className={`text-xl font-bold ${session.overall_score >= 8 ? 'text-emerald-400' :
                                                session.overall_score >= 6 ? 'text-amber-400' : 'text-red-400'
                                                }`}>
                                                {session.overall_score}/10
                                            </p>
                                        </div>
                                    )}
                                    <ArrowRight className="w-5 h-5 text-slate-600 group-hover:text-indigo-400 transform group-hover:translate-x-1 transition-all" />
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
