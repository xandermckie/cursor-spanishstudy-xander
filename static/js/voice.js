import { translateDirect } from './translation-client.js';

const MAX_RECORD_SECONDS = 15;
const TRANSLATE_TIMEOUT_MS = 35000;
const IDLE_HINT = 'Mantén pulsado el micrófono para hablar';
const IDLE_HINT_DESKTOP = 'Pulsa el micrófono para hablar';

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function isMobileOrLowMemory() {
  const mobileMq = window.matchMedia('(max-width: 900px)').matches;
  const lowMem =
    typeof navigator.deviceMemory === 'number' && navigator.deviceMemory <= 4;
  const ua = navigator.userAgent || '';
  const iosSafari =
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  return mobileMq || lowMem || iosSafari;
}

function isTouchPrimary() {
  return (
    window.matchMedia('(pointer: coarse)').matches ||
    (navigator.maxTouchPoints > 0 && window.matchMedia('(max-width: 1200px)').matches)
  );
}

function prefersWebSpeech(root) {
  if (root?.dataset?.preferWebspeech === 'true') {
    return true;
  }
  return isMobileOrLowMemory() || isTouchPrimary();
}

function detectSpeechBackendKind(root) {
  const SpeechRecognition = getSpeechRecognitionCtor();
  const useWebSpeech = prefersWebSpeech(root);

  if (useWebSpeech && SpeechRecognition) {
    return 'webspeech';
  }
  if (!useWebSpeech) {
    return 'whisper';
  }
  if (SpeechRecognition) {
    return 'webspeech';
  }
  return 'none';
}

class WebSpeechBackend {
  constructor() {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      throw new Error('Web Speech API no disponible');
    }
    this.recognition = new Ctor();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.isListening = false;
    this.sessionActive = false;
    this.stopPromise = null;
    this._bindHandlers();
  }

  get kind() {
    return 'webspeech';
  }

  get ready() {
    return true;
  }

  async load() {
    return undefined;
  }

  _bindHandlers() {
    this.recognition.onresult = (event) => {
      let interim = '';
      let finalPart = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalPart += text;
        } else {
          interim += text;
        }
      }
      if (finalPart) {
        this.finalTranscript += finalPart;
      }
      this.interimTranscript = interim;
    };

    this.recognition.onerror = (event) => {
      if (event.error === 'aborted') return;
      this.isListening = false;
      if (this.stopPromise) {
        const { reject } = this.stopPromise;
        this.stopPromise = null;
        if (event.error === 'not-allowed') {
          reject(new Error('No se pudo acceder al micrófono. Permite el acceso en tu navegador.'));
        } else if (event.error === 'no-speech') {
          reject(new Error('No se detectó voz. Inténtalo de nuevo.'));
        } else {
          reject(new Error('Error de reconocimiento. Inténtalo de nuevo.'));
        }
      }
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (this.sessionActive && !this.stopPromise) {
        try {
          this.recognition.start();
        } catch (err) {
          if (!err || err.name !== 'InvalidStateError') {
            console.warn('Web Speech restart failed:', err);
          }
        }
        return;
      }
      if (this.stopPromise) {
        const { resolve } = this.stopPromise;
        this.stopPromise = null;
        const text = (this.finalTranscript + this.interimTranscript).trim();
        resolve(text);
      }
    };

    this.recognition.onstart = () => {
      this.isListening = true;
    };
  }

  async start(lang) {
    this.sessionActive = true;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.recognition.lang = lang === 'es' ? 'es-ES' : 'en-US';
    return new Promise((resolve, reject) => {
      const previousOnStart = this.recognition.onstart;
      this.recognition.onstart = () => {
        this.recognition.onstart = previousOnStart;
        if (previousOnStart) previousOnStart.call(this.recognition);
        resolve();
      };
      try {
        this.recognition.start();
      } catch (err) {
        this.recognition.onstart = previousOnStart;
        if (err && err.name === 'InvalidStateError') {
          resolve();
          return;
        }
        reject(err);
      }
    });
  }

  async stop() {
    this.sessionActive = false;
    if (!this.isListening && !this.stopPromise) {
      return (this.finalTranscript + this.interimTranscript).trim();
    }
    return new Promise((resolve, reject) => {
      this.stopPromise = { resolve, reject };
      try {
        this.recognition.stop();
      } catch {
        this.stopPromise = null;
        resolve((this.finalTranscript + this.interimTranscript).trim());
      }
    });
  }

  dispose() {
    try {
      this.recognition.abort();
    } catch {
      /* ignore */
    }
  }
}

