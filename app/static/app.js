const state = {
  sessionId: null,
  masterUrl: null,
  variantUrl: null,
  segments: [],
  adBreaks: [],
  variants: [],
  activeSegmentIndex: -1,
  hls: null,
};

const elements = {
  createSessionBtn: document.getElementById("create-session-btn"),
  reloadManifestBtn: document.getElementById("reload-manifest-btn"),
  player: document.getElementById("player"),
  sessionId: document.getElementById("session-id"),
  playbackState: document.getElementById("playback-state"),
  currentPhase: document.getElementById("current-phase"),
  masterUrl: document.getElementById("master-url"),
  variantUrl: document.getElementById("variant-url"),
  currentSegment: document.getElementById("current-segment"),
  supportPill: document.getElementById("support-pill"),
  timeline: document.getElementById("timeline"),
  adBreaks: document.getElementById("ad-breaks"),
  variantsList: document.getElementById("variants-list"),
  breaksList: document.getElementById("breaks-list"),
  eventLog: document.getElementById("event-log"),
};

function appendEvent(message) {
  const item = document.createElement("li");
  item.textContent = `${new Date().toLocaleTimeString()}  ${message}`;
  elements.eventLog.prepend(item);
  while (elements.eventLog.children.length > 18) {
    elements.eventLog.removeChild(elements.eventLog.lastChild);
  }
}

function setSupportStatus() {
  if (window.Hls && window.Hls.isSupported()) {
    elements.supportPill.textContent = "hls.js 로 재생";
    return;
  }
  if (elements.player.canPlayType("application/vnd.apple.mpegurl")) {
    elements.supportPill.textContent = "브라우저 네이티브 HLS";
    return;
  }
  elements.supportPill.textContent = "이 브라우저는 HLS 재생 불가";
}

async function createSession() {
  appendEvent("신규 SSAI 세션 요청");
  const response = await fetch("/session");
  if (!response.ok) {
    throw new Error(`세션 생성 실패: ${response.status}`);
  }
  const payload = await response.json();
  state.sessionId = payload.session_id;
  state.masterUrl = new URL(payload.master_url, window.location.origin).toString();
  elements.sessionId.textContent = payload.session_id;
  elements.masterUrl.textContent = state.masterUrl;
  appendEvent(`세션 생성 완료: ${payload.session_id}`);
  renderConfiguredBreaks(payload.breaks || []);
  return payload;
}

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`manifest fetch failed: ${response.status} ${url}`);
  }
  return response.text();
}

function parseMasterManifest(text, baseUrl) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const variants = [];
  let currentStreamInf = null;

  for (const line of lines) {
    if (line.startsWith("#EXT-X-STREAM-INF:")) {
      currentStreamInf = line.replace("#EXT-X-STREAM-INF:", "");
      continue;
    }
    if (line.startsWith("#")) {
      continue;
    }
    variants.push({
      attributes: currentStreamInf || "",
      url: new URL(line, baseUrl).toString(),
      label: currentStreamInf?.match(/RESOLUTION=([^,]+)/)?.[1] || line,
    });
    currentStreamInf = null;
  }

  return variants;
}

function parseAttributeList(value) {
  return Object.fromEntries(
    value.split(",").map((pair) => {
      const [key, ...rest] = pair.split("=");
      return [key, rest.join("=")];
    }),
  );
}

