const LIVE_ENDPOINT =
  "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained";

const SYSTEM_INSTRUCTION =
  "You are JARVIS, Bertrand's polished digital assistant. " +
  "Use calm British formality, be concise and practical, and address Bertrand as 'sir' when natural. " +
  "Use occasional dry wit without becoming rude. Prioritise privacy, safety, accuracy, and useful next steps. " +
  "For spoken replies, sound composed, natural, confident, and conversational.";

const VOICE_STORAGE_KEY = "jarvisGeminiVoice";
const DEFAULT_VOICE = "Charon";

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send");
const micButton = document.querySelector("#mic");
const voiceSelect = document.querySelector("#voice-select");
const voicePreview = document.querySelector("#voice-preview");
const liveToggle = document.querySelector("#live-toggle");
const voiceNote = document.querySelector("#voice-note");
const statusText = document.querySelector("#status-text");
const statusDot = document.querySelector("#status-dot");

const fallbackHistory = [];
let live = null;
let microphone = null;
let userTranscript = null;
let assistantTranscript = null;

function addMessage(role, text, transient = false) {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user" : "assistant"}`;
  if (transient) article.dataset.transient = "true";

  const label = document.createElement("strong");
  label.textContent = role === "user" ? "YOU" : "JARVIS";

  const p = document.createElement("p");
  p.textContent = text;

  article.append(label, p);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function setStatus(label, state = "online") {
  statusText.textContent = label;
  statusDot.dataset.state = state;
}

function selectedVoice() {
  return voiceSelect.value || DEFAULT_VOICE;
}

function transcriptChunk(role, text, finished = false) {
  if (!text) return;
  let holder = role === "user" ? userTranscript : assistantTranscript;

  if (!holder) {
    holder = { article: addMessage(role, ""), text: "" };
    if (role === "user") userTranscript = holder;
    else assistantTranscript = holder;
  }

  const clean = String(text).replace(/\s+/g, " ");
  if (clean.startsWith(holder.text)) {
    holder.text = clean;
  } else {
    const separator =
      holder.text && !holder.text.endsWith(" ") && !/^[,.;!?]/.test(clean) ? " " : "";
    holder.text += separator + clean;
  }
  holder.article.querySelector("p").textContent = holder.text.trim();

  if (finished) {
    if (role === "user") userTranscript = null;
    else assistantTranscript = null;
  }
}

function bytesToBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function base64ToInt16(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const view = new DataView(bytes.buffer);
  const pcm = new Int16Array(Math.floor(bytes.length / 2));
  for (let i = 0; i < pcm.length; i += 1) {
    pcm[i] = view.getInt16(i * 2, true);
  }
  return pcm;
}

function resampleFloat32(inputData, inputRate, outputRate) {
  if (inputRate === outputRate) return inputData;
  const ratio = inputRate / outputRate;
  const outputLength = Math.max(1, Math.round(inputData.length / ratio));
  const output = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i += 1) {
    const start = i * ratio;
    const end = Math.min((i + 1) * ratio, inputData.length);
    const first = Math.floor(start);
    const last = Math.max(first + 1, Math.ceil(end));
    let sum = 0;
    let weight = 0;

    for (let j = first; j < last && j < inputData.length; j += 1) {
      const segmentStart = Math.max(start, j);
      const segmentEnd = Math.min(end, j + 1);
      const segmentWeight = Math.max(0, segmentEnd - segmentStart);
      sum += inputData[j] * segmentWeight;
      weight += segmentWeight;
    }
    output[i] = weight ? sum / weight : inputData[Math.min(first, inputData.length - 1)];
  }
  return output;
}

function floatToPcm16Bytes(floatData) {
  const bytes = new Uint8Array(floatData.length * 2);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < floatData.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, floatData[i]));
    const intValue = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    view.setInt16(i * 2, Math.round(intValue), true);
  }
  return bytes;
}

class PcmPlayer {
  constructor() {
    this.context = null;
    this.nextStartTime = 0;
    this.sources = new Set();
  }

  async prepare() {
    if (!this.context || this.context.state === "closed") {
      this.context = new (window.AudioContext || window.webkitAudioContext)();
      this.nextStartTime = this.context.currentTime;
    }
    if (this.context.state === "suspended") {
      await this.context.resume();
    }
  }

  async play(base64Audio) {
    await this.prepare();
    const pcm = base64ToInt16(base64Audio);
    if (!pcm.length) return;

    const buffer = this.context.createBuffer(1, pcm.length, 24000);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i += 1) channel[i] = pcm[i] / 32768;

    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);
    const startAt = Math.max(this.context.currentTime + 0.015, this.nextStartTime);
    source.start(startAt);
    this.nextStartTime = startAt + buffer.duration;
    this.sources.add(source);
    source.onended = () => this.sources.delete(source);
  }

  interrupt() {
    for (const source of this.sources) {
      try {
        source.stop();
      } catch (_) {
        // Source may already have ended.
      }
    }
    this.sources.clear();
    if (this.context && this.context.state !== "closed") {
      this.nextStartTime = this.context.currentTime;
    }
  }
}

