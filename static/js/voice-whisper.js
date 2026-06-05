const TARGET_SAMPLE_RATE = 16000;
const TRANSCRIBE_TIMEOUT_MS = 45000;

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

async function blobToFloat32(blob) {
  const audioContext = new AudioContext();
  try {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const channel = audioBuffer.getChannelData(0);
    return {
      samples: new Float32Array(channel),
      sampleRate: audioBuffer.sampleRate,
    };
  } finally {
    await audioContext.close().catch(() => {});
  }
}

function withTimeout(promise, ms, message) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(message));
    }, ms);
    promise
      .then((value) => {
        window.clearTimeout(timer);
        resolve(value);
      })
      .catch((err) => {
        window.clearTimeout(timer);
        reject(err);
      });
  });
}

export class WhisperBackend {
  constructor(ui) {
    this.ui = ui;
    this.transcriber = null;
    this.isModelReady = false;
    this.isLoading = false;
    this.mediaStream = null;
    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.isRecording = false;
    this.transformersModule = null;
    this.sourceLang = 'en';
  }

  get kind() {
    return 'whisper';
  }

  get ready() {
    return this.isModelReady;
  }

  async loadTransformers() {
    if (!this.transformersModule) {
      this.transformersModule = await import(
        'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.0'
      );
    }
    return this.transformersModule;
  }

  async load() {
    if (this.isModelReady || this.isLoading) {
      while (this.isLoading) {
        await new Promise((r) => window.setTimeout(r, 100));
      }
      return;
    }

    this.isLoading = true;
    const { pipeline, env } = await this.loadTransformers();
    env.allowLocalModels = false;
    const progressCallback = (progress) => this.ui.updateProgress(progress);

    try {
      this.ui.setModelStatus('Cargando modelo Whisper…');
      const skipWebGpu = isMobileOrLowMemory();
      if (!skipWebGpu) {
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
      } else {
        this.transcriber = await pipeline(
          'automatic-speech-recognition',
          'Xenova/whisper-tiny',
          { progress_callback: progressCallback }
        );
      }

      this.isModelReady = true;
      if (this.ui.progressWrap) this.ui.progressWrap.hidden = true;
      this.ui.setModelStatus('Modelo Whisper listo');
    } catch (err) {
      console.error('Whisper model load failed:', err);
      throw new Error(
        'No se pudo cargar Whisper. Comprueba tu conexión e inténtalo de nuevo.'
      );
    } finally {
      this.isLoading = false;
    }
  }

  async ensureMicAccess() {
    if (this.mediaStream) return this.mediaStream;
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    return this.mediaStream;
  }

  async start(lang) {
    this.sourceLang = lang;
    const stream = await this.ensureMicAccess();
    this.recordedChunks = [];
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    this.mediaRecorder = new MediaRecorder(stream, { mimeType });
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.recordedChunks.push(event.data);
      }
    };
    this.mediaRecorder.start(250);
    this.isRecording = true;
  }

  async stop() {
    if (!this.isRecording || !this.mediaRecorder) {
      return '';
    }

    this.isRecording = false;

    const recorder = this.mediaRecorder;
    this.mediaRecorder = null;

    const blob = await new Promise((resolve) => {
      recorder.onstop = () => {
        const type = recorder.mimeType || 'audio/webm';
        resolve(new Blob(this.recordedChunks, { type }));
      };
      try {
        recorder.stop();
      } catch {
        resolve(new Blob(this.recordedChunks, { type: recorder.mimeType || 'audio/webm' }));
      }
    });

    this.recordedChunks = [];

    if (!blob.size) {
      return '';
    }

    const { samples, sampleRate } = await blobToFloat32(blob);
    const audio = resampleTo16k(samples, sampleRate);
    return this.transcribe(audio);
  }

  async transcribe(audio) {
    if (!this.transcriber || !audio.length) {
      return '';
    }

    const output = await withTimeout(
      this.transcriber(audio, {
        language: this.sourceLang,
        task: 'transcribe',
      }),
      TRANSCRIBE_TIMEOUT_MS,
      'Transcription timeout'
    );
    return (output?.text || '').trim();
  }

  dispose() {
    if (this.mediaRecorder && this.isRecording) {
      try {
        this.mediaRecorder.stop();
      } catch {
        /* ignore */
      }
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
  }
}
