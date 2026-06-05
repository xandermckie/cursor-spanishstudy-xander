const LANG_LABELS = {
  en: 'Inglés',
  es: 'Español',
  ca: 'Catalán',
};

class TranslateApp {
  constructor(root) {
    this.root = root;
    this.csrf = root.dataset.csrf || '';
    this.isLoggedIn = root.dataset.loggedIn === 'true';
    this.phrasebookUrl = root.dataset.phrasebookUrl || '/phrasebook';

    this.sourceLangSelect = root.querySelector('#translate-source-lang');
    this.targetLangSelect = root.querySelector('#translate-target-lang');
    this.swapBtn = root.querySelector('#translate-swap-btn');
    this.sourceText = root.querySelector('#translate-source-text');
    this.targetText = root.querySelector('#translate-target-text');
    this.charCount = root.querySelector('#translate-char-count');
    this.cacheHint = root.querySelector('#translate-cache-hint');
    this.errorEl = root.querySelector('#translate-error');
    this.translateBtn = root.querySelector('#translate-btn');
    this.clearBtn = root.querySelector('#translate-clear-btn');
    this.copyBtn = root.querySelector('#translate-copy-btn');
    this.saveBtn = root.querySelector('#translate-save-btn');
    this.saveStatus = root.querySelector('#translate-save-status');
    this.emptyState = root.querySelector('#translate-empty-state');
    this.langThumbs = document.querySelectorAll('.translate-lang-thumb');

    this.lastResult = null;
    this.isBusy = false;

    this.bindEvents();
    this.updateCharCount();
    this.updateLangThumbs();
    this.updateSaveButton();
  }

  bindEvents() {
    this.sourceLangSelect?.addEventListener('change', () => {
      this.updateLangThumbs();
      this.updateSaveButton();
    });
    this.targetLangSelect?.addEventListener('change', () => {
      this.updateLangThumbs();
      this.updateSaveButton();
    });
    this.swapBtn?.addEventListener('click', () => this.swapLanguages());
    this.sourceText?.addEventListener('input', () => {
      this.updateCharCount();
      this.setError('');
    });
    this.translateBtn?.addEventListener('click', () => this.translate());
    this.clearBtn?.addEventListener('click', () => this.clear());
    this.copyBtn?.addEventListener('click', () => this.copyResult());
    this.saveBtn?.addEventListener('click', () => this.savePhrase());
    this.sourceText?.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        this.translate();
      }
    });
  }

  get sourceLang() {
    return this.sourceLangSelect?.value || 'en';
  }

  get targetLang() {
    return this.targetLangSelect?.value || 'es';
  }

  setError(message) {
    if (!this.errorEl) return;
    if (message) {
      this.errorEl.textContent = message;
      this.errorEl.classList.remove('hidden');
    } else {
      this.errorEl.textContent = '';
      this.errorEl.classList.add('hidden');
    }
  }

  updateCharCount() {
    const len = (this.sourceText?.value || '').length;
    if (this.charCount) {
      this.charCount.textContent = `${len} / 500`;
    }
  }

  updateLangThumbs() {
    const active = new Set([this.sourceLang, this.targetLang]);
    this.langThumbs.forEach((thumb) => {
      const lang = thumb.dataset.lang;
      thumb.classList.toggle('is-active', active.has(lang));
    });
  }

  canSaveToPhrasebook() {
    const langs = new Set([this.sourceLang, this.targetLang]);
    return langs.has('en') && langs.has('es') && !langs.has('ca');
  }

  updateSaveButton() {
    if (!this.saveBtn) return;
    const hasResult = Boolean(this.lastResult && this.lastResult.translated);
    this.saveBtn.disabled = !hasResult || !this.canSaveToPhrasebook();
  }

  swapLanguages() {
    const sourceLang = this.sourceLang;
    const targetLang = this.targetLang;
    if (this.sourceLangSelect) this.sourceLangSelect.value = targetLang;
    if (this.targetLangSelect) this.targetLangSelect.value = sourceLang;

    const sourceValue = this.sourceText?.value || '';
    const targetValue = this.targetText?.value || '';
    if (this.sourceText) this.sourceText.value = targetValue;
    if (this.targetText) this.targetText.value = sourceValue;

    if (this.lastResult) {
      this.lastResult = {
        source: targetValue,
        translated: sourceValue,
        source_lang: targetLang,
        target_lang: sourceLang,
        from_cache: false,
      };
    }

    this.updateLangThumbs();
    this.updateSaveButton();
    this.setError('');
  }

  async translate() {
    const text = (this.sourceText?.value || '').trim();
    if (!text) {
      this.setError('Escribe una frase para traducir.');
      return;
    }
    if (this.sourceLang === this.targetLang) {
      this.setError('Elige idiomas de origen y destino distintos.');
      return;
    }

    this.isBusy = true;
    if (this.translateBtn) this.translateBtn.disabled = true;
    this.setError('');
    if (this.cacheHint) this.cacheHint.classList.add('hidden');

    try {
      const response = await fetch('/translate/api', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrf,
        },
        body: JSON.stringify({
          text,
          source_lang: this.sourceLang,
          target_lang: this.targetLang,
        }),
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
    if (this.emptyState) this.emptyState.classList.add('hidden');
    if (this.targetText) this.targetText.value = data.translated || '';
    if (this.copyBtn) this.copyBtn.disabled = !data.translated;

    if (this.cacheHint) {
      if (data.from_cache) {
        this.cacheHint.textContent = 'Desde caché';
        this.cacheHint.classList.remove('hidden');
      } else {
        this.cacheHint.classList.add('hidden');
      }
    }

    if (this.saveStatus) {
      this.saveStatus.textContent = '';
      this.saveStatus.classList.add('hidden');
    }

    this.updateSaveButton();
  }

  clear() {
    this.lastResult = null;
    if (this.sourceText) this.sourceText.value = '';
    if (this.targetText) this.targetText.value = '';
    if (this.copyBtn) this.copyBtn.disabled = true;
    if (this.cacheHint) this.cacheHint.classList.add('hidden');
    if (this.emptyState) this.emptyState.classList.remove('hidden');
    if (this.saveStatus) {
      this.saveStatus.textContent = '';
      this.saveStatus.classList.add('hidden');
    }
    this.updateCharCount();
    this.updateSaveButton();
    this.setError('');
  }

  async copyResult() {
    const text = (this.targetText?.value || '').trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      if (this.copyBtn) {
        const original = this.copyBtn.textContent;
        this.copyBtn.textContent = 'Copiado';
        window.setTimeout(() => {
          if (this.copyBtn) this.copyBtn.textContent = original;
        }, 1500);
      }
    } catch (err) {
      console.error('Copy failed:', err);
      this.setError('No se pudo copiar al portapapeles.');
    }
  }

  async savePhrase() {
    if (!this.isLoggedIn || !this.lastResult || !this.canSaveToPhrasebook()) return;

    const { source, translated, source_lang: sourceLang } = this.lastResult;
    if (this.saveBtn) this.saveBtn.disabled = true;

    try {
      const response = await fetch('/translate/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrf,
        },
        body: JSON.stringify({
          spoken: source,
          translated,
          source_lang: sourceLang,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        this.setError(data.error || 'No se pudo guardar la frase.');
        return;
      }
      if (this.saveStatus) {
        this.saveStatus.textContent = 'Guardado en tu libro de frases.';
        this.saveStatus.classList.remove('hidden');
      }
    } catch (err) {
      console.error('Save failed:', err);
      this.setError('No se pudo guardar la frase.');
    } finally {
      this.updateSaveButton();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('translate-app');
  if (root) new TranslateApp(root);
});
