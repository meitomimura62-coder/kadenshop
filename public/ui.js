const apiBase = "http://localhost:8080";

const $ = (id) => document.getElementById(id);
const show = (el, data) => {
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
};

async function request(path, options = {}) {
  const res = await fetch(`${apiBase}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  if (!res.ok) {
    throw { status: res.status, body: json };
  }
  return json;
}

function parseChoices(raw) {
  if (!raw.trim()) return [];
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(":");
      const label = parts.shift()?.trim().toUpperCase();
      const text = parts.join(":").trim();
      return { choice_label: label, choice_text: text };
    });
}

$("healthBtn").addEventListener("click", async () => {
  try {
    const data = await request("/health");
    show($("healthStatus"), `ok (${data.status})`);
  } catch (err) {
    show($("healthStatus"), `error (${err.status})`);
  }
});

$("createQuestionBtn").addEventListener("click", async () => {
  const payload = {
    domain_name: $("qDomain").value,
    topic_name: $("qTopic").value || null,
    title: $("qTitle").value || null,
    stem: $("qStem").value,
    correct_label: $("qCorrect").value,
    choices: parseChoices($("qChoices").value),
  };
  try {
    const data = await request("/questions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    show($("questionsList"), data);
  } catch (err) {
    show($("questionsList"), err.body || err);
  }
});

$("listQuestionsBtn").addEventListener("click", async () => {
  const params = new URLSearchParams();
  if ($("listDomain").value) params.set("domain_name", $("listDomain").value);
  if ($("listTopic").value) params.set("topic_name", $("listTopic").value);
  if ($("listInclude").value) params.set("include", $("listInclude").value);
  if ($("listLimit").value) params.set("limit", $("listLimit").value);

  try {
    const data = await request(`/questions?${params.toString()}`);
    show($("questionsList"), data);
  } catch (err) {
    show($("questionsList"), err.body || err);
  }
});

$("getOneBtn").addEventListener("click", async () => {
  try {
    const data = await request(`/questions/${$("oneId").value}`);
    show($("oneOutput"), data);
  } catch (err) {
    show($("oneOutput"), err.body || err);
  }
});

$("updateOneBtn").addEventListener("click", async () => {
  try {
    const payload = JSON.parse($("updateJson").value || "{}");
    const data = await request(`/questions/${$("oneId").value}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    show($("oneOutput"), data);
  } catch (err) {
    show($("oneOutput"), err.body || err);
  }
});

$("deleteOneBtn").addEventListener("click", async () => {
  try {
    const data = await request(`/questions/${$("oneId").value}`, { method: "DELETE" });
    show($("oneOutput"), data);
  } catch (err) {
    show($("oneOutput"), err.body || err);
  }
});

$("submitAnswerBtn").addEventListener("click", async () => {
  const payload = {
    user_id: Number($("ansUser").value),
    question_id: Number($("ansQ").value),
    selected_label: $("ansLabel").value,
    elapsed_ms: $("ansElapsed").value ? Number($("ansElapsed").value) : null,
  };
  try {
    const data = await request("/answers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    show($("answerOutput"), data);
  } catch (err) {
    show($("answerOutput"), err.body || err);
  }
});

$("rawSendBtn").addEventListener("click", async () => {
  const method = $("rawMethod").value || "GET";
  const path = $("rawPath").value || "/";
  const rawBody = $("rawBody").value;

  try {
    const data = await request(path, {
      method,
      body: ["GET", "HEAD"].includes(method.toUpperCase()) ? undefined : rawBody || "{}",
    });
    show($("rawOutput"), data);
  } catch (err) {
    show($("rawOutput"), err.body || err);
  }
});
