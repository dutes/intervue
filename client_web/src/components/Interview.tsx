import { useRef, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Send, User, Bot, Mic, Square, Maximize2, Minimize2 } from "lucide-react";

interface Question {
    question_id: string;
    text: string;
    round: string;
    persona: string;
}

interface Session {
    session_id: string;
    status: string;
    questions: any[];
    start_round: number;
}

export default function Interview() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [session, setSession] = useState<Session | null>(null);
    const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isRecording, setIsRecording] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const recognitionRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);



    useEffect(() => {
        if (!id) return;
        fetchSession();
    }, [id]);

    const fetchSession = async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/sessions/${id}`);
            if (!res.ok) throw new Error("Failed to load session");
            const data = await res.json();
            setSession(data);
            if (data.status === 'completed') {
                navigate(`/report/${id}`);
                setLoading(false);
            } else {
                // Determine if we need to fetch the next question
                // If it's a new session, yes. 
                // In a real app we might check if there's an unanswered question or just fetch next.
                await fetchNextQuestion();
            }
        } catch (err: any) {
            setError(err.message);
            setLoading(false);
        }
    };

    const fetchNextQuestion = async () => {
        try {
            setLoading(true);
            const res = await fetch(`http://127.0.0.1:8000/sessions/${id}/next_question`, { method: "POST" });
            if (!res.ok) {
                const err = await res.json();
                if (err.detail === "Interview already complete") {
                    finishSession();
                    return;
                }
                throw new Error(err.detail);
            }
            const data = await res.json();
            setCurrentQuestion(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const finishSession = async () => {
        try {
            setLoading(true);
            const res = await fetch(`http://127.0.0.1:8000/sessions/${id}/end`, { method: "POST" });
            await res.json();
            // setSummary(data.summary);
            // setFinished(true);
            // setSession(prev => prev ? { ...prev, status: 'completed' } : null);
            navigate(`/report/${id}`);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const submitAnswer = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!currentQuestion) return;

        setSubmitting(true);
        try {
            await fetch(`http://127.0.0.1:8000/sessions/${id}/answer`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question_id: currentQuestion.question_id,
                    answer_text: answer
                })
            });
            setAnswer("");
            await fetchNextQuestion();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    const toggleRecording = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    const startRecording = () => {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert("Speech recognition is not supported in this browser.");
            return;
        }

        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = 'en-US';

        recognitionRef.current.onstart = () => {
            setIsRecording(true);
        };

        recognitionRef.current.onend = () => {
            setIsRecording(false);
        };

        recognitionRef.current.onerror = (event: any) => {
            console.error("Speech recognition error", event.error);
            setIsRecording(false);
        };

        recognitionRef.current.onresult = (event: any) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            // Append to existing answer or replace? 
            // Usually simpler to just append or update current buffer if we want real-time.
            // But here we might overwrite user typing if mixing modes.
            // Let's just append final results to end of current text for simplicity
            if (finalTranscript) {
                setAnswer(prev => prev + (prev ? " " : "") + finalTranscript);
            }
        };

        recognitionRef.current.start();
    };

    const stopRecording = () => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
    };

    const toggleFullscreen = () => {
        if (!document.fullscreenElement) {
            containerRef.current?.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    };

    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, []);

    if (loading && !session) return <div className="p-12 text-center">Loading session...</div>;
    if (error) return <div className="p-12 text-center text-red-400">{error}</div>;


    return (
        <div ref={containerRef} className={`transition-all duration-300 ${isFullscreen ? 'fixed inset-0 z-50 bg-slate-950 p-8 flex flex-col justify-center' : 'max-w-4xl mx-auto grid gap-6 pb-20'}`}>
            {/* Header */}
            <div className={`flex items-center justify-between ${isFullscreen ? 'mb-8 max-w-4xl mx-auto w-full' : ''}`}>
                <div className="flex items-center gap-3">
                    <div className="bg-indigo-500/10 p-2 rounded-lg">
                        <Bot className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <p className="text-sm text-indigo-400 font-medium">AI Interviewer</p>
                        <p className="text-xs text-slate-500 uppercase tracking-wider">
                            {currentQuestion?.round} • {currentQuestion?.persona}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-sm text-slate-500">
                        <span className="font-mono text-slate-400">{id?.slice(0, 8)}</span>
                    </div>
                    <button
                        onClick={toggleFullscreen}
                        className="p-2 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                        title={isFullscreen ? "Exit Immersive Mode" : "Enter Immersive Mode"}
                    >
                        {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
                    </button>
                </div>
            </div>

            {/* Chat Area */}
            <div className={`bg-slate-900/50 border border-slate-800 rounded-2xl p-6 md:p-10 flex flex-col justify-center shadow-inner relative overflow-hidden ${isFullscreen ? 'flex-1 max-w-4xl mx-auto w-full mb-8' : 'min-h-[300px]'}`}>
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-50"></div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center gap-4 text-slate-500 animate-pulse">
                        <Bot className="w-10 h-10 opacity-50" />
                        <p>Generating next question...</p>
                    </div>
                ) : (
                    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
                        <h3 className="text-2xl md:text-3xl font-medium text-slate-100 leading-relaxed">
                            {currentQuestion?.text}
                        </h3>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className={isFullscreen ? 'max-w-4xl mx-auto w-full' : ''}>
                <form onSubmit={submitAnswer} className="relative mt-4">
                    <div className="absolute top-4 left-4">
                        <User className="w-5 h-5 text-slate-500" />
                    </div>
                    <textarea
                        autoFocus
                        rows={4}
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.ctrlKey) submitAnswer(e);
                        }}
                        disabled={submitting || loading}
                        placeholder="Type your answer here... (Ctrl+Enter to submit)"
                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl pl-12 pr-4 py-4 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all resize-none shadow-xl"
                    />
                    <div className="absolute bottom-4 right-4 flex gap-3">
                        <button
                            type="button"
                            onClick={toggleRecording}
                            className={`p-2.5 rounded-xl transition-all ${isRecording
                                ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 animate-pulse'
                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                }`}
                            title={isRecording ? "Stop Recording" : "Start Voice Input"}
                        >
                            {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
                        </button>
                        <button
                            type="submit"
                            disabled={!answer.trim() || submitting || loading}
                            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
