import { useCallback, useEffect, useRef, useState } from "react";

// The three interviewer personas; each gets its own randomly-assigned voice so a round
// "sounds like" a consistent interviewer.
const PERSONA_KEYS = ["positive", "neutral", "hostile"];

/**
 * Speaks interview questions aloud using the browser's built-in SpeechSynthesis API.
 * No API key, no network, works offline — the speaking counterpart to the SpeechRecognition
 * already used for answers.
 */
export function useQuestionVoice() {
    const supported = typeof window !== "undefined" && "speechSynthesis" in window;
    // Off until the user opts in. The opt-in click also serves as the browser "user gesture"
    // that unlocks SpeechSynthesis (Chrome blocks speech before any interaction).
    const [enabled, setEnabled] = useState(false);
    const personaVoices = useRef<Record<string, SpeechSynthesisVoice | undefined>>({});

    // Voices load asynchronously in most browsers, so assign on load AND on the
    // "voiceschanged" event. Each persona gets a random English voice.
    useEffect(() => {
        if (!supported) return;
        const synth = window.speechSynthesis;
        const assignVoices = () => {
            const englishVoices = synth.getVoices().filter((v) => v.lang.toLowerCase().startsWith("en"));
            if (englishVoices.length === 0) return;
            const shuffled = [...englishVoices].sort(() => Math.random() - 0.5);
            const map: Record<string, SpeechSynthesisVoice> = {};
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

    const stop = useCallback(() => {
        if (supported) window.speechSynthesis.cancel();
    }, [supported]);

    // Caller decides whether speaking is wanted; speak() just does it (so it can be used to
    // speak the current question the moment the user enables voice).
    const speak = useCallback(
        (text: string, persona: string) => {
            if (!supported || !text) return;
            const synth = window.speechSynthesis;
            synth.cancel(); // never overlap two utterances
            synth.resume(); // Chrome can leave the queue paused; this unsticks it
            const utterance = new SpeechSynthesisUtterance(text);
            const voice = personaVoices.current[persona];
            if (voice) utterance.voice = voice;
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            synth.speak(utterance);
        },
        [supported],
    );

    return { supported, enabled, setEnabled, speak, stop };
}
