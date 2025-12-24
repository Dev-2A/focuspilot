// ====== 상태/설정 (localStorage) ======
const LS = {
  sound: "fp_opt_sound",
  notify: "fp_opt_notify",
  autoBreak: "fp_opt_autobreak",

  mode: "fp_mode",                 // "focus" | "break"

  // auto-break (자동 시작) 용
  pendingBreak: "fp_pending_break", // "1"이면 리로드 후 break 자동 시작
  breakStartMs: "fp_break_start_ms",
  breakTotalSec: "fp_break_total_sec",

  // manual-break (대기) 용: break 모드에서 아직 시작 안 했을 때 표시할 남은 시간
  breakReadySec: "fp_break_ready_sec",
};

function lsGetBool(key, defVal) {
  const v = localStorage.getItem(key);
  if (v === null) return defVal;
  return v === "1";
}
function lsSetBool(key, val) {
  localStorage.setItem(key, val ? "1" : "0");
}
function lsGetStr(key, defVal) {
  const v = localStorage.getItem(key);
  return v === null ? defVal : v;
}
function lsSetStr(key, val) {
  localStorage.setItem(key, String(val));
}
function lsDel(key) {
  localStorage.removeItem(key);
}

const el = (id) => document.getElementById(id);

// ====== 카드 이동/포커스 ======
function scrollToCard(cardId) {
  const node = el(cardId);
  if (!node) return;
  node.scrollIntoView({ behavior: "smooth", block: "start" });
  node.classList.add("flash");
  setTimeout(() => node.classList.remove("flash"), 650);
}
function focusForTarget(cardId) {
  let target = null;
  if (cardId === "cardGoals") target = el("goal1") || el("goal2") || el("goal3");
  else if (cardId === "cardDistractions") target = el("distractionNote");
  else if (cardId === "cardTimer") target = el("startBtn");

  if (!target) return;
  setTimeout(() => { try { target.focus(); } catch (_) {} }, 350);
}

// ====== 타이머 ======
let timerId = null;
let remainingSec = 25 * 60;

let mode = "focus";                // "focus" or "break"
let sessionStart = null;           // focus 시작 시간 (local ISO)
let plannedFocusMin = 25;          // focus 시작 시점 집중(분)
let plannedBreakMin = 5;           // break 분
let isSubmitting = false;          // 중복 제출 방지

// WebAudio (짧은 비프)
let audioCtx = null;

function fmt(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
}

function setDisplay() {
  el("timerDisplay").textContent = fmt(remainingSec);
  const titlePrefix = mode === "focus" ? "Focus" : "Break";
  document.title = `${titlePrefix} · ${fmt(remainingSec)} - FocusPilot`;
}

function setModePill() {
  const pill = el("modePill");
  if (!pill) return;
  pill.textContent = mode === "focus" ? "Focus" : "Break";
}

// ====== 상태바(다음 행동 1줄) ======
function updateStatusBar(extra = {}) {
  const bar = el("statusBar");
  if (!bar) return;

  const goalsCount = parseInt(bar.dataset.goalsCount || "0", 10);
  const sessionsCount = parseInt(bar.dataset.sessionsCount || "0", 10);
  const distractionsCount = parseInt(bar.dataset.distractionsCount || "0", 10);

  const running = !!timerId;

  const statusText = el("statusText");
  const statusHint = el("statusHint");

  const m = extra.mode || mode;
  const rem = (typeof extra.remainingSec === "number") ? extra.remainingSec : remainingSec;

  let main = "";
  let hint = "";
  let target = "cardTimer";

  if (running) {
    target = "cardTimer";
    if (m === "focus") {
      main = `지금은 집중 중 · ${fmt(rem)}`;
      hint = "흐름 끊기면 방해요소에 한 줄만 적고 다시 돌아오자.";
    } else {
      main = `지금은 휴식 중 · ${fmt(rem)}`;
      hint = "물 한 잔. 스트레칭. (딴 짓은 금지, 그건 휴식이 아니라 납치야.)";
    }
  } else {
    // ✅ 모드 전환이 항상 존재하도록: break 모드면 휴식 안내가 우선
    if (m === "break") {
      target = "cardTimer";
      main = "휴식 모드야. Start를 눌러 휴식을 시작해.";
      hint = "휴식이 끝나면 Focus로 자동 전환돼.";
    } else if (sessionsCount === 0) {
      if (goalsCount === 0) {
        target = "cardGoals";
        main = "다음 행동: 목표 1개만 적고 Start.";
        hint = "3개 다 안 써도 됨. 1개면 충분.";
      } else {
        target = "cardTimer";
        main = "다음 행동: Start 눌러서 첫 세션을 기록하자.";
        hint = "완벽한 준비보다 시작이 먼저.";
      }
    } else {
      target = (goalsCount === 0) ? "cardGoals" : "cardTimer";
      if (goalsCount > 0) {
        main = `오늘 ${sessionsCount}개 세션 기록됨. 다음은 5분만 해도 OK.`;
      } else {
        main = `오늘 ${sessionsCount}개 세션 기록됨. 목표 1개만 적어도 좋아.`;
      }
      if (distractionsCount > 0) {
        hint = `방해요소 ${distractionsCount}개 기록됨. 다음엔 “한 줄 기록 → 복귀”만 하면 된다.`;
      } else {
        hint = "방해요소는 생기면 적어. 적는 순간 통제력이 생긴다.";
      }
    }
  }

  statusText.textContent = main;
  statusHint.textContent = hint;
  bar.dataset.target = target;
}

