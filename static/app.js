const form = document.getElementById("clipForm");
const input = document.getElementById("youtubeUrl");
const formatSelect = document.getElementById("formatSelect");
const captionsToggle = document.getElementById("captionsToggle");
const button = document.getElementById("clipButton");
const results = document.getElementById("results");
const statusEl = document.getElementById("status");
const grid = document.getElementById("clipResults");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = input.value.trim();
  if (!url) return;
  results.classList.remove("hidden");
  grid.innerHTML = "";
  statusEl.textContent = "Working… downloading the video, transcribing speech and rendering clips can take a few minutes.";
  button.disabled = true;
  button.textContent = "Processing…";
  results.scrollIntoView({behavior:"smooth", block:"start"});
  try {
    const response = await fetch("/api/clip", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        url,
        format: formatSelect.value,
        captions: captionsToggle.checked
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something went wrong.");
    statusEl.textContent = data.note || "Done — review your clips before posting.";
    data.clips.forEach((clip) => {
      const card = document.createElement("article");
      card.className = "result-card";
      const title = document.createElement("h3");
      title.textContent = `${clip.title} · ${clip.start}s–${clip.end}s`;
      const details = document.createElement("p");
      const formatName = {"vertical":"9:16 Vertical","square":"1:1 Square","horizontal":"16:9 Horizontal"}[clip.format] || clip.format;
      details.textContent = `${formatName} · Captions ${clip.captions ? "on" : "off"}`;
      const link = document.createElement("a");
      link.className = "download";
      link.href = clip.url;
      link.textContent = "Download MP4 ↓";
      link.setAttribute("download", "");
      card.append(title, details, link);
      grid.appendChild(card);
    });
  } catch (error) {
    statusEl.textContent = error.message + " Check the server logs if you run this website yourself.";
  } finally {
    button.disabled = false;
    button.textContent = "✦ Generate clips";
  }
});
