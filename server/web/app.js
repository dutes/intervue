const state = {
  sessionId: null,
  currentQuestionId: null,
  answeredCount: 0,
  provider: null,
  apiKey: null,
  pendingStart: false,
  isListening: false,
  totalQuestions: 5,
};

const elements = {
  sessionStatus: document.getElementById("sessionStatus"),
  statusMessage: document.getElementById("statusMessage"),
  startForm: document.getElementById("startForm"),
  jobSpec: document.getElementById("jobSpec"),
  cvText: document.getElementById("cvText"),
  startRound: document.getElementById("startRound"),
  roundPill: document.getElementById("roundPill"),
  personaPill: document.getElementById("personaPill"),
  questionText: document.getElementById("questionText"),
  answerForm: document.getElementById("answerForm"),
  answerText: document.getElementById("answerText"),
  voiceToggle: document.getElementById("voiceToggle"),
  voiceStatus: document.getElementById("voiceStatus"),
  submitAnswer: document.getElementById("submitAnswer"),
  submitStatus: document.getElementById("submitStatus"),
  progressFill: document.getElementById("progressFill"),
  progressSteps: document.getElementById("progressSteps"),
  progressText: document.getElementById("progressText"),
  summaryCard: document.getElementById("summaryCard"),
  overallScore: document.getElementById("overallScore"),
  strengthsList: document.getElementById("strengthsList"),
  weaknessesList: document.getElementById("weaknessesList"),
  personaFeedbackList: document.getElementById("personaFeedbackList"),
  apiKeyDialog: document.getElementById("apiKeyDialog"),
  apiKeyForm: document.getElementById("apiKeyForm"),
  providerSelect: document.getElementById("providerSelect"),
  apiKeyInput: document.getElementById("apiKeyInput"),
  apiKeyHint: document.getElementById("apiKeyHint"),
  apiKeyError: document.getElementById("apiKeyError"),
};

let speechRecognition = null;

const setStatus = (status, message = "") => {
  elements.sessionStatus.textContent = status;
  elements.statusMessage.textContent = message;
};

const setSubmitting = (isSubmitting) => {
  elements.submitStatus.hidden = !isSubmitting;
  elements.submitAnswer.disabled = isSubmitting || !state.currentQuestionId;
};

const updateProgress = () => {
  const steps = Array.from(elements.progressSteps.children);
  steps.forEach((step, index) => {
    const isComplete = index < state.answeredCount;
    const isActive = index === state.answeredCount && state.currentQuestionId;
    step.classList.toggle("is-complete", isComplete);
    step.classList.toggle("is-active", isActive);
  });
  const totalSegments = Math.max(state.totalQuestions - 1, 1);
  const percent = Math.min(state.answeredCount / totalSegments, 1) * 100;
  elements.progressFill.style.width = `${percent}%`;
  elements.progressText.textContent = `${state.answeredCount} of ${state.totalQuestions} answered`;
};

const setQuestion = (question) => {
  if (!question) {
    elements.questionText.textContent = "No active question yet.";
    elements.roundPill.textContent = "Round —";
    elements.personaPill.textContent = "Persona —";
    state.currentQuestionId = null;
    elements.answerForm.hidden = true;
    stopVoiceInput();
    setSubmitting(false);
    return;
  }
  elements.questionText.textContent = question.text;
  elements.roundPill.textContent = `Round ${question.round}`;
  elements.personaPill.textContent = `Persona ${question.persona}`;
  state.currentQuestionId = question.question_id;
  elements.answerForm.hidden = false;
  setVoiceStatus("Voice input idle.");
  setSubmitting(false);
};