// ====== 버튼 상태 ======
function setButtons(running) {
  el("startBtn").disabled = running;
  el("pauseBtn").disabled = !running;

  el("finishBtn").disabled = !running;
  el("finishBtn").textContent = mode === "focus" ? "Finish" : "Skip";

  updateStatusBar();
}

function nowIsoLocal() {
  const d = new Date();
  d.setMilliseconds(0);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// ====== 알림/소리 ======
function ensureAudioCtx() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
}
function beep() {
  if (!lsGetBool(LS.sound, true)) return;
  try {
    ensureAudioCtx();
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type = "sine";
    o.frequency.value = 880;

    g.gain.value = 0.0001;
    o.connect(g);
    g.connect(audioCtx.destination);

    const t = audioCtx.currentTime;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.18, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);

    o.start(t);
    o.stop(t + 0.24);
  } catch (_) {}
}
function notify(title, body) {
  if (!lsGetBool(LS.notify, false)) return;
  if (!("Notification" in window)) return;
  if (Notification.permission === "granted") {
    try { new Notification(title, { body }); } catch (_) {}
  }
}

// ====== 설정 UI ======
function loadSettingsUI() {
  const sound = lsGetBool(LS.sound, true);
  const notifyOpt = lsGetBool(LS.notify, false);
  const autoBreak = lsGetBool(LS.autoBreak, false);

  el("optSound").checked = sound;
  el("optNotify").checked = notifyOpt;
  el("optAutoBreak").checked = autoBreak;

  el("optSound").addEventListener("change", (e) => {
    lsSetBool(LS.sound, e.target.checked);
    if (e.target.checked) {
      ensureAudioCtx();
      beep();
    }
  });

  el("optAutoBreak").addEventListener("change", (e) => {
    lsSetBool(LS.autoBreak, e.target.checked);
    updateStatusBar();
  });

  el("optNotify").addEventListener("change", async (e) => {
    const want = e.target.checked;
    if (!("Notification" in window)) {
      alert("이 브라우저는 데스크톱 알림을 지원하지 않아.");
      e.target.checked = false;
      lsSetBool(LS.notify, false);
      return;
    }
    if (!want) {
      lsSetBool(LS.notify, false);
      return;
    }
    if (Notification.permission === "granted") {
      lsSetBool(LS.notify, true);
      notify("FocusPilot", "데스크톱 알림이 켜졌어.");
      return;
    }
    if (Notification.permission === "denied") {
      alert("브라우저 알림이 차단돼 있어. 브라우저 설정에서 허용으로 바꿔야 해.");
      e.target.checked = false;
      lsSetBool(LS.notify, false);
      return;
    }
    try {
      const perm = await Notification.requestPermission();
      if (perm === "granted") {
        lsSetBool(LS.notify, true);
        notify("FocusPilot", "데스크톱 알림이 켜졌어.");
      } else {
        e.target.checked = false;
        lsSetBool(LS.notify, false);
      }
    } catch (_) {
      e.target.checked = false;
      lsSetBool(LS.notify, false);
    }
  });

  el("settingsBtn").addEventListener("click", () => {
    el("settingsPanel").classList.toggle("hidden");
  });
}

