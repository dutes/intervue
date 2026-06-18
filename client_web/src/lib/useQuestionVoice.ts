import { useCallback, useEffect, useRef, useState } from "react";

import { apiUrl } from "./api";

// ~10ms of silence. Played on the first user gesture to unlock autoplay so that the later,
// asynchronous /tts playback (which resolves outside the original click) is still allowed —
// Safari/Chrome block audio that isn't traceable to a user gesture.
const SILENT_WAV =
    "data:audio/wav;base64,UklGRnQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YVAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==";

/**
 * Speaks interview questions aloud using the backend's local Piper TTS (server/tts) via the
 * /tts endpoint, playing the returned WAV through a single reused <audio> element.
 *
 * Piper-only: there is no Web Speech fallback. If /tts is unavailable (e.g. running the API
 * outside the Docker image, where the Piper binary isn't bundled) the request fails and the
 * call is a no-op — voice simply doesn't play.
 */
export function useQuestionVoice() {
    const supported = typeof window !== "undefined" && typeof Audio !== "undefined";
    // Off until the user opts in. The opt-in click also serves as the "user gesture" that
    // unlocks audio playback for the rest of the session.
    const [enabled, setEnabled] = useState(false);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const objectUrlRef = useRef<string | null>(null);
    const abortRef = useRef<AbortController | null>(null);
    const unlockedRef = useRef(false);

    const getAudio = useCallback(() => {
        if (!audioRef.current) audioRef.current = new Audio();
        return audioRef.current;
    }, []);

    const revokeUrl = useCallback(() => {
        if (objectUrlRef.current) {
            URL.revokeObjectURL(objectUrlRef.current);
            objectUrlRef.current = null;
        }
    }, []);

    const stop = useCallback(() => {
        if (abortRef.current) {
            abortRef.current.abort();
            abortRef.current = null;
        }
        const audio = audioRef.current;
        if (audio) {
            audio.pause();
            audio.currentTime = 0;
        }
        revokeUrl();
    }, [revokeUrl]);

    // Caller decides whether speaking is wanted; speak() just fetches + plays (so it can be
    // used to speak the current question the moment the user enables voice).
    const speak = useCallback(
        (text: string, persona: string, sessionId?: string) => {
            if (!supported || !text) return;
            const audio = getAudio();

            // Unlock autoplay on the first (gesture-driven) call so later async plays work.
            if (!unlockedRef.current) {
                unlockedRef.current = true;
                audio.src = SILENT_WAV;
                audio.play().catch(() => {});
            }

            // Cancel any in-flight request and current playback before starting the new one.
            if (abortRef.current) abortRef.current.abort();
            const controller = new AbortController();
            abortRef.current = controller;
            audio.pause();

            fetch(apiUrl("/tts"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, persona, session_id: sessionId }),
                signal: controller.signal,
            })
                .then((res) => {
                    if (!res.ok) throw new Error(`TTS request failed: ${res.status}`);
                    return res.blob();
                })
                .then((blob) => {
                    if (controller.signal.aborted) return;
                    revokeUrl();
                    const url = URL.createObjectURL(blob);
                    objectUrlRef.current = url;
                    audio.src = url;
                    audio.play().catch(() => {});
                })
                .catch((err) => {
                    if (err?.name !== "AbortError") console.error("TTS playback error:", err);
                });
        },
        [supported, getAudio, revokeUrl],
    );

    // Tear down on unmount: abort any request, stop audio, free the object URL.
    useEffect(() => {
        return () => {
            if (abortRef.current) abortRef.current.abort();
            if (audioRef.current) audioRef.current.pause();
            if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        };
    }, []);

    return { supported, enabled, setEnabled, speak, stop };
}
