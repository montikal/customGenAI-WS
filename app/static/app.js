let DOC_ID = null;

function logChat(text, cls) {
  const chat = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = cls;
  div.innerText = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function uploadPDF() {
  const fileInput = document.getElementById("pdfFile");
  if (!fileInput.files.length) {
    alert("Select a PDF first");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  logChat("Uploading PDF...", "small");

  const res = await fetch("/upload", {
    method: "POST",
    body: formData
  });

  const data = await res.json();
  DOC_ID = data.doc_id;

  document.getElementById("docInfo").innerText =
    `Loaded document: ${data.filename} (${data.chunks} chunks)`;

  logChat("PDF indexed. You can ask questions now.", "small");
}

async function sendQuestion() {
  if (!DOC_ID) {
    alert("Upload a PDF first");
    return;
  }

  const qInput = document.getElementById("question");
  const question = qInput.value.trim();
  if (!question) return;

  logChat("You: " + question, "user");
  qInput.value = "";

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doc_id: DOC_ID,
      question: question
    })
  });

  const data = await res.json();
  logChat("Bot: " + data.answer, "bot");
}
