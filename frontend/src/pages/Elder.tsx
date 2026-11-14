import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { Icon } from '../lib/icons'
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
  call108: { kn: '108ಗೆ ಫೋನ್ ಮಾಡಿ', en: 'Call 108' },
  urgent108: { kn: 'ಅರ್ಜೆಂಟ್ ಇದ್ರೆ 108ಗೆ ಫೋನ್ ಮಾಡಿ', en: 'Emergency? Call 108' },
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
  youAsked: { kn: 'ನೀವು ಕೇಳಿದ್ದು', en: 'You asked' },
  examplesTitle: { kn: 'ಹೀಗೆ ಕೇಳಬಹುದು', en: 'You can ask' },
  examples: [
    { kn: '“ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?”', en: '“When do I take the white tablet?”' },
    { kn: '“ಊಟಕ್ಕೆ ಮುಂಚೆನಾ, ಆದ್ಮೇಲಾ?”', en: '“Before food or after?”' },
    { kn: '“ಇನ್ನೂ ಎಷ್ಟು ದಿನ?”', en: '“How many more days?”' },
  ] as Line[],
}

const both = (line: Line) => `${line.kn}\n${line.en}`
const label = (line: Line) => `${line.kn} / ${line.en}`

type Badge = { line: Line; tone: string; icon: string }

