import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { askElder, type AskResponse } from '../lib/api'
import { MAX_RECORDING_SECONDS, RecorderError, startRecording, type Recording } from '../lib/recorder'

// Elder page: one big button, one question, one spoken answer. No menus.
// Phases: idle -> recording -> processing -> answered (or failed).
// Every line exists in spoken-style Kannada and in English. Like most Indian
// multi-language apps, the screen shows ONE language at a time (Kannada by
// default) with a switch at the top, instead of stacking both.

type Line = { kn: string; en: string }

const TEXT = {
  sayAgain: { kn: 'ಇನ್ನೊಂದ್ಸಲ ಹೇಳಿ', en: 'Say it again' },
  askAgain: { kn: 'ಮತ್ತೆ ಕೇಳೋಕೆ ಒತ್ತಿ', en: 'Press to ask again' },
  call108: { kn: '📞 108ಗೆ ಫೋನ್ ಮಾಡಿ', en: 'Call 108' },
  urgent108: { kn: '📞 ಅರ್ಜೆಂಟ್ ಇದ್ರೆ 108ಗೆ ಫೋನ್ ಮಾಡಿ', en: 'Emergency? Call 108' },
  idleTitle: { kn: 'ಒತ್ತಿ, ಕೇಳಿ', en: 'Press and ask' },
  idleHint: { kn: 'ನಿಮ್ಮ ಮಾತ್ರೆ ಬಗ್ಗೆ ಕೇಳಿ.', en: 'Ask about your medicine.' },
  listeningTitle: { kn: 'ಕೇಳಿಸ್ಕೊಳ್ತಾ ಇದೀನಿ…', en: 'Listening…' },
  listeningHint: { kn: 'ಮಾತಾಡಿ ಆದ್ಮೇಲೆ ಮತ್ತೆ ಬಟನ್ ಒತ್ತಿ.', en: 'Press the button again when you finish.' },
  thinkingTitle: { kn: 'ಒಂದ್ ನಿಮಿಷ…', en: 'One moment…' },
  thinkingHint: { kn: 'ಉತ್ತರ ಹುಡುಕ್ತಾ ಇದೀನಿ.', en: 'Finding the answer.' },
  failedTitle: { kn: 'ಇನ್ನೊಂದ್ಸಲ ಕೇಳಿ', en: 'Please ask again' },
  failedHint: { kn: 'ಬಟನ್ ಒತ್ತಿ ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಕೇಳಿ.', en: 'Press the button and ask your question.' },
  noVoice: { kn: 'ಧ್ವನಿ ಬರ್ತಿಲ್ಲ. ಮೇಲಿರೋ ಉತ್ತರ ಓದಿ.', en: 'The voice could not play. Please read the answer above.' },
  micFailed: { kn: 'ಮೈಕ್ ಶುರು ಆಗ್ಲಿಲ್ಲ. ಇನ್ನೊಂದ್ಸಲ ಒತ್ತಿ.', en: 'The microphone did not start. Press again.' },
  noAnswer: { kn: 'ಉತ್ತರ ಬರ್ಲಿಲ್ಲ. ಇಂಟರ್ನೆಟ್ ನೋಡಿ, ಇನ್ನೊಂದ್ಸಲ ಕೇಳಿ.', en: 'No answer came. Check the internet and ask again.' },
  stopsAfter: (seconds: number): Line => ({
    kn: `${seconds} ಸೆಕೆಂಡ್ ಆದ್ಮೇಲೆ ತಾನಾಗೇ ನಿಲ್ಲುತ್ತೆ.`,
    en: `Stops by itself after ${seconds} seconds.`,
  }),
  startLabel: { kn: 'ಕೇಳೋಕೆ ಒತ್ತಿ', en: 'Start recording' },
  stopLabel: { kn: 'ನಿಲ್ಲಿಸೋಕೆ ಒತ್ತಿ', en: 'Stop recording' },
}

const both = (line: Line) => `${line.kn}\n${line.en}`
const label = (line: Line) => `${line.kn} / ${line.en}`

type Lang = 'kn' | 'en'
const LANG_KEY = 'medvoice-lang'
const LangContext = createContext<Lang>('kn')

function savedLang(): Lang {
  try {
    return window.localStorage.getItem(LANG_KEY) === 'en' ? 'en' : 'kn'
  } catch {
    return 'kn'
  }
}

/** The line in the chosen language. (`enClass` is kept so call sites stay unchanged.) */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function Bi({ line }: { line: Line; enClass?: string }) {
  return <span className="block">{line[useContext(LangContext)]}</span>
}

/** Error messages arrive as two lines (Kannada, then English); show the chosen one. */
function pick(message: string, lang: Lang): string {
  const [kn, en] = message.split('\n')
  return (lang === 'en' ? en : kn) ?? message
}

