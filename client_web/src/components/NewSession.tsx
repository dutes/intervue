
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, Briefcase, Loader2, Play } from "lucide-react";

export default function NewSession() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [jobSpec, setJobSpec] = useState("");
    const [cvText, setCvText] = useState("");
    const [provider, setProvider] = useState("openai");
    const [apiKey, setApiKey] = useState("");

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        setLoading(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/upload", {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Upload failed");
            const data = await res.json();
            setCvText(data.text_preview); // In a real app we might store a reference or the full text
        } catch (err) {
            console.error(err);
            setError("Failed to parse file. Please try pasting text.");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const payload = {
            job_spec: jobSpec,
            cv_text: cvText,
            provider,
            api_key: apiKey || undefined,
            start_round: 1
        };

        try {
            // If user provides key, we might want to set it in env or pass it. 
            // The backend expects it in the body.
            const res = await fetch("http://127.0.0.1:8000/sessions/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to start session");
            }

            const data = await res.json();
            navigate(`/session/${data.session_id}`);
        } catch (err: any) {
            setError(err.message);
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">New Interview Session</h1>
                <p className="text-slate-400">Configure your target role and resume to generate a custom interview.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-200 text-sm flex items-start gap-3">
                        <div className="mt-0.5"><Loader2 className="w-4 h-4 animate-spin" /></div> {/* Reuse icon or Alert */}
                        {error}
                    </div>
                )}

                <div className="space-y-4">
                    <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-xl">
                        <label className="block text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                            <Briefcase className="w-4 h-4 text-indigo-400" />
                            Job Specification
                        </label>
                        <textarea
                            required
                            rows={4}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all placeholder:text-slate-600"
                            placeholder="Paste the job requirements, responsibilities, and qualifications..."
                            value={jobSpec}
                            onChange={(e) => setJobSpec(e.target.value)}
                        />
                    </div>

                    <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-xl">
                        <div className="flex items-center justify-between mb-3">
                            <label className="block text-sm font-medium text-slate-300 flex items-center gap-2">
                                <FileText className="w-4 h-4 text-indigo-400" />
                                Your Resume / CV
                            </label>
                            <div className="relative">
                                <input
                                    type="file"
                                    id="cv-upload"
                                    className="hidden"
                                    accept=".pdf,.docx,.txt"
                                    onChange={handleFileUpload}
                                    disabled={loading}
                                />
                                <label
                                    htmlFor="cv-upload"
                                    className="cursor-pointer text-xs font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5 px-3 py-1.5 rounded-md hover:bg-indigo-500/10 transition-colors"
                                >
                                    <Upload className="w-3.5 h-3.5" />
                                    Upload PDF/DOCX
                                </label>
                            </div>
                        </div>

                        <textarea
                            required
                            rows={6}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all placeholder:text-slate-600"
                            placeholder="Paste your CV text or upload a file..."
                            value={cvText}
                            onChange={(e) => setCvText(e.target.value)}
                        />
                    </div>

                    <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-xl grid grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                LLM Provider
                            </label>
                            <select
                                value={provider}
                                onChange={(e) => setProvider(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 outline-none"
                            >
                                <option value="openai">OpenAI (GPT-4)</option>
                                <option value="gemini">Gemini Pro</option>
                                <option value="mock">Mock (Demo)</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                API Key <span className="text-slate-500 text-xs font-normal">(Optional if env set)</span>
                            </label>
                            <input
                                type="password"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                placeholder="sk-..."
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 outline-none placeholder:text-slate-700"
                            />
                        </div>
                    </div>
                </div>

                <div className="flex justify-end pt-4">
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-medium transition-all flex items-center gap-2 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 hover:-translate-y-0.5"
                    >
                        {loading ? (
                            <><Loader2 className="w-5 h-5 animate-spin" /> Starting Session...</>
                        ) : (
                            <><Play className="w-5 h-5 fill-current" /> Start Interview</>
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
}