const setSummary = (summary) => {
  elements.summaryCard.hidden = !summary;
  if (!summary) {
    return;
  }
  elements.overallScore.textContent = `Overall score: ${summary.overall_score}`;
  const fillList = (listElement, items) => {
    listElement.innerHTML = "";
    items.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      listElement.appendChild(li);
    });
  };
  const renderPersonaFeedback = (listElement, feedbackItems) => {
    listElement.innerHTML = "";
    feedbackItems.forEach((feedback) => {
      if (typeof feedback === "string") {
        const li = document.createElement("li");
        li.textContent = feedback;
        listElement.appendChild(li);
        return;
      }
      const li = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = `${feedback.persona?.toUpperCase() ?? "PERSONA"}: `;
      li.appendChild(title);

      const lines = [
        ...(feedback.positives || []).map((text) => `✅ ${text}`),
        ...(feedback.concerns || []).map((text) => `⚠️ ${text}`),
      ];
      if (feedback.next_step) {
        lines.push(`➡️ ${feedback.next_step}`);
      }
      if (lines.length) {
        const detailList = document.createElement("ul");
        lines.forEach((line) => {
          const detailItem = document.createElement("li");
          detailItem.textContent = line;
          detailList.appendChild(detailItem);
        });
        li.appendChild(detailList);
      }
      listElement.appendChild(li);
    });
  };
  fillList(elements.strengthsList, summary.strengths || []);
  fillList(elements.weaknessesList, summary.weaknesses || []);
  renderPersonaFeedback(elements.personaFeedbackList, summary.persona_feedback || []);
};

const apiRequest = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || "Request failed.");
  }
  return response.json();
};

const showApiKeyDialog = () => {
  elements.apiKeyError.hidden = true;
  elements.apiKeyError.textContent = "";
  if (state.provider) {
    elements.providerSelect.value = state.provider;
  }
  elements.apiKeyInput.value = state.apiKey ?? "";
  elements.apiKeyDialog.showModal();
  window.requestAnimationFrame(() => {
    elements.apiKeyInput.focus();
  });
};

const setVoiceStatus = (message) => {
  elements.voiceStatus.textContent = message;
};

const updateVoiceToggle = () => {
  elements.voiceToggle.textContent = state.isListening ? "Stop voice input" : "Start voice input";
  elements.voiceToggle.classList.toggle("voice-active", state.isListening);
};

const appendTranscript = (transcript) => {
  if (!transcript) {
    return;
  }
  const existing = elements.answerText.value;
  const spacer = existing && !existing.endsWith(" ") ? " " : "";
  elements.answerText.value = `${existing}${spacer}${transcript.trim()}`;
};

const stopVoiceInput = () => {
  if (speechRecognition && state.isListening) {
    speechRecognition.stop();
  }
  state.isListening = false;
  updateVoiceToggle();
};

const initSpeechRecognition = () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    elements.voiceToggle.disabled = true;
    setVoiceStatus("Voice input is not supported in this browser.");
    return;
  }
  speechRecognition = new SpeechRecognition();
  speechRecognition.lang = "en-US";
  speechRecognition.continuous = true;
  speechRecognition.interimResults = true;

  speechRecognition.addEventListener("result", (event) => {
    let interimTranscript = "";
    let finalTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      const transcript = result[0].transcript;
      if (result.isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }
    if (finalTranscript) {
      appendTranscript(finalTranscript);
    }
    if (state.isListening) {
      const interimSuffix = interimTranscript ? ` ${interimTranscript.trim()}` : "";
      setVoiceStatus(`Listening...${interimSuffix}`);
    }
  });

  speechRecognition.addEventListener("error", (event) => {
    setVoiceStatus(`Voice input error: ${event.error}`);
    stopVoiceInput();
  });

  speechRecognition.addEventListener("end", () => {
    if (state.isListening) {
      state.isListening = false;
      updateVoiceToggle();
      setVoiceStatus("Voice input idle.");
    }
  });
};

const updateApiKeyHint = () => {
  const provider = elements.providerSelect.value;
  const needsKey = provider === "openai" || provider === "gemini";
  elements.apiKeyHint.textContent = needsKey ? "Required for OpenAI and Gemini." : "No key required for mock.";
  elements.apiKeyInput.toggleAttribute("required", needsKey);
  elements.apiKeyInput.disabled = !needsKey;
};