class VoiceApp {
  constructor(root) {
    this.root = root;
    this.csrf = root.dataset.csrf || '';
    this.isLoggedIn = root.dataset.loggedIn === 'true';
    this.loginUrl = root.dataset.loginUrl || '/login';
    this.phrasebookUrl = root.dataset.phrasebookUrl || '/phrasebook';
    this.backendKind = detectSpeechBackendKind(root);
    this.useHoldToTalk = isTouchPrimary() || root.dataset.preferWebspeech === 'true';

    this.sourceLang = 'en';
    this.backend = null;
    this.whisperModulePromise = null;
    this.isRecording = false;
    this.isWarmingUp = false;
    this.isBusy = false;
    this.translateAbort = null;
    this.recordTimer = null;

    this.lastResult = null;

    this.micBtn = document.getElementById('voice-mic-btn');
    this.micHint = document.getElementById('voice-mic-hint');
    this.modelStatus = document.getElementById('voice-model-status');
    this.modelStatusText = this.modelStatus?.querySelector('.voice-model-status-text');
    this.progressWrap = this.modelStatus?.querySelector('.voice-model-progress');
    this.progressBar = document.getElementById('voice-model-progress-bar');
    this.unsupportedEl = document.getElementById('voice-unsupported');
    this.errorEl = document.getElementById('voice-error');
    this.transcriptCard = document.getElementById('voice-transcript-card');
    this.transcriptInput = document.getElementById('voice-transcript');
    this.translateBtn = document.getElementById('voice-translate-btn');
    this.cancelTranslateBtn = document.getElementById('voice-cancel-translate-btn');
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
    this.emptyStateNote = document.getElementById('voice-empty-note');
    this.directionBtns = root.querySelectorAll('.voice-direction-btn');

    root.dataset.speechBackend = this.backendKind;

    this.bindEvents();
    this.initBackend();
  }

  whisperUi() {
    return {
      setModelStatus: (msg) => this.setModelStatus(msg),
      updateProgress: (progress) => this.updateProgress(progress),
      progressWrap: this.progressWrap,
    };
  }

  async ensureWhisperBackend() {
    if (this.backend) return this.backend;
    if (!this.whisperModulePromise) {
      this.whisperModulePromise = import('./voice-whisper.js');
    }
    const { WhisperBackend } = await this.whisperModulePromise;
    this.backend = new WhisperBackend(this.whisperUi());
    return this.backend;
  }