// ====== 모드/저장 헬퍼 ======
function prepareBreakPending(sec) {
  // ✅ 자동휴식 OFF에서도 break 모드가 "대기"로 존재해야 함
  lsSetStr(LS.mode, "break");
  lsSetStr(LS.breakReadySec, String(sec));

  // auto-start 플래그는 제거(수동 시작)
  lsDel(LS.pendingBreak);
  lsDel(LS.breakStartMs);
  lsDel(LS.breakTotalSec);
}

function prepareBreakAutoStart(totalSec) {
  // autoBreak ON일 때: 리로드 후 break 자동 시작
  lsSetStr(LS.mode, "break");
  lsSetStr(LS.pendingBreak, "1");
  lsSetStr(LS.breakStartMs, String(Date.now()));
  lsSetStr(LS.breakTotalSec, String(totalSec));

  // readySec는 참고용(표시)으로 남겨도 되고 없어도 됨. 여기선 남김.
  lsSetStr(LS.breakReadySec, String(totalSec));
}

function clearBreakStored() {
  lsDel(LS.pendingBreak);
  lsDel(LS.breakStartMs);
  lsDel(LS.breakTotalSec);
  lsDel(LS.breakReadySec);
}

function switchToFocusPending() {

  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }

  clearBreakStored();
  lsSetStr(LS.mode, "focus");

  mode = "focus";
  sessionStart = null;

  plannedFocusMin = parseInt(el("focusMinutes").value || "25", 10);
  remainingSec = plannedFocusMin * 60;

  setModePill();
  setButtons(false);
  setDisplay();
  updateStatusBar();
}

// ====== 타이머 동작 ======
function startTimer() {
  if (timerId) return;

  const focusMin = parseInt(el("focusMinutes").value || "25", 10);
  const breakMin = parseInt(el("breakMinutes").value || "5", 10);
  plannedBreakMin = breakMin;

  ensureAudioCtx();

  if (mode === "focus") {
    if (!sessionStart) {
      plannedFocusMin = focusMin;
      remainingSec = plannedFocusMin * 60;
      sessionStart = nowIsoLocal();
    }
  } else {
    // break 모드에서는 이미 대기 시간(remainingSec)을 표시 중이므로 리셋하지 않음
    if (remainingSec <= 0) remainingSec = plannedBreakMin * 60;
  }

  setModePill();
  setButtons(true);

  timerId = setInterval(() => {
    remainingSec -= 1;
    updateStatusBar({ mode, remainingSec });

    if (remainingSec <= 0) {
      remainingSec = 0;
      setDisplay();
      clearInterval(timerId);
      timerId = null;

      if (mode === "focus") {
        // ✅ Focus 완료 → 세션 저장 + Break 모드로 전환(대기/자동)
        beep();
        notify("집중 끝!", "휴식하거나 다음 세션을 시작해.");
        autoSaveFocusThenSwitchToBreak();
      } else {
        // ✅ Break 완료 → Focus 모드로 전환(대기)
        beep();
        notify("휴식 끝!", "다음 집중을 시작해볼까?");
        switchToFocusPending();
      }

      updateStatusBar();
      return;
    }

    setDisplay();
  }, 1000);

  setDisplay();
  updateStatusBar({ mode, remainingSec });
}

function pauseTimer() {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }
  setButtons(false);
  updateStatusBar();
}

