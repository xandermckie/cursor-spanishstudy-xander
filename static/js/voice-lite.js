/**
 * Lightweight mobile Voz UI — no speech recognition JS.
 * Users dictate via the keyboard's built-in mic into the textarea.
 */
import { translateDirect } from './translation-client.js';

const TRANSLATE_TIMEOUT_MS = 35000;

class VoiceLiteApp {
  constructor(root) {
    this.root = root;
    this.csrf = root.dataset.csrf || '';
    this.isLoggedIn = root.dataset.loggedIn === 'true';
    this.loginUrl = root.dataset.loginUrl || '/login';
    this.sourceLang = 'en';
    this.isBusy = false;
    this.translateAbort = null;
    this.lastResult = null;

    this.directionBtns = root.querySelectorAll('.voice-direction-btn');
    this.transcriptInput = document.getElementById('voice-transcript');
    this.translateBtn = document.getElementById('voice-translate-btn');
    this.cancelTranslateBtn = document.getElementById('voice-cancel-translate-btn');
    this.clearBtn = document.getElementById('voice-clear-btn');
    this.errorEl = document.getElementById('voice-error');
    this.resultsCard = document.getElementById('voice-results');
    this.spokenLabel = document.getElementById('voice-spoken-label');
    this.translatedLabel = document.getElementById('voice-translated-label');
    this.spokenText = document.getElementById('voice-spoken-text');
    this.translatedText = document.getElementById('voice-translated-text');
    this.saveBtn = document.getElementById('voice-save-btn');
    this.saveStatus = document.getElementById('voice-save-status');
    this.phrasebookLink = document.getElementById('voice-phrasebook-link');

    if (!this.csrf) {
      console.error('Voice lite: missing CSRF token');
    }

    root.dataset.speechBackend = 'keyboard';
    this.bindEvents();
  }

  bindEvents() {
    this.directionBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.setDirection(btn.dataset.sourceLang);
      });
    });

    const onTranslate = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.translateTranscript();
    };

    this.translateBtn?.addEventListener('click', onTranslate);

    this.cancelTranslateBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.cancelTranslate();
    });

    this.clearBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.clearTranscript();
    });

    this.saveBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.savePhrase();
    });

    this.transcriptInput?.addEventListener('input', () => this.setError(''));
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
    this.errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  clearTranscript() {
    if (this.transcriptInput) this.transcriptInput.value = '';
    if (this.resultsCard) this.resultsCard.classList.add('hidden');
    this.lastResult = null;
    this.setError('');
    this.transcriptInput?.focus();
  }

  async parseJsonResponse(response) {
    try {
      return await response.json();
    } catch {
      return { error: 'Respuesta no válida del servidor.' };
    }
  }

  cancelTranslate() {
    this.translateAbort?.abort();
  }

  async translateTranscript() {
    const text = (this.transcriptInput?.value || '').trim();
    if (!text) {
      this.setError('Escribe o dicta una frase antes de traducir.');
      return;
    }

    if (!this.csrf) {
      this.setError('Recarga la página e inténtalo de nuevo.');
      return;
    }

    this.transcriptInput?.blur();

    this.isBusy = true;
    const translateLabel = this.translateBtn?.textContent || 'Traducir';
    if (this.translateBtn) {
      this.translateBtn.disabled = true;
      this.translateBtn.textContent = 'Traduciendo…';
    }
    if (this.cancelTranslateBtn) this.cancelTranslateBtn.hidden = false;
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
          Accept: 'application/json',
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
        if (response.status === 403) {
          this.setError('Sesión caducada. Recarga la página e inténtalo de nuevo.');
        } else if (response.status === 504) {
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
        this.setError('No se recibió traducción. Inténtalo de nuevo.');
        return;
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
        console.error('Voice lite translate failed:', err);
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
    }
  }

  showResult(data) {
    this.lastResult = data;
    if (this.resultsCard) {
      this.resultsCard.classList.remove('hidden');
      this.resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrf,
          Accept: 'application/json',
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
      console.error('Voice lite save failed:', err);
      this.setError('No se pudo guardar la frase.');
    } finally {
      this.isBusy = false;
      if (this.saveBtn) this.saveBtn.disabled = false;
    }
  }
}

function bootVoiceLiteApp() {
  const root = document.getElementById('voice-app');
  if (root) {
    new VoiceLiteApp(root);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootVoiceLiteApp);
} else {
  bootVoiceLiteApp();
}
