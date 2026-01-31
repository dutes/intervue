const state = {
  sessionId: null,
  currentQuestionId: null,
  answeredCount: 0,
};

const elements = {
  sessionStatus: document.getElementById("sessionStatus"),
  statusMessage: document.getElementById("statusMessage"),
  startForm: document.getElementById("startForm"),
  jobSpec: document.getElementById("jobSpec"),
  cvText: document.getElementById("cvText"),
  roundPill: document.getElementById("roundPill"),
  personaPill: document.getElementById("personaPill"),
  questionText: document.getElementById("questionText"),
  answerForm: document.getElementById("answerForm"),
  answerText: document.getElementById("answerText"),
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
};

const TOTAL_QUESTIONS = 5;

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
  const percent = Math.min(state.answeredCount / TOTAL_QUESTIONS, 1) * 100;
  elements.progressFill.style.width = `${percent}%`;
  elements.progressText.textContent = `${state.answeredCount} of ${TOTAL_QUESTIONS} answered`;
};

const setQuestion = (question) => {
  if (!question) {
    elements.questionText.textContent = "No active question yet.";
    elements.roundPill.textContent = "Round —";
    elements.personaPill.textContent = "Persona —";
    state.currentQuestionId = null;
    elements.answerForm.hidden = true;
    setSubmitting(false);
    return;
  }
  elements.questionText.textContent = question.text;
  elements.roundPill.textContent = `Round ${question.round}`;
  elements.personaPill.textContent = `Persona ${question.persona}`;
  state.currentQuestionId = question.question_id;
  elements.answerForm.hidden = false;
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
  fillList(elements.strengthsList, summary.strengths || []);
  fillList(elements.weaknessesList, summary.weaknesses || []);
  fillList(elements.personaFeedbackList, summary.persona_feedback || []);
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
  for (let i = 0; i < TOTAL_QUESTIONS; i += 1) {
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
  setStatus("Starting", "Generating rubric and first question...");
  setSummary(null);
  state.answeredCount = 0;
  updateProgress();
  try {
    const payload = {
      job_spec: elements.jobSpec.value.trim(),
      cv_text: elements.cvText.value.trim(),
      provider: "openai",
    };
    const data = await apiRequest("/sessions/start", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.sessionId = data.session_id;
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

setQuestion(null);
initProgress();
