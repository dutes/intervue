const state = {
  sessionId: null,
  currentQuestionId: null,
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
  nextQuestion: document.getElementById("nextQuestion"),
  summaryCard: document.getElementById("summaryCard"),
  overallScore: document.getElementById("overallScore"),
  strengthsList: document.getElementById("strengthsList"),
  weaknessesList: document.getElementById("weaknessesList"),
  personaFeedbackList: document.getElementById("personaFeedbackList"),
};

const setStatus = (status, message = "") => {
  elements.sessionStatus.textContent = status;
  elements.statusMessage.textContent = message;
};

const setQuestion = (question) => {
  if (!question) {
    elements.questionText.textContent = "No active question yet.";
    elements.roundPill.textContent = "Round —";
    elements.personaPill.textContent = "Persona —";
    state.currentQuestionId = null;
    return;
  }
  elements.questionText.textContent = question.text;
  elements.roundPill.textContent = `Round ${question.round}`;
  elements.personaPill.textContent = `Persona ${question.persona}`;
  state.currentQuestionId = question.question_id;
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

elements.startForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Starting", "Generating rubric and first question...");
  setSummary(null);
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
    setStatus("Answered", "Answer submitted. Get the next question when ready.");
  } catch (error) {
    setStatus("Error", error.message);
  }
});

elements.nextQuestion.addEventListener("click", async () => {
  setStatus("Loading", "Fetching the next question...");
  try {
    await fetchNextQuestion();
    setStatus("Active", `Session ID: ${state.sessionId}`);
  } catch (error) {
    if (error.message.includes("Interview already complete")) {
      setStatus("Complete", "Interview complete. Generating summary...");
      try {
        const result = await apiRequest(`/sessions/${state.sessionId}/end`, {
          method: "POST",
        });
        setSummary(result.summary);
      } catch (summaryError) {
        setStatus("Error", summaryError.message);
      }
    } else {
      setStatus("Error", error.message);
    }
  }
});

setQuestion(null);