const persistApiKey = () => {
  const provider = elements.providerSelect.value;
  const apiKey = elements.apiKeyInput.value.trim();
  const needsKey = provider === "openai" || provider === "gemini";
  if (needsKey && !apiKey) {
    elements.apiKeyError.textContent = "Please enter an API key to continue.";
    elements.apiKeyError.hidden = false;
    return false;
  }
  state.provider = provider;
  state.apiKey = needsKey ? apiKey : null;
  elements.apiKeyDialog.close();
  return true;
};

const fetchNextQuestion = async () => {
  if (!state.sessionId) {
    throw new Error("Start a session first.");
  }
  const question = await apiRequest(`/sessions/${state.sessionId}/next_question`, {
    method: "POST",
  });
  setQuestion(question);
};

const initProgress = () => {
  elements.progressSteps.innerHTML = "";
  for (let i = 0; i < state.totalQuestions; i += 1) {
    const step = document.createElement("span");
    step.className = "progress-step";
    elements.progressSteps.appendChild(step);
  }
  updateProgress();
};

const endSession = async () => {
  setStatus("Complete", "Interview complete. Generating summary...");
  try {
    const result = await apiRequest(`/sessions/${state.sessionId}/end`, {
      method: "POST",
    });
    setSummary(result.summary);
  } catch (summaryError) {
    setStatus("Error", summaryError.message);
  } finally {
    setQuestion(null);
  }
};

elements.startForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.provider) {
    state.pendingStart = true;
    showApiKeyDialog();
    return;
  }
  setStatus("Starting", "Generating rubric and first question...");
  setSummary(null);
  state.answeredCount = 0;
  updateProgress();
  try {
    const startRound = Number.parseInt(elements.startRound.value, 10) || 1;
    const payload = {
      job_spec: elements.jobSpec.value.trim(),
      cv_text: elements.cvText.value.trim(),
      provider: state.provider,
      api_key: state.apiKey,
      start_round: startRound,
    };
    const data = await apiRequest("/sessions/start", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.sessionId = data.session_id;
    state.totalQuestions = data.total_questions ?? state.totalQuestions;
    initProgress();
    setStatus("Active", `Session ID: ${state.sessionId}`);
    await fetchNextQuestion();
  } catch (error) {
    setStatus("Error", error.message);
  }
});

elements.answerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.sessionId || !state.currentQuestionId) {
    setStatus("Error", "No active question to answer.");
    return;
  }
  stopVoiceInput();
  setSubmitting(true);
  setStatus("Scoring", "Submitting your answer for evaluation...");
  try {
    await apiRequest(`/sessions/${state.sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({
        question_id: state.currentQuestionId,
        answer_text: elements.answerText.value.trim(),
      }),
    });
    elements.answerText.value = "";
    state.answeredCount += 1;
    updateProgress();
    setStatus("Answered", "Answer submitted. Fetching the next question...");
    try {
      await fetchNextQuestion();
      setStatus("Active", `Session ID: ${state.sessionId}`);
    } catch (error) {
      if (error.message.includes("Interview already complete")) {
        await endSession();
      } else {
        setStatus("Error", error.message);
      }
    } finally {
      setSubmitting(false);
    }
  } catch (error) {
    setStatus("Error", error.message);
    setSubmitting(false);
  }
});

elements.providerSelect.addEventListener("change", updateApiKeyHint);

elements.apiKeyForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!persistApiKey()) {
    return;
  }
  updateApiKeyHint();
  if (state.pendingStart) {
    state.pendingStart = false;
    elements.startForm.requestSubmit();
  }
});

elements.voiceToggle.addEventListener("click", () => {
  if (!speechRecognition) {
    setVoiceStatus("Voice input is not supported in this browser.");
    return;
  }
  if (state.isListening) {
    stopVoiceInput();
    setVoiceStatus("Voice input idle.");
    return;
  }
  try {
    speechRecognition.start();
    state.isListening = true;
    updateVoiceToggle();
    setVoiceStatus("Listening...");
  } catch (error) {
    setVoiceStatus("Unable to start voice input.");
    state.isListening = false;
    updateVoiceToggle();
  }
});

setQuestion(null);
initProgress();
updateApiKeyHint();
initSpeechRecognition();
showApiKeyDialog();