function LangSwitch({ lang, onChange }: { lang: Lang; onChange: (lang: Lang) => void }) {
  const option = (value: Lang, text: string) => (
    <button
      type="button"
      onClick={() => onChange(value)}
      aria-pressed={lang === value}
      className={`rounded-full px-3 py-1 text-sm font-semibold transition-colors ${
        lang === value ? 'bg-teal-700 text-white shadow' : 'text-teal-800'
      }`}
    >
      {text}
    </button>
  )
  return (
    <div className="flex rounded-full bg-white p-1 ring-1 ring-teal-100" role="group" aria-label="Language / ಭಾಷೆ">
      {option('kn', 'ಕನ್ನಡ')}
      {option('en', 'English')}
    </div>
  )
}

export default function Elder({ token }: { token: string }) {
  const [lang, setLang] = useState<Lang>(savedLang)
  function choose(next: Lang) {
    setLang(next)
    try {
      window.localStorage.setItem(LANG_KEY, next)
    } catch {
      // Private mode: the choice just isn't remembered.
    }
  }
  return (
    <LangContext.Provider value={lang}>
      <ElderScreen token={token} lang={lang} onLang={choose} />
    </LangContext.Provider>
  )
}

type Phase = 'idle' | 'recording' | 'processing' | 'answered' | 'failed'

const micIcon = (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-1/3 w-1/3">
    <path d="M12 15a3.5 3.5 0 0 0 3.5-3.5v-5a3.5 3.5 0 0 0-7 0v5A3.5 3.5 0 0 0 12 15Z" />
    <path d="M18 11.5a1 1 0 1 0-2 0 4 4 0 0 1-8 0 1 1 0 1 0-2 0 6 6 0 0 0 5 5.91V20H9a1 1 0 1 0 0 2h6a1 1 0 1 0 0-2h-2v-2.59A6 6 0 0 0 18 11.5Z" />
  </svg>
)

const stopIcon = (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-1/3 w-1/3">
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
)