  bindEvents() {
    this.directionBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.setDirection(btn.dataset.sourceLang);
      });
    });

    if (this.micBtn) {
      if (this.useHoldToTalk) {
        this.micBtn.addEventListener('pointerdown', (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (this.micBtn.disabled || this.isBusy || this.isRecording || this.isWarmingUp) {
            return;
          }
          this.micBtn.setPointerCapture(e.pointerId);
          this.beginRecording();
        });
        this.micBtn.addEventListener('pointerup', (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (this.isRecording) {
            this.endRecording();
          }
        });
        this.micBtn.addEventListener('pointercancel', (e) => {
          e.preventDefault();
          if (this.isRecording) {
            this.endRecording();
          }
        });
      } else {
        this.micBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          if (this.micBtn.disabled || this.isBusy || this.isWarmingUp) return;
          if (this.isRecording) {
            this.endRecording();
          } else {
            this.beginRecording();
          }
        });
      }
    }

    this.translateBtn?.addEventListener('click', () => this.translateTranscript());
    this.cancelTranslateBtn?.addEventListener('click', () => this.cancelTranslate());
    this.retryBtn?.addEventListener('click', () => this.resetToIdle());
    this.saveBtn?.addEventListener('click', () => this.savePhrase());
  }

  initBackend() {
    if (this.backendKind === 'none') {
      this.showUnsupported();
      return;
    }

    try {
      if (this.backendKind === 'webspeech') {
        this.backend = new WebSpeechBackend();
        if (this.progressWrap) this.progressWrap.hidden = true;
        this.setModelStatus('Usando reconocimiento del navegador');
        if (this.micBtn) this.micBtn.disabled = false;
        this.setIdleHint();
        if (this.emptyStateNote) {
          this.emptyStateNote.textContent =
            'En móvil usamos el micrófono del navegador. Mantén pulsado el botón mientras hablas.';
        }
      } else {
        if (this.progressWrap) this.progressWrap.hidden = true;
        this.setModelStatus('Pulsa el micrófono para cargar Whisper');
        if (this.micBtn) this.micBtn.disabled = false;
        this.setIdleHint();
        if (this.emptyStateNote) {
          this.emptyStateNote.textContent =
            'La primera grabación descarga ~40 MB del modelo Whisper; luego queda en caché.';
        }
      }
    } catch (err) {
      console.error('Backend init failed:', err);
      this.showUnsupported();
      this.setError(err.message || 'Reconocimiento de voz no disponible.');
    }
  }

  showUnsupported() {
    if (this.unsupportedEl) this.unsupportedEl.classList.remove('hidden');
    if (this.micBtn) this.micBtn.disabled = true;
    this.setModelStatus('Reconocimiento de voz no disponible');
    if (this.micHint) {
      this.micHint.textContent = 'Escribe tu frase abajo y pulsa Traducir.';
    }
    if (this.transcriptCard) this.transcriptCard.classList.remove('hidden');
    if (this.emptyState) this.emptyState.classList.add('hidden');
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

  setError(message, scroll = true) {
    if (!this.errorEl) return;
    if (!message) {
      this.errorEl.textContent = '';
      this.errorEl.classList.add('hidden');
      return;
    }
    this.errorEl.textContent = message;
    this.errorEl.classList.remove('hidden');
    if (scroll) {
      this.errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  setModelStatus(message) {
    if (this.modelStatusText) {
      this.modelStatusText.textContent = message;
    }
  }

  setIdleHint() {
    if (this.micHint) {
      this.micHint.textContent = this.useHoldToTalk ? IDLE_HINT : IDLE_HINT_DESKTOP;
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

  micIsReady() {
    if (this.backendKind === 'none') return false;
    if (this.backendKind === 'webspeech') return !!this.backend;
    return !this.isWarmingUp && !this.isBusy;
  }

  async beginRecording() {
    if (this.isBusy || this.isRecording || this.isWarmingUp) return;

    this.isWarmingUp = true;
    if (this.micHint) this.micHint.textContent = 'Espera, preparando…';
    if (this.micBtn) this.micBtn.disabled = true;

    try {
      if (this.backendKind === 'whisper') {
        await this.ensureWhisperBackend();
        if (!this.backend.ready) {
          await this.backend.load();
        }
      } else if (!this.backend) {
        return;
      }

      this.setError('');
      if (this.resultsCard) this.resultsCard.classList.add('hidden');
      this.lastResult = null;

      await this.backend.start(this.sourceLang);

      this.isRecording = true;
      document.body.classList.add('voice-recording');
      this.micBtn?.classList.add('is-recording');
      if (this.micHint) {
        this.micHint.textContent = this.useHoldToTalk
          ? 'Escuchando… suelta para terminar'
          : 'Escuchando… pulsa de nuevo para terminar';
      }
      if (this.micBtn) {
        this.micBtn.setAttribute('aria-label', 'Pulsa para dejar de grabar');
        this.micBtn.disabled = false;
      }

      this.recordTimer = window.setTimeout(() => {
        if (this.isRecording) this.endRecording();
      }, MAX_RECORD_SECONDS * 1000);
    } catch (err) {
      console.error('Start recording failed:', err);
      this.setError(
        err.message || 'No se pudo iniciar la grabación. Inténtalo de nuevo.'
      );
      this.setIdleHint();
      if (this.micBtn) this.micBtn.disabled = !this.micIsReady();
    } finally {
      this.isWarmingUp = false;
    }
  }

  async endRecording() {
    if (this.isWarmingUp || !this.isRecording || !this.backend) return;

    if (this.recordTimer) {
      window.clearTimeout(this.recordTimer);
      this.recordTimer = null;
    }

    this.isRecording = false;
    document.body.classList.remove('voice-recording');
    this.micBtn?.classList.remove('is-recording');
    if (this.micBtn) {
      this.micBtn.setAttribute('aria-label', 'Pulsa para hablar');
      this.micBtn.disabled = true;
    }
    if (this.micHint) this.micHint.textContent = 'Transcribiendo…';

    this.isBusy = true;
    if (this.translateBtn) this.translateBtn.disabled = true;

    try {
      const text = await this.backend.stop();
      if (!text) {
        this.setError('No se detectó audio. Inténtalo de nuevo.', false);
        this.setIdleHint();
        return;
      }
      this.showTranscript(text);
    } catch (err) {
      console.error('Stop recording failed:', err);
      this.setError(err.message || 'Error al transcribir. Inténtalo de nuevo.');
      this.setIdleHint();
    } finally {
      this.isBusy = false;
      if (this.micBtn && this.micIsReady()) this.micBtn.disabled = false;
      if (this.translateBtn) this.translateBtn.disabled = false;
    }
  }

  showTranscript(text) {
    if (this.emptyState) this.emptyState.classList.add('hidden');
    if (this.transcriptCard) {
      this.transcriptCard.classList.remove('hidden');
      this.transcriptCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (this.transcriptInput) this.transcriptInput.value = text;
    if (this.micHint) this.micHint.textContent = 'Revisa el texto y pulsa Traducir';
  }

  async translateTranscript() {
    const text = (this.transcriptInput?.value || '').trim();
    if (!text) {
      this.setError('Escribe o dicta una frase antes de traducir.');
      return;
    }
    await this.translateText(text);
  }

  cancelTranslate() {
    if (this.translateAbort) {
      this.translateAbort.abort();
    }
  }

  async parseJsonResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      return { error: 'Respuesta no válida del servidor.' };
    }
    try {
      return await response.json();
    } catch {
      return { error: 'Respuesta no válida del servidor.' };
    }
  }

  async translateText(text) {
    this.isBusy = true;
    const translateLabel = this.translateBtn?.textContent || 'Traducir';
    if (this.translateBtn) {
      this.translateBtn.disabled = true;
      this.translateBtn.textContent = 'Traduciendo…';
    }
    if (this.cancelTranslateBtn) this.cancelTranslateBtn.hidden = false;
    if (this.micBtn) this.micBtn.disabled = true;
    this.setError('');

    this.translateAbort = new AbortController();
    const timeoutId = window.setTimeout(() => {
      this.translateAbort?.abort();
    }, TRANSLATE_TIMEOUT_MS);

    try {
      const response = await fetch('/voice/translate', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrf,
        },
        body: JSON.stringify({ text, source_lang: this.sourceLang }),
        signal: this.translateAbort.signal,
      });
      const data = await this.parseJsonResponse(response);
      if (!response.ok) {
        const targetLang = this.sourceLang === 'en' ? 'es' : 'en';
        const direct = await translateDirect(text, this.sourceLang, targetLang);
        if (direct) {
          this.showResult({
            spoken: text,
            translated: direct,
            source_lang: this.sourceLang,
            target_lang: targetLang,
          });
          return;
        }
        if (response.status === 504) {
          this.setError('La traducción tardó demasiado. Inténtalo de nuevo.');
        } else {
          this.setError(data.error || 'No se pudo traducir.');
        }
        return;
      }
      if (!data.translated) {
        const targetLang = this.sourceLang === 'en' ? 'es' : 'en';
        const direct = await translateDirect(text, this.sourceLang, targetLang);
        if (direct) {
          this.showResult({
            spoken: text,
            translated: direct,
            source_lang: this.sourceLang,
            target_lang: targetLang,
          });
          return;
        }
      }
      this.showResult(data);
    } catch (err) {
      const targetLang = this.sourceLang === 'en' ? 'es' : 'en';
      const direct = await translateDirect(text, this.sourceLang, targetLang);
      if (direct) {
        this.showResult({
          spoken: text,
          translated: direct,
          source_lang: this.sourceLang,
          target_lang: targetLang,
        });
        return;
      }
      if (err.name === 'AbortError') {
        this.setError('La traducción tardó demasiado. Inténtalo de nuevo.');
      } else {
        console.error('Translate failed:', err);
        this.setError('No se pudo traducir. Comprueba tu conexión.');
      }
    } finally {
      window.clearTimeout(timeoutId);
      this.translateAbort = null;
      this.isBusy = false;
      if (this.translateBtn) {
        this.translateBtn.disabled = false;
        this.translateBtn.textContent = translateLabel;
      }
      if (this.cancelTranslateBtn) this.cancelTranslateBtn.hidden = true;
      if (this.micBtn && this.micIsReady()) this.micBtn.disabled = false;
    }
  }

  showResult(data) {
    this.lastResult = data;
    if (this.resultsCard) {
      this.resultsCard.classList.remove('hidden');
      this.resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

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
    if (this.isRecording) {
      this.backend?.stop().catch(() => {});
      this.isRecording = false;
      document.body.classList.remove('voice-recording');
      this.micBtn?.classList.remove('is-recording');
    }
    this.lastResult = null;
    if (this.transcriptCard) this.transcriptCard.classList.add('hidden');
    if (this.resultsCard) this.resultsCard.classList.add('hidden');
    if (this.transcriptInput) this.transcriptInput.value = '';
    if (this.emptyState && this.backendKind !== 'none') {
      this.emptyState.classList.remove('hidden');
    }
    this.setError('');
    this.setIdleHint();
    if (this.saveStatus) {
      this.saveStatus.textContent = '';
      this.saveStatus.classList.add('hidden');
    }
    if (this.phrasebookLink) this.phrasebookLink.hidden = true;
    if (this.micBtn && this.micIsReady()) this.micBtn.disabled = false;
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
      const data = await this.parseJsonResponse(response);
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

function bootVoiceApp() {
  const root = document.getElementById('voice-app');
  if (root) {
    new VoiceApp(root);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootVoiceApp);
} else {
  bootVoiceApp();
}