function parseMediaManifest(text, baseUrl) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const segments = [];
  const adBreaks = [];
  let currentDuration = null;
  let currentBreak = null;
  let mediaSequence = 0;

  for (const line of lines) {
    if (line.startsWith("#EXT-X-MEDIA-SEQUENCE:")) {
      mediaSequence = Number(line.split(":")[1]);
      continue;
    }
    if (line.startsWith("#EXT-X-DATERANGE:")) {
      const attrs = parseAttributeList(line.replace("#EXT-X-DATERANGE:", ""));
      currentBreak = {
        id: (attrs.ID || "ad-break").replaceAll('"', ""),
        duration: Number(attrs.DURATION || 0),
        startSegmentIndex: segments.length,
      };
      continue;
    }
    if (line.startsWith("#EXT-X-CUE-IN")) {
      if (currentBreak) {
        currentBreak.endSegmentIndex = segments.length - 1;
        adBreaks.push(currentBreak);
        currentBreak = null;
      }
      continue;
    }
    if (line.startsWith("#EXTINF:")) {
      currentDuration = Number(line.replace("#EXTINF:", "").split(",")[0]);
      continue;
    }
    if (line.startsWith("#")) {
      continue;
    }
    const isAd = Boolean(currentBreak);
    segments.push({
      index: mediaSequence + segments.length,
      duration: currentDuration ?? 0,
      url: new URL(line, baseUrl).toString(),
      kind: isAd ? "ad" : "content",
      breakId: currentBreak?.id || null,
    });
    currentDuration = null;
  }

  let elapsed = 0;
  for (const segment of segments) {
    segment.start = elapsed;
    elapsed += segment.duration;
    segment.end = elapsed;
  }

  for (const adBreak of adBreaks) {
    const items = segments.slice(adBreak.startSegmentIndex, adBreak.endSegmentIndex + 1);
    adBreak.segmentCount = items.length;
    adBreak.actualDuration = items.reduce((total, item) => total + item.duration, 0);
    adBreak.timelineStart = items[0]?.start ?? 0;
    adBreak.timelineEnd = items.at(-1)?.end ?? adBreak.timelineStart;
  }

  return { segments, adBreaks };
}

function renderConfiguredBreaks(breaks) {
  elements.breaksList.innerHTML = "";
  if (!breaks.length) {
    const item = document.createElement("li");
    item.textContent = "설정된 광고 구간 없음";
    elements.breaksList.appendChild(item);
    return;
  }

  for (const adBreak of breaks) {
    const item = document.createElement("li");
    item.innerHTML = `<strong>${adBreak.id}</strong><br>after segment ${adBreak.after_segments}<br>${adBreak.asset_playlist}`;
    elements.breaksList.appendChild(item);
  }
}

function renderVariants(variants) {
  elements.variantsList.innerHTML = "";
  if (!variants.length) {
    const item = document.createElement("li");
    item.textContent = "variant 없음";
    elements.variantsList.appendChild(item);
    return;
  }

  for (const variant of variants) {
    const item = document.createElement("li");
    item.innerHTML = `<strong>${variant.label}</strong><br>${variant.attributes}<br><code>${variant.url}</code>`;
    elements.variantsList.appendChild(item);
  }
}

function renderTimeline() {
  elements.timeline.innerHTML = "";
  elements.adBreaks.innerHTML = "";

  if (!state.segments.length) {
    const empty = document.createElement("div");
    empty.className = "break-card";
    empty.textContent = "manifest 분석 결과가 없습니다.";
    elements.adBreaks.appendChild(empty);
    return;
  }

  const totalDuration = state.segments.at(-1).end || 1;
  for (const [index, segment] of state.segments.entries()) {
    const node = document.createElement("div");
    node.className = `timeline-segment ${segment.kind}`;
    node.dataset.segmentIndex = String(index);
    node.style.flexGrow = String(Math.max(segment.duration, 1));
    node.innerHTML = `<span>${segment.kind === "ad" ? "AD" : "CONTENT"}<br>${segment.duration.toFixed(1)}s</span>`;
    elements.timeline.appendChild(node);
  }

  for (const adBreak of state.adBreaks) {
    const card = document.createElement("article");
    card.className = "break-card";
    const percent = ((adBreak.timelineStart / totalDuration) * 100).toFixed(1);
    card.innerHTML = `
      <strong>${adBreak.id}</strong>
      <p>${adBreak.segmentCount}개 광고 세그먼트, ${adBreak.actualDuration.toFixed(1)}초</p>
      <p>Playback ${adBreak.timelineStart.toFixed(1)}s 지점에서 시작 (${percent}%)</p>
    `;
    elements.adBreaks.appendChild(card);
  }
}

