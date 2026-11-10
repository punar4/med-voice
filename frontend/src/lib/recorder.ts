// Records one question and hands it back as a 16 kHz mono 16-bit WAV file.
//
// Why all this work in the browser: the backend uses ffmpeg to convert audio,
// and ffmpeg is not installed on the development machine. Browsers record WebM
// or MP4, which Prisma cannot read reliably, so the clip is decoded with the Web
// Audio API, resampled to 16 kHz mono, and written as a WAV by hand. The server
// then receives a format it accepts as-is and passes it straight through.

export const TARGET_SAMPLE_RATE = 16000
export const MAX_RECORDING_SECONDS = 10
export const WAV_MIME_TYPE = 'audio/wav'

// First format the browser supports wins. MediaRecorder cannot be told a sample
// rate, so the recorded file is only a container; the WAV is built afterwards.
const PREFERRED_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
]

// Messages are two lines: Kannada first, then English.
export class RecorderError extends Error {}

export interface Recording {
  /** Stop the microphone and resolve with the WAV file (safe to call twice). */
  stop(): Promise<Blob>
  /** Stop and throw the clip away, e.g. when leaving the page. */
  cancel(): void
}

export async function startRecording(onAutoStop?: () => void): Promise<Recording> {
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    throw new RecorderError('ಇದರಲ್ಲಿ ರೆಕಾರ್ಡ್ ಆಗ್ತಿಲ್ಲ. Chrome ಅಲ್ಲಿ ತೆಗೀರಿ.\nThis browser cannot record. Please open it in Chrome.')
  }

  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      // Noise suppression and echo cancellation can cut soft or slow speech
      // (elders!) down to a word; auto gain lifts a quiet voice instead.
      audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true },
    })
  } catch {
    throw new RecorderError('ಮೈಕ್ ಬ್ಲಾಕ್ ಆಗಿದೆ. ಮೈಕ್‌ಗೆ Allow ಕೊಟ್ಟು, ಮತ್ತೆ ಒತ್ತಿ.\nThe microphone is blocked. Allow it and press again.')
  }

  const mimeType = PREFERRED_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
  let recorder: MediaRecorder
  try {
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
  } catch {
    stream.getTracks().forEach((track) => track.stop())
    throw new RecorderError('ಇದರಲ್ಲಿ ರೆಕಾರ್ಡ್ ಆಗ್ತಿಲ್ಲ. Chrome ಅಲ್ಲಿ ತೆಗೀರಿ.\nThis browser cannot record. Please open it in Chrome.')
  }

  const chunks: Blob[] = []
  recorder.addEventListener('dataavailable', (event) => {
    if (event.data.size > 0) chunks.push(event.data)
  })

  const finished = new Promise<Blob>((resolve, reject) => {
    recorder.addEventListener(
      'stop',
      () => {
        stream.getTracks().forEach((track) => track.stop())
        const clip = new Blob(chunks, { type: recorder.mimeType || chunks[0]?.type || '' })
        toWav(clip).then(resolve, reject)
      },
      { once: true },
    )
  })

  // Nothing is sent until stop(), so a promise rejection here has no listener
  // yet; the caller awaits the same promise, which counts as handled.
  finished.catch(() => {})

  // Hand back control only once the recorder is really running, so the screen
  // says "listening" no earlier than the microphone does. The 250 ms slices make
  // sure every bit of audio reaches `chunks`, not just one blob at the end.
  const started = new Promise<void>((resolve) => {
    recorder.addEventListener('start', () => resolve(), { once: true })
  })
  recorder.start(250)
  await started
  const timer = window.setTimeout(() => {
    if (recorder.state !== 'inactive') {
      onAutoStop?.()
      recorder.stop()
    }
  }, MAX_RECORDING_SECONDS * 1000)

  return {
    stop() {
      window.clearTimeout(timer)
      if (recorder.state !== 'inactive') recorder.stop()
      return finished
    },
    cancel() {
      window.clearTimeout(timer)
      if (recorder.state !== 'inactive') recorder.stop()
    },
  }
}

/** Decode whatever the browser recorded, mix to mono at 16 kHz, and wrap in WAV. */
async function toWav(clip: Blob): Promise<Blob> {
  const bytes = await clip.arrayBuffer()
  const context = new AudioContext()
  try {
    const decoded = await context.decodeAudioData(bytes)
    const samples = await toMono16k(decoded)
    return encodeWav(samples, TARGET_SAMPLE_RATE)
  } catch {
    throw new RecorderError('ಸರಿಯಾಗಿ ರೆಕಾರ್ಡ್ ಆಗ್ಲಿಲ್ಲ. ಇನ್ನೊಂದ್ಸಲ ಕೇಳಿ.\nThe recording did not work. Please ask again.')
  } finally {
    void context.close()
  }
}

async function toMono16k(buffer: AudioBuffer): Promise<Float32Array> {
  if (buffer.numberOfChannels === 1 && buffer.sampleRate === TARGET_SAMPLE_RATE) {
    return buffer.getChannelData(0).slice()
  }
  // An OfflineAudioContext with one channel does the downmix and resampling for
  // us, using the browser's own (good) resampler.
  const frames = Math.max(1, Math.round(buffer.duration * TARGET_SAMPLE_RATE))
  const offline = new OfflineAudioContext(1, frames, TARGET_SAMPLE_RATE)
  const source = offline.createBufferSource()
  source.buffer = buffer
  source.connect(offline.destination)
  source.start()
  const rendered = await offline.startRendering()
  return rendered.getChannelData(0)
}

/** Write a standard 44-byte RIFF/WAVE header followed by 16-bit PCM samples. */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const dataSize = samples.length * 2
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // size of this fmt chunk
  view.setUint16(20, 1, true) // 1 = uncompressed PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // bytes per second
  view.setUint16(32, 2, true) // bytes per frame
  view.setUint16(34, 16, true) // bits per sample
  writeAscii(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  let offset = 44
  for (let index = 0; index < samples.length; index += 1) {
    const value = Math.max(-1, Math.min(1, samples[index]))
    view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true)
    offset += 2
  }

  return new Blob([buffer], { type: WAV_MIME_TYPE })
}

function writeAscii(view: DataView, offset: number, text: string): void {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index))
  }
}