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
    const [enabled, setEnabled] = useState(supported);
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

    const speak = useCallback(
        (text: string, persona: string) => {
            if (!supported || !enabled || !text) return;
            const synth = window.speechSynthesis;
            synth.cancel(); // never overlap two utterances
            const utterance = new SpeechSynthesisUtterance(text);
            const voice = personaVoices.current[persona];
            if (voice) utterance.voice = voice;
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            synth.speak(utterance);
        },
        [supported, enabled],
    );

    const toggle = useCallback(() => {
        setEnabled((prev) => {
            const next = !prev;
            if (!next && supported) window.speechSynthesis.cancel(); // muting stops current speech
            return next;
        });
    }, [supported]);

    return { supported, enabled, toggle, speak, stop };
}