function finishBtnAction() {
  if (mode === "focus") {
    // ✅ 수동 Finish도: 기록 남기고 Break로 전환(대기/자동)
    const usedSec = (plannedFocusMin * 60) - remainingSec;
    const usedMin = Math.max(1, Math.floor(usedSec / 60));

    el("sessionStartTs").value = sessionStart || nowIsoLocal();
    el("sessionEndTs").value = nowIsoLocal();
    el("sessionMinutes").value = usedMin;

    // 다음은 Break(대기). 자동휴식 ON이면 자동 시작하도록 준비.
    const totalBreakSec = plannedBreakMin * 60;
    if (lsGetBool(LS.autoBreak, false)) prepareBreakAutoStart(totalBreakSec);
    else prepareBreakPending(totalBreakSec);

    // UI는 제출 전에 정리(리로드되므로 크게 중요하진 않음)
    sessionStart = null;
    mode = "break";
    remainingSec = totalBreakSec;
    setModePill();
    setButtons(false);
    setDisplay();
    updateStatusBar();

    el("sessionForm").submit();
  } else {
    // break 중 Skip = 휴식 종료 → focus로 전환(대기)
    if (timerId) { clearInterval(timerId); timerId = null; }
    switchToFocusPending();
  }
}

function autoSaveFocusThenSwitchToBreak() {
  if (isSubmitting) return;
  isSubmitting = true;

  // focus 세션 저장
  el("sessionStartTs").value = sessionStart || nowIsoLocal();
  el("sessionEndTs").value = nowIsoLocal();
  el("sessionMinutes").value = plannedFocusMin;

  sessionStart = null;

  // ✅ 저장 후 Break로 전환 (autoBreak는 "자동 시작" 여부만 결정)
  const totalBreakSec = plannedBreakMin * 60;
  if (lsGetBool(LS.autoBreak, false)) prepareBreakAutoStart(totalBreakSec);
  else prepareBreakPending(totalBreakSec);

  // UI 정리(리로드되지만 깔끔하게)
  mode = "break";
  remainingSec = totalBreakSec;
  setModePill();
  setButtons(false);
  setDisplay();
  updateStatusBar();

  el("sessionForm").submit();
}

function restoreModeOnLoad() {
  const savedMode = lsGetStr(LS.mode, "focus");
  const autoBreak = lsGetBool(LS.autoBreak, false);

  if (savedMode === "break") {
    mode = "break";
    setModePill();

    // auto-start 조건: autoBreak ON + pendingBreak=1 + breakStartMs/totalSec 존재
    const pending = lsGetStr(LS.pendingBreak, "0") === "1";
    const startMs = parseInt(lsGetStr(LS.breakStartMs, "0"), 10);
    const totalSec = parseInt(lsGetStr(LS.breakTotalSec, "0"), 10);

    if (autoBreak && pending && startMs > 0 && totalSec > 0) {
      const elapsedSec = Math.floor((Date.now() - startMs) / 1000);
      const left = Math.max(0, totalSec - elapsedSec);
      remainingSec = left;

      setButtons(false);
      setDisplay();
      updateStatusBar();

      if (remainingSec <= 0) {
        // 휴식 시간이 이미 지났으면 즉시 focus로
        switchToFocusPending();
      } else {
        // 자동으로 휴식 시작
        startTimer();
      }
      return;
    }

    // manual pending: breakReadySec 우선 사용, 없으면 입력값 사용
    const readySec = parseInt(lsGetStr(LS.breakReadySec, "0"), 10);
    if (readySec > 0) remainingSec = readySec;
    else {
      plannedBreakMin = parseInt(el("breakMinutes").value || "5", 10);
      remainingSec = plannedBreakMin * 60;
    }

    setButtons(false);
    setDisplay();
    updateStatusBar();
    return;
  }

  // focus 모드
  mode = "focus";
  setModePill();
  plannedFocusMin = parseInt(el("focusMinutes").value || "25", 10);
  remainingSec = plannedFocusMin * 60;

  setButtons(false);
  setDisplay();
  updateStatusBar();
}

// ====== init ======
document.addEventListener("DOMContentLoaded", () => {
  loadSettingsUI();

  el("startBtn").addEventListener("click", startTimer);
  el("pauseBtn").addEventListener("click", pauseTimer);
  el("finishBtn").addEventListener("click", finishBtnAction);

  // StatusBar 클릭 → 다음 행동 카드로 이동 + 포커스
  const bar = el("statusBar");
  if (bar) {
    bar.style.cursor = "pointer";
    bar.addEventListener("click", () => {
      const target = bar.dataset.target || "cardTimer";
      scrollToCard(target);
      focusForTarget(target);
    });
  }

  restoreModeOnLoad();
});
