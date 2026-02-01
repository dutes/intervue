
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, Briefcase, Loader2, Play, Target, AlertCircle } from "lucide-react";

const ROUND_OPTIONS = [
    { value: 1, label: "Round 1: Screening", description: "Establish baseline fit and core experience." },
    { value: 2, label: "Round 2: Deep Dive", description: "Explore depth, impact, and technical decision-making." },
    { value: 3, label: "Round 3: Challenge", description: "Stress-test claims and assess judgment under pressure." },
];

export default function NewSession() {
    const navigate = useNavigate();
    const [jobSpec, setJobSpec] = useState("");
    const [cvText, setCvText] = useState("");
    const [provider, setProvider] = useState("openai");
    const [apiKey, setApiKey] = useState("");
    const [startRound, setStartRound] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        try {
            setLoading(true);
            const res = await fetch("http://127.0.0.1:8000/upload", {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Upload failed");
            const data = await res.json();
            setCvText(data.text_preview); // Or handle text_length note if needed
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const res = await fetch("http://127.0.0.1:8000/sessions/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    job_spec: jobSpec,
                    cv_text: cvText,
                    provider,
                    api_key: apiKey || undefined,
                    start_round: startRound
                }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to start session");
            }

            const data = await res.json();
            navigate(`/session/${data.session_id}`);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto pb-20">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">New Interview Session</h1>
                <p className="text-slate-400">Configure your target role and resume to generate a custom interview.</p>
            </div>

            {error && (
                <div className="mb-6 bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-3">
                    <AlertCircle className="w-5 h-5" />
                    <p>{error}</p>
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">

                {/* Job Spec */}
                <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                        <Briefcase className="w-4 h-4 text-indigo-400" />
                        Job Specification
                    </label>
                    <textarea
                        required
                        rows={4}
                        className="w-full bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all resize-none"
                        placeholder="Paste the job requirements, responsibilities, and qualifications..."
                        value={jobSpec}
                        onChange={(e) => setJobSpec(e.target.value)}
                    />
                </div>

                {/* CV Upload */}
                <div className="space-y-2">
                    <div className="flex justify-between items-center">
                        <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                            <FileText className="w-4 h-4 text-indigo-400" />
                            Your Resume / CV
                        </label>
                        <label className="cursor-pointer text-xs flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors">
                            <Upload className="w-3 h-3" />
                            Upload PDF/DOCX
                            <input type="file" className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={handleFileUpload} />
                        </label>
                    </div>
                    <textarea
                        required
                        rows={6}
                        className="w-full bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all resize-none"
                        placeholder="Paste your CV text or upload a file..."
                        value={cvText}
                        onChange={(e) => setCvText(e.target.value)}
                    />
                </div>

                {/* Round Selection */}
                <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                        <Target className="w-4 h-4 text-indigo-400" />
                        Starting Round
                    </label>
                    <div className="grid md:grid-cols-3 gap-3">
                        {ROUND_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => setStartRound(option.value)}
                                className={`text-left p-4 rounded-xl border transition-all ${startRound === option.value
                                        ? "bg-indigo-500/10 border-indigo-500/50 text-white shadow-lg shadow-indigo-500/10"
                                        : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700 hover:bg-slate-900"
                                    }`}
                            >
                                <div className="font-medium mb-1">{option.label}</div>
                                <div className="text-xs opacity-70 leading-relaxed">{option.description}</div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Settings */}
                <div className="grid md:grid-cols-2 gap-4 pt-4 border-t border-slate-800/50">
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-400">LLM Provider</label>
                        <div className="relative">
                            <select
                                value={provider}
                                onChange={(e) => setProvider(e.target.value)}
                                className="w-full appearance-none bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:ring-1 focus:ring-indigo-500 outline-none"
                            >
                                <option value="openai">OpenAI (GPT-4)</option>
                                <option value="gemini">Google (Gemini Pro)</option>
                                <option value="mock">Mock (Testing)</option>
                            </select>
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                            </div>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-400">API Key (Optional if env set)</label>
                        <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder="sk-..."
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:ring-1 focus:ring-indigo-500 outline-none"
                        />
                    </div>
                </div>

                <div className="pt-4 flex justify-end">
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20 flex items-center gap-2"
                    >
                        {loading ? (
                            <>Starting Session...</>
                        ) : (
                            <>
                                <Play className="w-4 h-4 fill-current" />
                                Start Interview
                            </>
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
}