class MicrophoneStreamer {
  constructor(onChunk) {
    this.onChunk = onChunk;
    this.stream = null;
    this.context = null;
    this.source = null;
    this.processor = null;
    this.silentGain = null;
    this.active = false;
  }

  async start() {
    if (this.active) return;
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    this.context = new (window.AudioContext || window.webkitAudioContext)();
    this.source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    this.silentGain = this.context.createGain();
    this.silentGain.gain.value = 0;

    this.processor.onaudioprocess = (event) => {
      if (!this.active) return;
      const mono = event.inputBuffer.getChannelData(0);
      const resampled = resampleFloat32(mono, this.context.sampleRate, 16000);
      const pcmBytes = floatToPcm16Bytes(resampled);
      this.onChunk(bytesToBase64(pcmBytes));
    };

    this.source.connect(this.processor);
    this.processor.connect(this.silentGain);
    this.silentGain.connect(this.context.destination);
    this.active = true;
  }

  async stop() {
    if (!this.active && !this.stream) return;
    this.active = false;

    if (this.processor) {
      this.processor.onaudioprocess = null;
      this.processor.disconnect();
    }
    if (this.source) this.source.disconnect();
    if (this.silentGain) this.silentGain.disconnect();
    if (this.stream) this.stream.getTracks().forEach((track) => track.stop());
    if (this.context && this.context.state !== "closed") await this.context.close();

    this.stream = null;
    this.context = null;
    this.source = null;
    this.processor = null;
    this.silentGain = null;
  }
}

class GeminiLiveConnection {
  constructor(model, voice, token) {
    this.model = model;
    this.voice = voice;
    this.token = token;
    this.socket = null;
    this.connected = false;
    this.setupComplete = false;
    this.player = new PcmPlayer();
  }

  async connect() {
    await this.player.prepare();
    return new Promise((resolve, reject) => {
      let settled = false;
      const url = `${LIVE_ENDPOINT}?access_token=${encodeURIComponent(this.token)}`;
      this.socket = new WebSocket(url);

      const fail = (error) => {
        if (!settled) {
          settled = true;
          reject(error);
        }
      };

      const timeout = window.setTimeout(() => {
        fail(new Error("Gemini Live connection timed out."));
        this.close();
      }, 12000);

      this.socket.onopen = () => {
        this.connected = true;
        setStatus("Connecting…", "busy");
        this.send({
          setup: {
            model: `models/${this.model}`,
            generationConfig: {
              responseModalities: ["AUDIO"],
              speechConfig: {
                voiceConfig: {
                  prebuiltVoiceConfig: { voiceName: this.voice },
                },
              },
            },
            systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
            inputAudioTranscription: {},
            outputAudioTranscription: {},
          },
        });
      };

      this.socket.onmessage = async (event) => {
        let payload;
        try {
          const raw = event.data instanceof Blob ? await event.data.text() : event.data;
          payload = JSON.parse(raw);
        } catch (error) {
          console.error("Could not parse Gemini Live message", error);
          return;
        }

        if (payload.setupComplete) {
          this.setupComplete = true;
          window.clearTimeout(timeout);
          setStatus("Live", "online");
          if (!settled) {
            settled = true;
            resolve();
          }
        }

        const server = payload.serverContent;
        if (!server) return;

        if (server.inputTranscription?.text) {
          transcriptChunk("user", server.inputTranscription.text, Boolean(server.inputTranscription.finished));
        }
        if (server.outputTranscription?.text) {
          transcriptChunk(
            "assistant",
            server.outputTranscription.text,
            Boolean(server.outputTranscription.finished),
          );
        }

        const parts = server.modelTurn?.parts || [];
        for (const part of parts) {
          if (part.inlineData?.data) await this.player.play(part.inlineData.data);
          if (part.text) transcriptChunk("assistant", part.text, false);
        }

        if (server.interrupted) {
          this.player.interrupt();
          assistantTranscript = null;
        }
        if (server.turnComplete) {
          userTranscript = null;
          assistantTranscript = null;
        }
      };

      this.socket.onerror = () => {
        setStatus("Live error", "error");
        fail(new Error("Could not connect to Gemini Live."));
      };

      this.socket.onclose = (event) => {
        window.clearTimeout(timeout);
        this.connected = false;
        this.setupComplete = false;
        this.player.interrupt();
        if (live === this) live = null;
        if (microphone?.active) stopMicrophone(false);
        setStatus("Text mode", "offline");
        liveToggle.textContent = "Start Live";
        if (!settled) {
          fail(new Error(event.reason || "Gemini Live connection closed."));
        }
      };
    });
  }

  send(payload) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error("Gemini Live is not connected.");
    }
    this.socket.send(JSON.stringify(payload));
  }

  sendText(text) {
    this.send({ realtimeInput: { text } });
  }

  sendAudio(base64Audio) {
    if (!this.setupComplete) return;
    this.send({
      realtimeInput: {
        audio: {
          data: base64Audio,
          mimeType: "audio/pcm;rate=16000",
        },
      },
    });
  }

  endAudioStream() {
    if (this.setupComplete) this.send({ realtimeInput: { audioStreamEnd: true } });
  }

  close() {
    this.player.interrupt();
    if (this.socket && this.socket.readyState < WebSocket.CLOSING) this.socket.close(1000, "User ended session");
    this.connected = false;
    this.setupComplete = false;
  }
}

