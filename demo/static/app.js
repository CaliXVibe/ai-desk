const SAMPLE = `Client: North Pier Logistics
Need a loading-bay walkthrough Tuesday 2026-09-15 09:00.
Contact: ops@northpier.example
Notes: bring the checklist, 45 minutes, bay 3.
Open: confirm forklift escort on arrival.`;

const $ = (id) => document.getElementById(id);

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || res.statusText);
  }
  return data;
}

function empty(el, fallback) {
  el.innerHTML = "";
  if (fallback) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = fallback;
    el.appendChild(li);
  }
}

function renderDesk(desk) {
  const mail = desk.mail || [];
  const files = desk.files || [];
  const calendar = desk.calendar || [];
  $("mail-count").textContent = String(mail.length);
  $("file-count").textContent = String(files.length);
  $("cal-count").textContent = String(calendar.length);

  const mailList = $("mail");
  empty(mailList, mail.length ? "" : "Empty. This login has no mail.");
  mail.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${esc(item.subject)}</strong><br/><span class="muted">from ${esc(item.from)} → ${esc(item.to)}</span><br/>${esc(item.body)}`;
    mailList.appendChild(li);
  });

  const fileList = $("files");
  empty(fileList, files.length ? "" : "Empty. This login has no files.");
  files.forEach((item) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "link";
    btn.type = "button";
    btn.textContent = item.path;
    btn.addEventListener("click", () => {
      const view = $("file-view");
      view.hidden = false;
      view.textContent = item.markdown;
    });
    li.appendChild(btn);
    fileList.appendChild(li);
  });

  const calList = $("calendar");
  empty(calList, calendar.length ? "" : "Empty. This login has no events.");
  calendar.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${esc(item.title)}</strong><br/><span class="muted">${esc(item.start)} → ${esc(item.end)}</span><br/>${esc(item.notes)}`;
    calList.appendChild(li);
  });
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderSession(session) {
  const select = $("user");
  if (!select.options.length) {
    session.users.forEach((user) => {
      const opt = document.createElement("option");
      opt.value = user;
      opt.textContent = user;
      select.appendChild(opt);
    });
  }
  select.value = session.user;
  const iso = session.isolation || {};
  const a = session.users[0];
  const b = session.users[1];
  $("iso-a").textContent = `${a}: ${fmtCounts(iso[a])}`;
  $("iso-b").textContent = `${b}: ${fmtCounts(iso[b])}`;
}

function fmtCounts(counts) {
  if (!counts) return "mail 0 / files 0 / cal 0";
  return `mail ${counts.mail} / files ${counts.files} / cal ${counts.calendar}`;
}

async function refresh() {
  const session = await api("/api/session");
  const desk = await api("/api/desk");
  renderSession(session);
  renderDesk(desk.desk);
  return session;
}

$("sample").addEventListener("click", () => {
  $("job").value = SAMPLE;
});

$("submit").addEventListener("click", async () => {
  $("drop-status").textContent = "Ingesting…";
  $("banner").hidden = true;
  try {
    const result = await api("/api/drop", {
      method: "POST",
      body: JSON.stringify({ text: $("job").value }),
    });
    $("drop-status").textContent = `Filed ${result.artifacts.file.path} for ${result.user}`;
    $("banner").hidden = false;
    $("banner").textContent = `Night Desk wrote mail + file + event for ${result.user} only. Switch logins to confirm the other desk stayed empty.`;
    const session = await refresh();
    renderDesk(result.desk);
    renderSession(session);
  } catch (err) {
    $("drop-status").textContent = err.message;
  }
});

$("user").addEventListener("change", async (event) => {
  $("file-view").hidden = true;
  $("banner").hidden = true;
  await api("/api/login", {
    method: "POST",
    body: JSON.stringify({ user: event.target.value }),
  });
  await refresh();
});

refresh().catch((err) => {
  $("drop-status").textContent = err.message;
});
