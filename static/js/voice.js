import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.0';

const MAX_RECORD_SECONDS = 30;
const TARGET_SAMPLE_RATE = 16000;

function mergeFloat32Arrays(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
}

function resampleTo16k(audioData, sampleRate) {
  if (sampleRate === TARGET_SAMPLE_RATE) {
    return audioData;
  }
  const ratio = sampleRate / TARGET_SAMPLE_RATE;
  const newLength = Math.round(audioData.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i += 1) {
    const srcIndex = i * ratio;
    const idx = Math.floor(srcIndex);
    const frac = srcIndex - idx;
    const a = audioData[idx] || 0;
    const b = audioData[idx + 1] || a;
    result[i] = a + frac * (b - a);
  }
  return result;
}

function stopMediaStream(stream) {
  if (!stream) return;
  stream.getTracks().forEach((track) => track.stop());
}

class VoiceApp {
  constructor(root) {
    this.root = root;
    this.csrf = root.dataset.csrf || '';
    this.isLoggedIn = root.dataset.loggedIn === 'true';
    this.loginUrl = root.dataset.loginUrl || '/login';
    this.phrasebookUrl = root.dataset.phrasebookUrl || '/phrasebook';

    this.sourceLang = 'en';
    this.transcriber = null;
    this.isModelReady = false;
    this.isRecording = false;
    this.isBusy = false;

    this.mediaStream = null;
    this.audioContext = null;
    this.processor = null;
    this.sourceNode = null;
    this.audioChunks = [];
    this.recordTimer = null;

    this.lastResult = null;

    this.micBtn = document.getElementById('voice-mic-btn');
    this.micHint = document.getElementById('voice-mic-hint');
    this.modelStatus = document.getElementById('voice-model-status');
    this.modelStatusText = this.modelStatus?.querySelector('.voice-model-status-text');
    this.progressWrap = this.modelStatus?.querySelector('.voice-model-progress');
    this.progressBar = document.getElementById('voice-model-progress-bar');
    this.errorEl = document.getElementById('voice-error');
    this.transcriptCard = document.getElementById('voice-transcript-card');
    this.transcriptInput = document.getElementById('voice-transcript');
    this.translateBtn = document.getElementById('voice-translate-btn');
    this.retryBtn = document.getElementById('voice-retry-btn');
    this.resultsCard = document.getElementById('voice-results');
    this.spokenLabel = document.getElementById('voice-spoken-label');
    this.translatedLabel = document.getElementById('voice-translated-label');
    this.spokenText = document.getElementById('voice-spoken-text');
    this.translatedText = document.getElementById('voice-translated-text');
    this.saveBtn = document.getElementById('voice-save-btn');
    this.saveStatus = document.getElementById('voice-save-status');
    this.phrasebookLink = document.getElementById('voice-phrasebook-link');
    this.emptyState = document.getElementById('voice-empty-state');
    this.directionBtns = root.querySelectorAll('.voice-direction-btn');

    this.bindEvents();
    this.loadModel();
  }