async function getLiveToken() {
  const response = await fetch("/api/live-token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not create Live token.");
  return data;
}

async function ensureLive() {
  if (live?.connected && live.setupComplete) return live;

  setStatus("Starting Live…", "busy");
  const tokenData = await getLiveToken();
  const connection = new GeminiLiveConnection(
    tokenData.model,
    selectedVoice(),
    tokenData.token,
  );
  live = connection;
  await connection.connect();
  liveToggle.textContent = "End Live";
  voiceNote.textContent =
    `Native Gemini audio is active with ${selectedVoice()}. The permanent API key remains on Render.`;
  return connection;
}

async function stopMicrophone(endStream = true) {
  if (!microphone) return;
  await microphone.stop();
  micButton.classList.remove("listening");
  micButton.textContent = "🎙";
  micButton.setAttribute("aria-pressed", "false");
  if (endStream && live?.setupComplete) {
    try {
      live.endAudioStream();
    } catch (_) {
      // Session may have closed while stopping.
    }
  }
  setStatus(live?.setupComplete ? "Live" : "Text mode", live?.setupComplete ? "online" : "offline");
}

async function startMicrophone() {
  const connection = await ensureLive();
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not support microphone capture.");
  }

  if (!microphone) {
    microphone = new MicrophoneStreamer((chunk) => {
      try {
        connection.sendAudio(chunk);
      } catch (error) {
        console.error("Audio send failed", error);
      }
    });
  }

  await microphone.start();
  micButton.classList.add("listening");
  micButton.textContent = "■";
  micButton.setAttribute("aria-pressed", "true");
  setStatus("Listening", "listening");
  voiceNote.textContent = "Gemini Live is listening. Speak naturally; you can interrupt JARVIS while it is talking.";
}

async function endLiveSession() {
  await stopMicrophone(true);
  if (live) {
    const closing = live;
    live = null;
    closing.close();
  }
  liveToggle.textContent = "Start Live";
  setStatus("Text mode", "offline");
}

async function fallbackText(text) {
  const pending = addMessage("assistant", "Thinking…", true);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: fallbackHistory }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    pending.dataset.transient = "false";
    pending.querySelector("p").textContent = data.reply;
    fallbackHistory.push({ role: "user", text }, { role: "model", text: data.reply });
    voiceNote.textContent = "Live audio was unavailable, so JARVIS answered in text mode.";
  } catch (error) {
    pending.querySelector("p").textContent = `Error: ${error.message}`;
  }
}

voiceSelect.value = localStorage.getItem(VOICE_STORAGE_KEY) || DEFAULT_VOICE;
if (!voiceSelect.value) voiceSelect.value = DEFAULT_VOICE;

voiceSelect.addEventListener("change", async () => {
  localStorage.setItem(VOICE_STORAGE_KEY, selectedVoice());
  voiceNote.textContent = `Selected Gemini voice: ${selectedVoice()}. It will apply to the next Live session.`;
  if (live) await endLiveSession();
});

voicePreview.addEventListener("click", async () => {
  voicePreview.disabled = true;
  try {
    const connection = await ensureLive();
    connection.sendText("Say exactly this short line: Good evening, sir. JARVIS voice systems are online.");
  } catch (error) {
    voiceNote.textContent = `Voice test failed: ${error.message}`;
  } finally {
    voicePreview.disabled = false;
  }
});

liveToggle.addEventListener("click", async () => {
  liveToggle.disabled = true;
  try {
    if (live?.connected) {
      await endLiveSession();
    } else {
      await ensureLive();
    }
  } catch (error) {
    voiceNote.textContent = `Live connection failed: ${error.message}`;
    setStatus("Text mode", "offline");
  } finally {
    liveToggle.disabled = false;
  }
});

micButton.addEventListener("click", async () => {
  micButton.disabled = true;
  try {
    if (microphone?.active) {
      await stopMicrophone(true);
    } else {
      await startMicrophone();
    }
  } catch (error) {
    voiceNote.textContent =
      error.name === "NotAllowedError"
        ? "Microphone permission was blocked. Allow microphone access and try again."
        : `Microphone error: ${error.message}`;
    setStatus(live?.setupComplete ? "Live" : "Text mode", live?.setupComplete ? "online" : "offline");
  } finally {
    micButton.disabled = false;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  addMessage("user", text);
  input.value = "";
  sendButton.disabled = true;

  try {
    const connection = await ensureLive();
    connection.sendText(text);
  } catch (error) {
    console.warn("Gemini Live unavailable; using text fallback", error);
    await fallbackText(text);
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
});

window.addEventListener("beforeunload", () => {
  if (live) live.close();
  if (microphone?.active) microphone.stop();
});

setStatus("Text mode", "offline");