// Every answer says what kind of answer it is, with an icon and words, so the
// meaning never depends on colour alone.
const OUTCOME_BADGES: Record<string, Badge> = {
  answered: { line: { kn: 'ನಿಮ್ಮ ಡಾಕ್ಟರ್ ಚೀಟಿ ಪ್ರಕಾರ', en: 'From your prescription' }, tone: 'bg-emerald-50 text-emerald-800 ring-emerald-200', icon: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z' },
  clarify_which: { line: { kn: 'ಸ್ವಲ್ಪ ಸ್ಪಷ್ಟ ಮಾಡಿ', en: 'Just to be sure' }, tone: 'bg-amber-50 text-amber-800 ring-amber-200', icon: 'M11 18h2v-2h-2zm1-16a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16m0-14a4 4 0 0 0-4 4h2a2 2 0 1 1 4 0c0 2-3 1.8-3 5h2c0-2.3 3-2.5 3-5a4 4 0 0 0-4-4' },
  clarify_question: { line: { kn: 'ಸ್ವಲ್ಪ ಸ್ಪಷ್ಟ ಮಾಡಿ', en: 'Just to be sure' }, tone: 'bg-amber-50 text-amber-800 ring-amber-200', icon: 'M11 18h2v-2h-2zm1-16a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16m0-14a4 4 0 0 0-4 4h2a2 2 0 1 1 4 0c0 2-3 1.8-3 5h2c0-2.3 3-2.5 3-5a4 4 0 0 0-4-4' },
  clarify_repeat: { line: { kn: 'ಸ್ವಲ್ಪ ಸ್ಪಷ್ಟ ಮಾಡಿ', en: 'Just to be sure' }, tone: 'bg-amber-50 text-amber-800 ring-amber-200', icon: 'M11 18h2v-2h-2zm1-16a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16m0-14a4 4 0 0 0-4 4h2a2 2 0 1 1 4 0c0 2-3 1.8-3 5h2c0-2.3 3-2.5 3-5a4 4 0 0 0-4-4' },
  referral: { line: { kn: 'ಡಾಕ್ಟರ್‌ನ ಕೇಳಿ', en: 'Ask your doctor' }, tone: 'bg-violet-50 text-violet-800 ring-violet-200', icon: 'M19 8h-2V6a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2M9 6h6v2H9zm4 10v2h-2v-2H9v-2h2v-2h2v2h2v2z' },
  error: { line: { kn: 'ಮತ್ತೆ ಕೇಳಿ', en: 'Please ask again' }, tone: 'bg-slate-100 text-slate-700 ring-slate-200', icon: 'M12 6V3L8 7l4 4V8a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8' },
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  const badge = OUTCOME_BADGES[outcome] ?? OUTCOME_BADGES.error
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-base font-semibold ring-1 ${badge.tone}`}>
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-5 w-5">
        <path d={badge.icon} />
      </svg>
      <Bi line={badge.line} />
    </span>
  )
}

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
        lang === value ? 'bg-[#0C2451] text-white shadow' : 'text-[#0C2451]'
      }`}
    >
      {text}
    </button>
  )
  return (
    <div className="flex rounded-full bg-white p-1 ring-1 ring-blue-100" role="group" aria-label="Language / ಭಾಷೆ">
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

const spinner = (
  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-1/4 w-1/4 animate-spin">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.3" strokeWidth="3" />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
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
    // Silence the previous answer first, or the microphone records the phone's
    // own speaker along with the new question.
    playerRef.current?.pause()
    playerRef.current = null
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
          className="flex w-full max-w-md items-center justify-center gap-3 rounded-2xl bg-white px-6 py-5 text-3xl font-black text-red-800 no-underline shadow-xl active:scale-95"
        >
          <Icon name="phone" className="h-8 w-8" />
          <span><Bi line={TEXT.call108} /></span>
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
    <main className="flex min-h-screen flex-col items-center bg-linear-to-b from-blue-50 via-white to-slate-100 px-5 pt-5 pb-6 text-center">
      {/* Brand: who is speaking to the elder. */}
      <header className="flex w-full max-w-xl items-center justify-between gap-2 text-[#0C2451]">
        <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0C2451] text-white">
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
            <OutcomeBadge outcome={answer.outcome} />

            {answer.transcript && (
              <div className="rounded-2xl bg-slate-50 px-4 py-3 text-left ring-1 ring-slate-100">
                <p className="text-sm font-semibold tracking-wide text-slate-500 uppercase">
                  <Bi line={TEXT.youAsked} />
                </p>
                <p className="mt-0.5 text-lg text-slate-800">“{answer.transcript}”</p>
              </div>
            )}

            {answer.medicine && (
              <div className="flex flex-col items-center gap-3">
                {answer.medicine.photo_url && (
                  <img
                    src={answer.medicine.photo_url}
                    alt={answer.medicine.label}
                    className="h-28 w-28 rounded-2xl border border-slate-200 bg-white object-contain p-2"
                  />
                )}
                <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-4 py-1.5 text-lg font-semibold text-[#0C2451] ring-1 ring-blue-100">
                  <span className="h-2.5 w-2.5 rounded-full bg-blue-600" aria-hidden="true" />
                  {answer.medicine.label}
                </span>
              </div>
            )}

            <p className="text-[1.75rem] leading-snug font-bold text-slate-900">{answer.answer_text}</p>

            {answer.audio_error && (
              <p className="text-lg text-slate-600"><Bi line={TEXT.noVoice} enClass="text-base" /></p>
            )}

            {answer.audio_base64 && !answer.audio_error && (
              <button
                type="button"
                onClick={replay}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[#0C2451] px-6 py-4 text-2xl font-bold text-white shadow-md active:scale-95"
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
            {phase === 'idle' && (
              <div className="pt-3">
                <p className="text-sm font-semibold tracking-wide text-slate-500 uppercase">
                  <Bi line={TEXT.examplesTitle} />
                </p>
                <ul className="mt-2 flex flex-col items-center gap-2">
                  {TEXT.examples.map((example) => (
                    <li key={example.en} className="rounded-full bg-white px-4 py-1.5 text-base text-slate-700 shadow-sm ring-1 ring-slate-200">
                      <Bi line={example} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {problem && (
          <p role="alert" className="w-full rounded-2xl bg-red-50 px-5 py-4 text-xl whitespace-pre-line text-red-800 ring-1 ring-red-100">
            {pick(problem, lang)}
          </p>
        )}

        <div className="relative flex items-center justify-center">
        {recording && (
          // Expanding rings show the microphone is live, like a call screen.
          <>
            <span className="absolute inset-0 animate-ping rounded-full bg-red-400/30" aria-hidden="true" />
            <span className="absolute -inset-4 animate-pulse rounded-full bg-red-200/40" aria-hidden="true" />
          </>
        )}
        <button
          type="button"
          onClick={handlePress}
          disabled={busy}
          aria-label={label(recording ? TEXT.stopLabel : TEXT.startLabel)}
          className={`flex aspect-square w-[64vw] max-w-72 items-center justify-center rounded-full text-white shadow-2xl ring-[14px] transition-transform active:scale-95 disabled:opacity-60 ${
            recording
              ? 'relative bg-red-600 ring-red-100'
              : busy
                ? 'bg-slate-400 ring-slate-100'
                : 'bg-linear-to-br from-[#3395FF] to-[#0C2451] ring-blue-100'
          }`}
        >
          {recording ? stopIcon : busy ? spinner : micIcon}
        </button>
        </div>

        {recording && (
          <p className="text-lg text-slate-500"><Bi line={TEXT.stopsAfter(MAX_RECORDING_SECONDS)} enClass="text-base" /></p>
        )}
      </div>

      {/* Always reachable: if the app mishears or cannot hear an emergency,
          the elder can still call for help with one tap. */}
      <a
        href="tel:108"
        aria-label={label(TEXT.urgent108)}
        className="flex w-full max-w-xl items-center justify-center gap-2 rounded-2xl border-2 border-red-600 bg-white px-6 py-3 text-xl font-bold text-red-700 no-underline shadow-sm active:scale-95"
      >
        <Icon name="phone" className="h-6 w-6" />
        <span><Bi line={TEXT.urgent108} enClass="text-base font-normal" /></span>
      </a>
    </main>
  )
}
