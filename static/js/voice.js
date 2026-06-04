(function () {
  'use strict';

  var app = document.getElementById('voice-app');
  if (!app) return;

  var csrf = app.getAttribute('data-csrf-token') || '';
  var translateUrl = app.getAttribute('data-translate-url') || '';
  var saveUrl = app.getAttribute('data-save-url') || '';
  var saveEnabled = app.getAttribute('data-save-enabled') === 'true';

  var listenBtn = document.getElementById('voice-listen-btn');
  var stopBtn = document.getElementById('voice-stop-btn');
  var translateBtn = document.getElementById('voice-translate-btn');
  var transcriptEl = document.getElementById('voice-transcript');
  var statusEl = document.getElementById('voice-status');
  var unsupportedEl = document.getElementById('voice-unsupported');
  var resultsEl = document.getElementById('voice-results');
  var originalEl = document.getElementById('voice-original');
  var translationEl = document.getElementById('voice-translation');
  var resultReveal = document.getElementById('voice-result-reveal');
  var resultPlain = document.getElementById('voice-result-plain');
  var revealEs = document.getElementById('voice-reveal-es');
  var revealEn = document.getElementById('voice-reveal-en');
  var revealCard = document.getElementById('voice-reveal-card');
  var saveBtn = document.getElementById('voice-save-btn');

  var SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognition = null;
  var isListening = false;
  var sessionActive = false;
  var finalTranscript = '';
  var translateDebounce = null;
  var lastSavedText = '';

  function getSpeakLang() {
    var checked = document.querySelector('input[name="voice-lang"]:checked');
    return checked ? checked.value : 'en';
  }

  function getRecognitionLang() {
    return getSpeakLang() === 'es' ? 'es-ES' : 'en-US';
  }

  function getTranslatePair() {
    var speak = getSpeakLang();
    if (speak === 'es') {
      return { source: 'es', target: 'en' };
    }
    return { source: 'en', target: 'es' };
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || '';
  }

  function setTranscript(text) {
    if (transcriptEl) transcriptEl.textContent = text;
    if (translateBtn) translateBtn.disabled = !text.trim();
  }

  function showUnsupported() {
    if (unsupportedEl) unsupportedEl.classList.remove('hidden');
    if (listenBtn) listenBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = true;
  }

  function setListening(active) {
    isListening = active;
    if (listenBtn) {
      listenBtn.disabled = active || !SpeechRecognition;
      listenBtn.setAttribute('aria-pressed', active ? 'true' : 'false');
      listenBtn.classList.toggle('voice-listening', active);
      listenBtn.textContent = active ? 'Escuchando…' : 'Escuchar';
    }
    if (stopBtn) stopBtn.disabled = !active;
  }

  function showResults(original, translated, pair) {
    if (!resultsEl) return;
    resultsEl.classList.remove('hidden');

    var useReveal = pair.target === 'es' && pair.source === 'en';
    if (resultReveal && resultPlain && revealEs && revealEn) {
      if (useReveal) {
        resultReveal.classList.remove('hidden');
        resultPlain.classList.add('hidden');
        revealEs.textContent = translated;
        revealEn.textContent = original;
        if (revealCard) revealCard.classList.remove('is-open');
      } else {
        resultReveal.classList.add('hidden');
        resultPlain.classList.remove('hidden');
        if (originalEl) originalEl.textContent = original;
        if (translationEl) translationEl.textContent = translated;
      }
    } else {
      if (originalEl) originalEl.textContent = original;
      if (translationEl) translationEl.textContent = translated;
    }

    if (saveBtn && saveEnabled && pair.source === 'en') {
      saveBtn.classList.remove('hidden');
      lastSavedText = original;
    } else if (saveBtn) {
      saveBtn.classList.add('hidden');
    }
  }

  function hideSaveIfNeeded() {
    if (saveBtn) saveBtn.classList.add('hidden');
  }

  function translate() {
    var text = (transcriptEl && transcriptEl.textContent) || finalTranscript;
    text = text.trim();
    if (!text) {
      setStatus('No hay texto para traducir.');
      return;
    }

    var pair = getTranslatePair();
    setStatus('Traduciendo…');
    hideSaveIfNeeded();

    fetch(translateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf,
      },
      body: JSON.stringify({
        text: text,
        source: pair.source,
        target: pair.target,
      }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          setStatus(
            (result.data && result.data.error) ||
              'No se pudo traducir. Inténtalo de nuevo.'
          );
          return;
        }
        var translated = result.data.translated || '';
        showResults(text, translated, pair);
        var cacheNote = result.data.from_cache ? ' (caché)' : '';
        setStatus('Traducción lista.' + cacheNote);
      })
      .catch(function () {
        setStatus('Error de red. Inténtalo de nuevo.');
      });
  }

  function scheduleAutoTranslate() {
    if (translateDebounce) clearTimeout(translateDebounce);
    translateDebounce = setTimeout(function () {
      var text = (transcriptEl && transcriptEl.textContent) || '';
      if (text.trim()) translate();
    }, 300);
  }

  function startRecognition() {
    if (!recognition || !sessionActive) return;
    try {
      recognition.start();
    } catch (e) {
      if (e && e.name === 'InvalidStateError') return;
      sessionActive = false;
      setListening(false);
      setStatus('No se pudo iniciar el micrófono. Espera un momento.');
    }
  }

  function beginListenSession() {
    if (!recognition) return;
    sessionActive = true;
    finalTranscript = '';
    setTranscript('');
    recognition.lang = getRecognitionLang();
    setStatus('Escuchando… Habla ahora. Pulsa Detener cuando termines.');
    startRecognition();
  }

  function endListenSession() {
    sessionActive = false;
    setListening(false);
    if (recognition) {
      try {
        recognition.stop();
      } catch (e) {
        /* ignore */
      }
    }
  }

  function initRecognition() {
    if (!SpeechRecognition) {
      showUnsupported();
      return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = function () {
      setListening(true);
    };

    recognition.onresult = function (event) {
      var interim = '';
      var final = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += t;
        } else {
          interim += t;
        }
      }
      if (final) finalTranscript += final;
      setTranscript(finalTranscript + interim);
    };

    recognition.onerror = function (event) {
      if (event.error === 'aborted') return;
      if (sessionActive && event.error === 'no-speech') {
        setStatus('No se detectó voz aún. Sigue hablando o pulsa Detener.');
        return;
      }
      sessionActive = false;
      setListening(false);
      if (event.error === 'not-allowed') {
        setStatus('Permiso de micrófono denegado.');
      } else if (event.error === 'no-speech') {
        setStatus('No se detectó voz. Inténtalo de nuevo.');
      } else {
        setStatus('Error de reconocimiento. Inténtalo de nuevo.');
      }
    };

    recognition.onend = function () {
      if (sessionActive) {
        startRecognition();
        return;
      }
      setListening(false);
      if (transcriptEl) finalTranscript = transcriptEl.textContent.trim();
      scheduleAutoTranslate();
    };
  }

  if (listenBtn) {
    listenBtn.addEventListener('click', beginListenSession);
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', function () {
      if (sessionActive || isListening) endListenSession();
    });
  }

  if (translateBtn) {
    translateBtn.addEventListener('click', translate);
  }

  document.querySelectorAll('input[name="voice-lang"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      hideSaveIfNeeded();
      if (resultsEl) resultsEl.classList.add('hidden');
    });
  });

  if (saveBtn && saveEnabled) {
    saveBtn.addEventListener('click', function () {
      var text = lastSavedText.trim();
      if (!text) return;
      setStatus('Guardando…');
      fetch(saveUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
        },
        body: JSON.stringify({ text: text }),
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok) {
            setStatus(
              (result.data && result.data.error) ||
                'No se pudo guardar la frase.'
            );
            return;
          }
          setStatus('Frase guardada en tu libro.');
          saveBtn.classList.add('hidden');
        })
        .catch(function () {
          setStatus('Error de red al guardar.');
        });
    });
  }

  initRecognition();
})();
