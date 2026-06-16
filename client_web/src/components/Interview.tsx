import { useRef, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Send, User, Bot, Mic, Square, Maximize2, Minimize2, Volume2, VolumeX } from "lucide-react";
import ScoreRing from "./ScoreRing";
import ThinkingIndicator, { type ThinkingPhase } from "./ThinkingIndicator";
import { apiUrl } from "../lib/api";
import { useQuestionVoice } from "../lib/useQuestionVoice";

interface Question {
    question_id: string;
    text: string;
    round: string;
    persona: string;
    anchor?: string;
    competency?: string;
    number?: number;
    total?: number;
}

interface Session {
    session_id: string;
    status: string;
    questions: any[];
    start_round: number;
}

interface Coaching {
    strengths: string[];
    improvements: string[];
    rewrite: string;
}

interface StarFeedback {
    star_complete: boolean;
    metrics_present: boolean;
    specificity: number;
    summary: string;
}

interface Delivery {
    word_count: number;
    wpm: number | null;
    hedge_count: number;
    used_voice: boolean;
    notes: string[];
}

interface AnswerFeedback {
    average_overall_score: number;
    competency_scores: Record<string, number>;
    star_feedback: StarFeedback;
    coaching: Coaching;
    delivery?: Delivery;
}

export default function Interview() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [session, setSession] = useState<Session | null>(null);
    const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [phase, setPhase] = useState<ThinkingPhase | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isRecording, setIsRecording] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [latestFeedback, setLatestFeedback] = useState<AnswerFeedback | null>(null);
    const recognitionRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    // Delivery timing: when the candidate started composing, and whether they used voice.
    const answerStartRef = useRef<number | null>(null);
    const usedVoiceRef = useRef<boolean>(false);
    const { supported: voiceSupported, enabled: voiceEnabled, toggle: toggleVoice, speak, stop: stopSpeaking } = useQuestionVoice();

    // Read each new question aloud (once per question), unless we're mid "thinking".
    useEffect(() => {
        if (currentQuestion?.text && !phase) {
            speak(currentQuestion.text, currentQuestion.persona);
        }
        // Reset delivery timing for the new question.
        answerStartRef.current = null;
        usedVoiceRef.current = false;
        // Only re-run when the question changes, not when speak()/phase identity changes.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentQuestion?.question_id]);

    useEffect(() => {
        if (!id) return;
        fetchSession();
    }, [id]);

    const fetchSession = async () => {
        try {
            const res = await fetch(apiUrl(`/sessions/${id}`));
            if (!res.ok) throw new Error("Failed to load session");
            const data = await res.json();
            setSession(data);
            if (data.status === "completed") {
                navigate(`/report/${id}`);
                setLoading(false);
            } else {
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
            setPhase("generating");
            const res = await fetch(apiUrl(`/sessions/${id}/next_question`), { method: "POST" });
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
            setPhase(null);
        }
    };

    const finishSession = async () => {
        try {
            setLoading(true);
            const res = await fetch(apiUrl(`/sessions/${id}/end`), { method: "POST" });
            await res.json();
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
        setPhase("evaluating");
        const durationSeconds = answerStartRef.current ? (Date.now() - answerStartRef.current) / 1000 : null;
        try {
            const res = await fetch(apiUrl(`/sessions/${id}/answer`), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question_id: currentQuestion.question_id,
                    answer_text: answer,
                    duration_seconds: durationSeconds,
                    used_voice: usedVoiceRef.current,
                }),
            });
            if (!res.ok) throw new Error("Failed to submit answer");
            const data = (await res.json()) as AnswerFeedback;
            setLatestFeedback(data);
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
        if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
            alert("Speech recognition is not supported in this browser.");
            return;
        }

        // Don't let the interviewer talk over the candidate.
        stopSpeaking();

        // Mark that this answer was spoken, and start the delivery timer if not already.
        usedVoiceRef.current = true;
        if (answerStartRef.current === null) answerStartRef.current = Date.now();

        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = "en-US";

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
            let finalTranscript = "";
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                }
            }
            if (finalTranscript) {
                setAnswer((prev) => prev + (prev ? " " : "") + finalTranscript);
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
        document.addEventListener("fullscreenchange", handleFullscreenChange);
        return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
    }, []);

    if (loading && !session) return <div className="p-12 text-center">Loading session...</div>;
    if (error) return <div className="p-12 text-center text-red-400">{error}</div>;

    return (
        <div ref={containerRef} className={`transition-all duration-300 ${isFullscreen ? "fixed inset-0 z-50 bg-slate-950 p-8 flex flex-col justify-center" : "max-w-4xl mx-auto grid gap-6 pb-20"}`}>
            <div className={`flex items-center justify-between ${isFullscreen ? "mb-8 max-w-4xl mx-auto w-full" : ""}`}>
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
                    {currentQuestion?.number && currentQuestion?.total ? (
                        <div className="text-sm font-medium text-slate-300">
                            Question {currentQuestion.number}<span className="text-slate-500"> of {currentQuestion.total}</span>
                        </div>
                    ) : (
                        <div className="text-sm text-slate-500">
                            <span className="font-mono text-slate-400">{id?.slice(0, 8)}</span>
                        </div>
                    )}
                    {voiceSupported && (
                        <button
                            onClick={toggleVoice}
                            aria-label={voiceEnabled ? "Mute the interviewer's voice" : "Let the interviewer read questions aloud"}
                            className="p-2 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                            title={voiceEnabled ? "Mute interviewer voice" : "Read questions aloud"}
                        >
                            {voiceEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                        </button>
                    )}
                    <button
                        onClick={toggleFullscreen}
                        className="p-2 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                        title={isFullscreen ? "Exit Immersive Mode" : "Enter Immersive Mode"}
                    >
                        {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
                    </button>
                </div>
            </div>

            {currentQuestion?.number && currentQuestion?.total && (
                <div className={`${isFullscreen ? "max-w-4xl mx-auto w-full mb-6" : ""} h-1.5 bg-slate-800 rounded-full overflow-hidden`}>
                    <div
                        className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                        style={{ width: `${(currentQuestion.number / currentQuestion.total) * 100}%` }}
                    />
                </div>
            )}

            <div className={`bg-slate-900/50 border border-slate-800 rounded-2xl p-6 md:p-10 flex flex-col justify-center shadow-inner relative overflow-hidden ${isFullscreen ? "flex-1 max-w-4xl mx-auto w-full mb-8" : "min-h-[300px]"}`}>
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-50"></div>

                {phase ? (
                    <ThinkingIndicator phase={phase} />
                ) : (
                    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
                        <h3 className="font-display text-2xl md:text-3xl font-medium tracking-tight text-slate-100 leading-relaxed">{currentQuestion?.text}</h3>
                        {(currentQuestion?.competency || currentQuestion?.anchor) && (
                            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60">
                                {currentQuestion?.competency && (
                                    <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                                        {currentQuestion.competency}
                                    </span>
                                )}
                                {currentQuestion?.anchor && (
                                    <span className="text-xs text-slate-500 italic">
                                        Probing: “{currentQuestion.anchor}”
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>

            <div className={isFullscreen ? "max-w-4xl mx-auto w-full" : ""}>
                <form onSubmit={submitAnswer} className="relative mt-4">
                    <div className="absolute top-4 left-4">
                        <User className="w-5 h-5 text-slate-500" />
                    </div>
                    <textarea
                        autoFocus
                        rows={4}
                        value={answer}
                        onChange={(e) => {
                            if (answerStartRef.current === null && e.target.value) answerStartRef.current = Date.now();
                            setAnswer(e.target.value);
                        }}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && e.ctrlKey) submitAnswer(e);
                        }}
                        disabled={submitting || loading}
                        placeholder="Type your answer here... (Ctrl+Enter to submit)"
                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl pl-12 pr-28 py-4 text-slate-200 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all resize-none shadow-xl"
                    />
                    <div className="absolute bottom-4 right-4 flex gap-3">
                        <button
                            type="button"
                            onClick={toggleRecording}
                            aria-label={isRecording ? "Stop voice input" : "Start voice input"}
                            className={`p-2.5 rounded-xl transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${isRecording ? "bg-red-500/10 text-red-500 hover:bg-red-500/20 animate-pulse" : "text-slate-500 hover:text-slate-300 hover:bg-white/5"}`}
                            title={isRecording ? "Stop Recording" : "Start Voice Input"}
                        >
                            {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
                        </button>
                        <button
                            type="submit"
                            disabled={!answer.trim() || submitting || loading}
                            aria-label="Submit answer"
                            className="bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 text-white p-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </form>
            </div>

            {latestFeedback && (
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                    <div className="flex items-start justify-between gap-4 mb-3">
                        <div>
                            <h3 className="text-white font-semibold">Per-Answer Coaching</h3>
                            <p className="text-xs text-slate-500 mt-0.5 uppercase tracking-wider">Average score</p>
                        </div>
                        <ScoreRing value={latestFeedback.average_overall_score} caption="/ 100" />
                    </div>
                    <p className="text-sm text-slate-300 mb-2">STAR feedback: <span className="text-slate-200">{latestFeedback.star_feedback.summary}</span></p>
                    <p className="text-xs text-slate-500 mb-4">
                        STAR complete: {String(latestFeedback.star_feedback.star_complete)} | Metrics: {String(latestFeedback.star_feedback.metrics_present)} | Specificity: {latestFeedback.star_feedback.specificity}
                    </p>

                    {latestFeedback.delivery && (
                        <div className="mb-4 bg-slate-950/40 border border-slate-800 rounded-xl p-3">
                            <p className="text-xs uppercase text-sky-400 mb-1">Delivery</p>
                            <p className="text-xs text-slate-500 mb-2">
                                {latestFeedback.delivery.word_count} words
                                {latestFeedback.delivery.wpm != null && ` · ~${latestFeedback.delivery.wpm} wpm`}
                                {latestFeedback.delivery.hedge_count > 0 && ` · ${latestFeedback.delivery.hedge_count} hedging phrases`}
                            </p>
                            <ul className="text-sm text-slate-300 space-y-1">
                                {latestFeedback.delivery.notes.map((n, i) => <li key={i}>• {n}</li>)}
                            </ul>
                        </div>
                    )}

                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <p className="text-xs uppercase text-emerald-400 mb-1">Strengths</p>
                            <ul className="text-sm text-slate-300 space-y-1">
                                {latestFeedback.coaching.strengths.map((item, idx) => (
                                    <li key={idx}>• {item}</li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <p className="text-xs uppercase text-amber-400 mb-1">Improve Next</p>
                            <ul className="text-sm text-slate-300 space-y-1">
                                {latestFeedback.coaching.improvements.map((item, idx) => (
                                    <li key={idx}>• {item}</li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <div>
                        <p className="text-xs uppercase text-indigo-400 mb-1">Rewrite</p>
                        <pre className="text-xs whitespace-pre-wrap bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-300">{latestFeedback.coaching.rewrite}</pre>
                    </div>
                </div>
            )}
        </div>
    );
}
