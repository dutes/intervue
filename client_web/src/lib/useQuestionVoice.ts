import { useCallback, useEffect, useRef, useState } from "react";

// The three interviewer personas; each gets its own randomly-assigned voice so a round
// "sounds like" a consistent interviewer.
const PERSONA_KEYS = ["positive", "neutral", "hostile"];

/**
 * Speaks interview questions aloud using the browser's built-in SpeechSynthesis API.
 * No API key, no network, works offline — the speaking counterpart to the SpeechRecognition
 * already used for answers. Hardened for Edge, Chrome and Safari quirks.
 */
export function useQuestionVoice() {
    const supported = typeof window !== "undefined" && "speechSynthesis" in window;
    // Off until the user opts in. The opt-in click also serves as the browser "user gesture"
    // that unlocks SpeechSynthesis (Chrome/Safari block speech before any interaction).
    const [enabled, setEnabled] = useState(false);
    const personaVoices = useRef<Record<string, SpeechSynthesisVoice | undefined>>({});
    const keepAlive = useRef<number | null>(null);

    // Voices load asynchronously (Chrome, Safari), so assign on load AND on "voiceschanged".
    useEffect(() => {
        if (!supported) return;
        const synth = window.speechSynthesis;
        const assignVoices = () => {
            const englishVoices = synth.getVoices().filter((v) => v.lang.toLowerCase().startsWith("en"));
            if (englishVoices.length === 0) return;
            // Prefer LOCAL (offline) voices — Edge/Chrome expose many remote/online voices that can
            // be flaky or silent. Fall back to the full list only if there are no local ones.
            const localVoices = englishVoices.filter((v) => v.localService);
            const pool = localVoices.length > 0 ? localVoices : englishVoices;
            const shuffled = [...pool].sort(() => Math.random() - 0.5);
            const map: Record<string, SpeechSynthesisVoice | undefined> = {};
            PERSONA_KEYS.forEach((persona, i) => {
                map[persona] = shuffled[i % shuffled.length];
            });
            personaVoices.current = map;
        };
        assignVoices();
        synth.addEventListener("voiceschanged", assignVoices);
        return () => {
            synth.removeEventListener("voiceschanged", assignVoices);
            synth.cancel();
        };
    }, [supported]);

    const clearKeepAlive = useCallback(() => {
        if (keepAlive.current !== null) {
            clearInterval(keepAlive.current);
            keepAlive.current = null;
        }
    }, []);

    const stop = useCallback(() => {
        clearKeepAlive();
        if (supported) window.speechSynthesis.cancel();
    }, [supported, clearKeepAlive]);

    // Caller decides whether speaking is wanted; speak() just does it (so it can be used to
    // speak the current question the moment the user enables voice).
    const speak = useCallback(
        (text: string, persona: string) => {
            if (!supported || !text) return;
            const synth = window.speechSynthesis;
            clearKeepAlive();
            // Only cancel if something is actually playing/queued — cancel() then speak() on an
            // idle queue is a known Chrome bug that silently drops the utterance.
            if (synth.speaking || synth.pending) synth.cancel();
            synth.resume(); // Chrome can leave the queue paused; this unsticks it.

            const utterance = new SpeechSynthesisUtterance(text);
            let voice = personaVoices.current[persona];
            if (!voice) {
                // Voices may not have been ready when assigned (common on Safari) — pick one now.
                const english = synth.getVoices().filter((v) => v.lang.toLowerCase().startsWith("en"));
                voice = english.find((v) => v.localService) ?? english[0];
            }
            if (voice) utterance.voice = voice;
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.onend = clearKeepAlive;
            utterance.onerror = clearKeepAlive;
            synth.speak(utterance);

            // Chrome pauses long utterances after ~15s; nudge resume() periodically to keep going.
            keepAlive.current = window.setInterval(() => {
                if (window.speechSynthesis.speaking) window.speechSynthesis.resume();
                else clearKeepAlive();
            }, 5000);
        },
        [supported, clearKeepAlive],
    );

    return { supported, enabled, setEnabled, speak, stop };
}