function ElderScreen({ token, lang, onLang }: { token: string; lang: Lang; onLang: (lang: Lang) => void }) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [answer, setAnswer] = useState<AskResponse | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const recordingRef = useRef<Recording | null>(null)
  const playerRef = useRef<HTMLAudioElement | null>(null)

  // Stop the microphone and the voice if the page is left mid-flow.
  useEffect(
    () => () => {
      recordingRef.current?.cancel()
      playerRef.current?.pause()
    },
    [],
  )

  function playVoice(base64: string) {
    playerRef.current?.pause()
    const player = new Audio(`data:audio/wav;base64,${base64}`)
    playerRef.current = player
    // Phones sometimes refuse autoplay; the "say it again" button still works.
    void player.play().catch(() => {})
  }

  async function start() {
    setProblem(null)
    setAnswer(null)
    setPhase('recording')
    try {
      recordingRef.current = await startRecording(() => void finish())
    } catch (error) {
      setPhase('failed')
      setProblem(error instanceof RecorderError ? error.message : both(TEXT.micFailed))
    }
  }

  async function finish() {
    const recording = recordingRef.current
    if (!recording) return
    recordingRef.current = null
    setPhase('processing')
    try {
      const result = await askElder(token, await recording.stop())
      setAnswer(result)
      setPhase('answered')
      if (result.audio_base64 && !result.audio_error) playVoice(result.audio_base64)
    } catch (error) {
      // Server/network details stay in the console; the elder sees plain Kannada.
      console.error(error)
      setPhase('failed')
      setProblem(error instanceof RecorderError ? error.message : both(TEXT.noAnswer))
    }
  }

  function handlePress() {
    if (phase === 'recording') void finish()
    else if (phase !== 'processing') void start()
  }

  function replay() {
    if (answer?.audio_base64) playVoice(answer.audio_base64)
  }

  // Emergency: the whole screen turns red with a huge 108, because this is the
  // one answer that must not be missed.
  if (answer?.outcome === 'emergency') {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-red-700 px-6 py-10 text-center text-white">
        <a href="tel:108" className="text-[9rem] leading-none font-black tracking-tight text-white no-underline" aria-label={label(TEXT.call108)}>
          108
        </a>
        <p className="max-w-xl text-3xl leading-snug font-semibold">{answer.answer_text}</p>
        {/* One tap on a phone starts the call. */}
        <a
          href="tel:108"
          className="w-full max-w-md rounded-2xl bg-white px-6 py-5 text-3xl font-black text-red-800 no-underline shadow-xl active:scale-95"
        >
          <Bi line={TEXT.call108} />
        </a>
        {answer.audio_base64 && !answer.audio_error && (
          <button
            type="button"
            onClick={replay}
            className="rounded-full border-2 border-white px-10 py-4 text-2xl font-bold text-white active:scale-95"
          >
            <Bi line={TEXT.sayAgain} />
          </button>
        )}
        <button
          type="button"
          onClick={handlePress}
          aria-label={label(TEXT.askAgain)}
          className="flex h-[55vw] max-h-64 w-[55vw] max-w-64 items-center justify-center rounded-full bg-white text-red-700 shadow-xl active:scale-95"
        >
          {micIcon}
        </button>
        <p className="text-xl font-medium">
          <Bi line={TEXT.askAgain} />
        </p>
      </main>
    )
  }

  const recording = phase === 'recording'
  const busy = phase === 'processing'

  return (
    <main className="flex min-h-screen flex-col items-center bg-linear-to-b from-teal-50 via-white to-amber-50 px-5 pt-5 pb-6 text-center">
      {/* Brand: who is speaking to the elder. */}
      <header className="flex w-full max-w-xl items-center justify-between gap-2 text-teal-800">
        <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-700 text-white">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-4 w-4">
            <path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z" />
          </svg>
        </span>
        <span className="text-xl font-bold tracking-tight">MedVoice</span>
        </div>
        <LangSwitch lang={lang} onChange={onLang} />
      </header>

      <div className="flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-7 py-6">
        {phase === 'answered' && answer ? (
          <section className="w-full space-y-5 rounded-3xl bg-white p-6 shadow-lg ring-1 ring-slate-100">
            {answer.medicine && (
              <div className="flex flex-col items-center gap-3">
                {answer.medicine.photo_url && (
                  <img
                    src={answer.medicine.photo_url}
                    alt={answer.medicine.label}
                    className="h-28 w-28 rounded-2xl border border-slate-200 bg-white object-contain p-2"
                  />
                )}
                <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-4 py-1.5 text-lg font-semibold text-teal-800 ring-1 ring-teal-100">
                  <span className="h-2.5 w-2.5 rounded-full bg-teal-600" aria-hidden="true" />
                  {answer.medicine.label}
                </span>
              </div>
            )}

            <p className="text-3xl leading-snug font-semibold text-slate-900">{answer.answer_text}</p>

            {answer.audio_error && (
              <p className="text-lg text-slate-600"><Bi line={TEXT.noVoice} enClass="text-base" /></p>
            )}

            {answer.audio_base64 && !answer.audio_error && (
              <button
                type="button"
                onClick={replay}
                className="w-full rounded-2xl bg-teal-700 px-6 py-4 text-2xl font-bold text-white shadow-md active:scale-95"
              >
                <Bi line={TEXT.sayAgain} />
              </button>
            )}
          </section>
        ) : (
          <section className="space-y-3">
            <p className="text-4xl font-bold text-slate-900">
              <Bi
                line={busy ? TEXT.thinkingTitle : recording ? TEXT.listeningTitle : phase === 'failed' ? TEXT.failedTitle : TEXT.idleTitle}
                enClass="text-[0.5em] font-medium text-slate-500"
              />
            </p>
            <p className="text-xl text-slate-600">
              <Bi
                line={
                  busy
                    ? TEXT.thinkingHint
                    : recording
                      ? TEXT.listeningHint
                      : phase === 'failed'
                        ? TEXT.failedHint
                        : TEXT.idleHint
                }
                enClass="text-base text-slate-500"
              />
            </p>
          </section>
        )}

        {problem && (
          <p role="alert" className="w-full rounded-2xl bg-red-50 px-5 py-4 text-xl whitespace-pre-line text-red-800 ring-1 ring-red-100">
            {pick(problem, lang)}
          </p>
        )}

        <button
          type="button"
          onClick={handlePress}
          disabled={busy}
          aria-label={label(recording ? TEXT.stopLabel : TEXT.startLabel)}
          className={`flex aspect-square w-[64vw] max-w-72 items-center justify-center rounded-full text-white shadow-2xl ring-[14px] transition-transform active:scale-95 disabled:opacity-60 ${
            recording
              ? 'animate-pulse bg-red-600 ring-red-100'
              : busy
                ? 'bg-slate-400 ring-slate-100'
                : 'bg-linear-to-br from-teal-600 to-teal-800 ring-teal-100'
          }`}
        >
          {recording ? stopIcon : micIcon}
        </button>

        {recording && (
          <p className="text-lg text-slate-500"><Bi line={TEXT.stopsAfter(MAX_RECORDING_SECONDS)} enClass="text-base" /></p>
        )}
      </div>

      {/* Always reachable: if the app mishears or cannot hear an emergency,
          the elder can still call for help with one tap. */}
      <a
        href="tel:108"
        aria-label={label(TEXT.urgent108)}
        className="w-full max-w-xl rounded-2xl border-2 border-red-600 bg-white px-6 py-3 text-xl font-bold text-red-700 no-underline shadow-sm active:scale-95"
      >
        <Bi line={TEXT.urgent108} enClass="text-base font-normal" />
      </a>
    </main>
  )
}