function updateActiveSegment(currentTime) {
  if (!state.segments.length) {
    return;
  }

  const nextIndex = state.segments.findIndex((segment) => currentTime >= segment.start && currentTime < segment.end);
  if (nextIndex === state.activeSegmentIndex || nextIndex < 0) {
    return;
  }

  state.activeSegmentIndex = nextIndex;
  for (const node of elements.timeline.children) {
    node.classList.toggle("active", node.dataset.segmentIndex === String(nextIndex));
  }

  const segment = state.segments[nextIndex];
  elements.currentPhase.textContent = segment.kind === "ad" ? `광고 재생 중 (${segment.breakId})` : "콘텐츠 재생 중";
  elements.currentSegment.textContent = `${segment.kind} / ${segment.duration.toFixed(1)}s / #${segment.index}`;
  appendEvent(`${segment.kind === "ad" ? "AD" : "CONTENT"} segment 진입: #${segment.index}`);
}

async function inspectSession() {
  if (!state.masterUrl) {
    return;
  }

  appendEvent("master manifest 분석 시작");
  const masterText = await fetchText(state.masterUrl);
  state.variants = parseMasterManifest(masterText, state.masterUrl);
  renderVariants(state.variants);

  const preferredVariant = state.variants[0];
  if (!preferredVariant) {
    throw new Error("사용 가능한 variant가 없습니다.");
  }

  state.variantUrl = preferredVariant.url;
  elements.variantUrl.textContent = state.variantUrl;
  appendEvent(`대표 variant 선택: ${preferredVariant.label}`);

  const mediaText = await fetchText(state.variantUrl);
  const parsed = parseMediaManifest(mediaText, state.variantUrl);
  state.segments = parsed.segments;
  state.adBreaks = parsed.adBreaks;
  renderTimeline();
  appendEvent(`media manifest 분석 완료: ${state.segments.length} segments / ${state.adBreaks.length} ad breaks`);
}

function destroyPlayer() {
  if (state.hls) {
    state.hls.destroy();
    state.hls = null;
  }
  elements.player.removeAttribute("src");
  elements.player.load();
}

function attachPlayerEvents() {
  elements.player.addEventListener("play", () => {
    elements.playbackState.textContent = "재생 중";
  });
  elements.player.addEventListener("pause", () => {
    elements.playbackState.textContent = "일시정지";
  });
  elements.player.addEventListener("waiting", () => {
    elements.playbackState.textContent = "버퍼링";
  });
  elements.player.addEventListener("timeupdate", () => {
    updateActiveSegment(elements.player.currentTime);
  });
  elements.player.addEventListener("error", () => {
    elements.playbackState.textContent = "재생 오류";
    appendEvent("비디오 엘리먼트 오류 발생");
  });
}

function loadPlayback(url) {
  destroyPlayer();

  if (window.Hls && window.Hls.isSupported()) {
    const hls = new window.Hls({
      enableWorker: true,
      lowLatencyMode: false,
    });
    hls.loadSource(url);
    hls.attachMedia(elements.player);
    hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
      appendEvent("hls.js manifest parsed");
      elements.playbackState.textContent = "준비 완료";
    });
    hls.on(window.Hls.Events.LEVEL_SWITCHED, (_, data) => {
      appendEvent(`ABR level switched: ${data.level}`);
    });
    hls.on(window.Hls.Events.ERROR, (_, data) => {
      appendEvent(`hls.js error: ${data.details}`);
    });
    state.hls = hls;
    return;
  }

  if (elements.player.canPlayType("application/vnd.apple.mpegurl")) {
    elements.player.src = url;
    elements.playbackState.textContent = "준비 완료";
    return;
  }

  throw new Error("이 브라우저는 HLS playback을 지원하지 않습니다.");
}

async function bootstrapSession() {
  elements.playbackState.textContent = "세션 준비 중";
  elements.currentPhase.textContent = "manifest 생성 중";
  const payload = await createSession();
  await inspectSession();
  loadPlayback(new URL(payload.master_url, window.location.origin).toString());
}

async function main() {
  setSupportStatus();
  attachPlayerEvents();

  elements.createSessionBtn.addEventListener("click", async () => {
    try {
      await bootstrapSession();
    } catch (error) {
      appendEvent(error.message);
      elements.playbackState.textContent = "실패";
    }
  });

  elements.reloadManifestBtn.addEventListener("click", async () => {
    try {
      await inspectSession();
    } catch (error) {
      appendEvent(error.message);
    }
  });

  try {
    await bootstrapSession();
  } catch (error) {
    appendEvent(error.message);
    elements.playbackState.textContent = "초기화 실패";
  }
}

main();
