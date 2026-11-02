// Chế độ tự kiểm thử: thay micro bằng luồng âm thanh do trang tạo, phát lần lượt
// các câu khách mẫu (file giọng đọc) và chờ bot nói xong mới phát câu tiếp.
// Nạp TRƯỚC OMICallSDK vì SDK dò thiết bị micro ngay khi tải.
(() => {
  const ctx = new AudioContext();
  const dest = ctx.createMediaStreamDestination();
  const md = navigator.mediaDevices;
  const realGum = md.getUserMedia.bind(md);
  const realEnum = md.enumerateDevices.bind(md);

  md.getUserMedia = async (c) => {
    if (c?.video) return realGum(c);
    ctx.resume();
    // SDK dừng track khi gác máy, nên mỗi cuộc gọi nhận một bản sao
    return new MediaStream([dest.stream.getAudioTracks()[0].clone()]);
  };
  md.enumerateDevices = async () => {
    const list = await realEnum().catch(() => []);
    if (list.some((d) => d.kind === 'audioinput')) return list;
    return [...list, { deviceId: 'autotest', groupId: 'autotest', kind: 'audioinput', label: 'Giọng thử tự động', toJSON() { return this; } }];
  };

  const events = [];
  const t0 = () => (window.__webcall?.callStart ? Date.now() - window.__webcall.callStart : 0);
  const note = (type, data) => { events.push({ at: (t0() / 1000).toFixed(1), type, ...data }); console.log('[autotest]', type, data ?? ''); };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function loadBuffer(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Không tải được ${url}`);
    return ctx.decodeAudioData(await res.arrayBuffer());
  }
  function play(buf) {
    return new Promise((resolve) => {
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(dest);
      src.connect(ctx.destination); // để người ngồi cạnh nghe được câu khách
      src.onended = resolve;
      src.start();
    });
  }

  // Mức âm thanh phía bot, lấy mẫu bằng setInterval để vẫn chạy khi tab bị ẩn
  function botLevel(stream) {
    const an = ctx.createAnalyser();
    an.fftSize = 512;
    ctx.createMediaStreamSource(stream).connect(an);
    const buf = new Uint8Array(an.fftSize);
    return () => {
      an.getByteTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += ((v - 128) / 128) ** 2;
      return Math.sqrt(sum / buf.length);
    };
  }
  // Chờ bot bắt đầu nói (tối đa startMs), rồi chờ im lặng đủ silenceMs
  function waitBotTurn(level, { startMs = 12000, silenceMs = 1600, maxMs = 45000, thr = 0.02 } = {}) {
    return new Promise((resolve) => {
      const begin = Date.now();
      let spoke = 0, lastVoice = 0;
      const id = setInterval(() => {
        const now = Date.now();
        if (level() > thr) { spoke += 50; lastVoice = now; }
        const done =
          (spoke >= 300 && now - lastVoice >= silenceMs) ||
          (!spoke && now - begin >= startMs) ||
          now - begin >= maxMs;
        if (done || !window.__webcall?.call) {
          clearInterval(id);
          resolve({ spokeMs: spoke, waitedMs: now - begin });
        }
      }, 50);
    });
  }

  // Lượt chen ngang: chờ bot đã nói được speakMs rồi khách nói luôn, không đợi bot dứt câu
  function waitBotSpeaking(level, speakMs, { maxMs = 15000, thr = 0.02 } = {}) {
    return new Promise((resolve) => {
      const begin = Date.now();
      let spoke = 0;
      const id = setInterval(() => {
        if (level() > thr) spoke += 50;
        if (spoke >= speakMs || Date.now() - begin >= maxMs || !window.__webcall?.call) {
          clearInterval(id);
          resolve({ spokeMs: spoke, waitedMs: Date.now() - begin });
        }
      }, 50);
    });
  }

  function waitEvent(name, ms) {
    return new Promise((resolve) => {
      const timer = setTimeout(() => resolve(null), ms);
      OMICallSDK.on(name, (c) => { clearTimeout(timer); resolve(c); });
    });
  }

  async function run(planUrl) {
    events.length = 0; // mỗi ca (mỗi cuộc gọi) một dòng sự kiện riêng
    const state = (window.AutoTest.result = { status: 'running', plan: planUrl, events, transcript: [] });
    try {
      const base = new URL(planUrl, location.href);
      const plan = await (await fetch(base)).json();
      state.name = plan.name;
      const bufs = await Promise.all(plan.turns.map((t) => (t.audio ? loadBuffer(new URL(t.audio, base)) : null)));
      note('plan_loaded', { turns: plan.turns.length });

      const accepted = waitEvent('accepted', 45000);
      const ended = waitEvent('ended', 600000);
      await OMICallSDK.makeCall(window.__webcall.phoneNumber);
      note('dialing');
      const c = await accepted;
      if (!c) throw new Error('Bot không nhấc máy trong 45 giây');
      note('accepted');
      const level = botLevel(c.streams.remote);

      // Lượt thường: chờ bot nói xong rồi nói. {"bargeMs": n}: nói chen khi bot mới nói được n ms.
      // {"silence": n} (không có text): khách im lặng n ms để thử bot nhắc lại.
      for (let i = 0; i < plan.turns.length; i++) {
        const t = plan.turns[i];
        if (t.bargeMs) note('bot_turn_barge', await waitBotSpeaking(level, t.bargeMs));
        else note('bot_turn', await waitBotTurn(level));
        if (!window.__webcall.call) { note('ended_early', { beforeTurn: t.id }); break; }
        if (!bufs[i]) {
          note('silent', { id: t.id, ms: t.silence || 0 });
          await sleep(t.silence || 0);
          continue;
        }
        note(t.bargeMs ? 'barge_in' : 'say', { id: t.id, text: t.text });
        await play(bufs[i]);
      }
      if (window.__webcall.call) {
        note('bot_turn', await waitBotTurn(level));
        await sleep(1000);
        if (window.__webcall.call) { note('hangup_by_test'); window.__webcall.call.end(); }
      }
      const endedCall = await ended;
      // uuid cuộc gọi trên tổng đài: tra bản ghi chính thức bằng MCP get_call_detail
      state.callUuid = endedCall?.uuid || c.uuid || null;
      await sleep(2000); // chờ phụ đề chốt câu cuối
      state.status = 'done';
    } catch (e) {
      note('error', { message: e.message });
      state.status = 'error';
      state.error = e.message;
      window.__webcall?.call?.end();
    }
    state.transcript = window.__webcall.transcript();
    return state;
  }

  // ---------- Chế độ khách AI: Python điều khiển từng bước qua CDP ----------
  // begin() gọi máy → waitBot() chờ bot nói xong, trả câu bot (phụ đề) → say(url) phát câu khách
  // vừa sinh → ... → end() gác máy, trả kết quả như run().
  let live = null; // { state, call, level, ended, seen }

  async function begin(caseId) {
    events.length = 0;
    const state = (window.AutoTest.result = { status: 'running', plan: caseId, events, transcript: [] });
    const accepted = waitEvent('accepted', 45000);
    const ended = waitEvent('ended', 600000);
    await OMICallSDK.makeCall(window.__webcall.phoneNumber);
    note('dialing');
    const c = await accepted;
    if (!c) {
      note('error', { message: 'Bot không nhấc máy trong 45 giây' });
      Object.assign(state, { status: 'error', error: 'Bot không nhấc máy trong 45 giây' });
      window.__webcall?.call?.end();
      return false;
    }
    note('accepted');
    live = { state, call: c, level: botLevel(c.streams.remote), ended, seen: 0 };
    return true;
  }

  // Câu bot nói từ lượt khách gần nhất (gồm cả phần phụ đề đang nhận dạng dở)
  function botTextSince() {
    const lines = window.__webcall.transcript();
    let lastMe = -1;
    lines.forEach((l, i) => { if (l.who === 'me') lastMe = i; });
    const from = Math.max(lastMe + 1, live.seen);
    const text = lines.slice(from).filter((l) => l.who === 'bot').map((l) => l.text).join(' ');
    live.seen = lines.length;
    return text;
  }

  async function waitBot(opts) {
    const w = await waitBotTurn(live.level, opts);
    note('bot_turn', w);
    await sleep(600); // cho phụ đề chốt câu vừa nói
    return { ...w, ended: !window.__webcall.call, botText: botTextSince() };
  }

  async function say(url, text, id) {
    if (!window.__webcall.call) return false;
    note('say', { id, text });
    await play(await loadBuffer(url));
    return true;
  }

  async function end() {
    if (window.__webcall.call) { note('hangup_by_test'); window.__webcall.call.end(); }
    const endedCall = await live.ended;
    live.state.callUuid = endedCall?.uuid || live.call.uuid || null;
    await sleep(2000);
    live.state.status = live.state.status === 'running' ? 'done' : live.state.status;
    live.state.transcript = window.__webcall.transcript();
    return live.state;
  }

  window.AutoTest = { run, begin, waitBot, say, end, result: null };
})();