  bindEvents() {
    this.directionBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.setDirection(btn.dataset.sourceLang);
      });
    });

    if (this.micBtn) {
      const stopEvents = ['pointerdown', 'pointerup', 'pointercancel', 'click'];
      stopEvents.forEach((eventName) => {
        this.micBtn.addEventListener(eventName, (e) => e.stopPropagation());
      });

      this.micBtn.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        if (this.micBtn.disabled || this.isBusy) return;
        this.startRecording();
      });

      this.micBtn.addEventListener('pointerup', () => this.stopRecording());
      this.micBtn.addEventListener('pointercancel', () => this.stopRecording());
      this.micBtn.addEventListener('pointerleave', () => {
        if (this.isRecording) this.stopRecording();
      });
    }

    this.translateBtn?.addEventListener('click', () => this.translateTranscript());
    this.retryBtn?.addEventListener('click', () => this.resetToIdle());
    this.saveBtn?.addEventListener('click', () => this.savePhrase());
  }

  setDirection(lang) {
    if (lang !== 'en' && lang !== 'es') return;
    this.sourceLang = lang;
    this.directionBtns.forEach((btn) => {
      const active = btn.dataset.sourceLang === lang;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  setError(message) {
    if (!this.errorEl) return;
    if (!message) {
      this.errorEl.textContent = '';
      this.errorEl.classList.add('hidden');
      return;
    }
    this.errorEl.textContent = message;
    this.errorEl.classList.remove('hidden');
  }

  setModelStatus(message) {
    if (this.modelStatusText) {
      this.modelStatusText.textContent = message;
    }
  }

  updateProgress(progress) {
    if (!this.progressWrap || !this.progressBar) return;
    if (progress.status === 'progress' && typeof progress.progress === 'number') {
      this.progressWrap.hidden = false;
      const pct = Math.min(100, Math.round(progress.progress * 100));
      this.progressBar.style.width = `${pct}%`;
      this.setModelStatus(`Descargando modelo… ${pct}%`);
    } else if (progress.status === 'done') {
      this.progressBar.style.width = '100%';
    }
  }

  async loadModel() {
    env.allowLocalModels = false;
    const progressCallback = (progress) => this.updateProgress(progress);

    try {
      this.setModelStatus('Cargando modelo de voz…');
      try {
        this.transcriber = await pipeline(
          'automatic-speech-recognition',
          'Xenova/whisper-tiny',
          { device: 'webgpu', progress_callback: progressCallback }
        );
      } catch (webgpuError) {
        console.warn('WebGPU unavailable, using WASM:', webgpuError);
        this.transcriber = await pipeline(
          'automatic-speech-recognition',
          'Xenova/whisper-tiny',
          { progress_callback: progressCallback }
        );
      }

      this.isModelReady = true;
      if (this.progressWrap) this.progressWrap.hidden = true;
      this.setModelStatus('Modelo listo');
      if (this.micBtn) this.micBtn.disabled = false;
      if (this.micHint) {
        this.micHint.textContent = 'Mantén pulsado para hablar';
      }
    } catch (err) {
      console.error('Whisper model load failed:', err);
      this.setModelStatus('No se pudo cargar el modelo de voz.');
      if (this.micHint) {
        this.micHint.textContent = 'Recarga la página e inténtalo de nuevo.';
      }
      this.setError(
        'No se pudo cargar Whisper. Comprueba tu conexión y recarga la página.'
      );
    }
  }

  async ensureMicAccess() {
    if (this.mediaStream) return this.mediaStream;
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      return this.mediaStream;
    } catch (err) {
      console.error('Microphone access denied:', err);
      this.setError(
        'No se pudo acceder al micrófono. Permite el acceso en tu navegador o escribe frases en el libro de frases.'
      );
      return null;
    }
  }

  async startRecording() {
    if (!this.isModelReady || this.isRecording || this.isBusy) return;

    const stream = await this.ensureMicAccess();
    if (!stream) return;

    this.setError('');
    this.isRecording = true;
    document.body.classList.add('voice-recording');
    this.micBtn?.classList.add('is-recording');
    if (this.micHint) this.micHint.textContent = 'Grabando… suelta para transcribir';

    this.audioChunks = [];
    this.audioContext = new AudioContext();
    this.sourceNode = this.audioContext.createMediaStreamSource(stream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (event) => {
      if (!this.isRecording) return;
      const channel = event.inputBuffer.getChannelData(0);
      this.audioChunks.push(new Float32Array(channel));
    };

    this.sourceNode.connect(this.processor);
    this.processor.connect(this.audioContext.destination);

    this.recordTimer = window.setTimeout(() => {
      if (this.isRecording) this.stopRecording();
    }, MAX_RECORD_SECONDS * 1000);
  }

  cleanupRecordingGraph() {
    if (this.recordTimer) {
      window.clearTimeout(this.recordTimer);
      this.recordTimer = null;
    }
    if (this.processor) {
      this.processor.disconnect();
      this.processor.onaudioprocess = null;
      this.processor = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
  }

  async stopRecording() {
    if (!this.isRecording) return;

    this.isRecording = false;
    document.body.classList.remove('voice-recording');
    this.micBtn?.classList.remove('is-recording');

    const sampleRate = this.audioContext?.sampleRate || TARGET_SAMPLE_RATE;
    this.cleanupRecordingGraph();
    const rawAudio = mergeFloat32Arrays(this.audioChunks);
    this.audioChunks = [];

    if (!rawAudio.length) {
      if (this.micHint) this.micHint.textContent = 'No se detectó audio. Inténtalo de nuevo.';
      return;
    }

    const audio = resampleTo16k(rawAudio, sampleRate);
    await this.transcribeAudio(audio);
  }

  async transcribeAudio(audio) {
    if (!this.transcriber) return;

    this.isBusy = true;
    if (this.micBtn) this.micBtn.disabled = true;
    if (this.micHint) this.micHint.textContent = 'Transcribiendo…';

    try {
      const output = await this.transcriber(audio, {
        language: this.sourceLang,
        task: 'transcribe',
      });
      const text = (output?.text || '').trim();

      if (!text) {
        this.setError('No se entendió el audio. Inténtalo de nuevo.');
        return;
      }

      if (this.emptyState) this.emptyState.classList.add('hidden');
      if (this.transcriptCard) this.transcriptCard.classList.remove('hidden');
      if (this.transcriptInput) this.transcriptInput.value = text;

      await this.translateText(text);
    } catch (err) {
      console.error('Transcription failed:', err);
      this.setError('Error al transcribir. Inténtalo de nuevo.');
    } finally {
      this.isBusy = false;
      if (this.micBtn && this.isModelReady) this.micBtn.disabled = false;
      if (this.micHint) this.micHint.textContent = 'Mantén pulsado para hablar';
    }
  }

  async translateTranscript() {
    const text = (this.transcriptInput?.value || '').trim();
    if (!text) {
      this.setError('Escribe o dicta una frase antes de traducir.');
      return;
    }
    await this.translateText(text);
  }

  async translateText(text) {
    this.isBusy = true;
    if (this.translateBtn) this.translateBtn.disabled = true;
    this.setError('');

    try {
      const response = await fetch('/voice/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrf,
        },
        body: JSON.stringify({ text, source_lang: this.sourceLang }),
      });
      const data = await response.json();
      if (!response.ok) {
        this.setError(data.error || 'No se pudo traducir.');
        return;
      }
      this.showResult(data);
    } catch (err) {
      console.error('Translate failed:', err);
      this.setError('No se pudo traducir. Comprueba tu conexión.');
    } finally {
      this.isBusy = false;
      if (this.translateBtn) this.translateBtn.disabled = false;
    }
  }

  showResult(data) {
    this.lastResult = data;
    if (this.resultsCard) this.resultsCard.classList.remove('hidden');

    const spokenLabel = data.source_lang === 'en' ? 'Inglés' : 'Español';
    const translatedLabel = data.target_lang === 'en' ? 'Inglés' : 'Español';

    if (this.spokenLabel) this.spokenLabel.textContent = spokenLabel;
    if (this.translatedLabel) this.translatedLabel.textContent = translatedLabel;
    if (this.spokenText) this.spokenText.textContent = data.spoken;
    if (this.translatedText) this.translatedText.textContent = data.translated;

    if (this.saveStatus) {
      this.saveStatus.textContent = '';
      this.saveStatus.classList.add('hidden');
    }
    if (this.phrasebookLink) this.phrasebookLink.hidden = true;
  }

  resetToIdle() {
    this.lastResult = null;
    if (this.transcriptCard) this.transcriptCard.classList.add('hidden');
    if (this.resultsCard) this.resultsCard.classList.add('hidden');
    if (this.transcriptInput) this.transcriptInput.value = '';
    if (this.emptyState) this.emptyState.classList.remove('hidden');
    this.setError('');
    if (this.saveStatus) {
      this.saveStatus.textContent = '';
      this.saveStatus.classList.add('hidden');
    }
    if (this.phrasebookLink) this.phrasebookLink.hidden = true;
  }

  async savePhrase() {
    if (!this.isLoggedIn) {
      window.location.href = this.loginUrl;
      return;
    }
    if (!this.lastResult) return;

    this.isBusy = true;
    if (this.saveBtn) this.saveBtn.disabled = true;
    this.setError('');

    try {
      const response = await fetch('/voice/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrf,
        },
        body: JSON.stringify({
          spoken: this.lastResult.spoken,
          translated: this.lastResult.translated,
          source_lang: this.lastResult.source_lang,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        this.setError(data.error || 'No se pudo guardar la frase.');
        return;
      }
      if (this.saveStatus) {
        this.saveStatus.textContent = 'Frase guardada en tu libro.';
        this.saveStatus.classList.remove('hidden');
      }
      if (this.phrasebookLink) this.phrasebookLink.hidden = false;
    } catch (err) {
      console.error('Save failed:', err);
      this.setError('No se pudo guardar la frase.');
    } finally {
      this.isBusy = false;
      if (this.saveBtn) this.saveBtn.disabled = false;
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('voice-app');
  if (root) {
    new VoiceApp(root);
  }
});
