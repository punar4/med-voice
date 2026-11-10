import { useEffect, useMemo, useState } from 'react'
import { getQuestionLog, type AskOutcome, type QuestionLog } from '../lib/api'
import { Brand } from './CaregiverSetup'

// How each outcome is named and coloured. `referral` stands out because it means
// the elder was sent to a doctor; `emergency` is red because someone may be in danger.
const OUTCOME_STYLES: Record<AskOutcome, { label: string; tag: string }> = {
  answered: { label: 'Answered', tag: 'bg-slate-100 text-slate-700' },
  clarify_which: { label: 'Clarify: which tablet', tag: 'bg-amber-100 text-amber-800' },
  clarify_question: { label: 'Clarify: question', tag: 'bg-amber-100 text-amber-800' },
  clarify_repeat: { label: 'Clarify: repeat', tag: 'bg-amber-100 text-amber-800' },
  referral: { label: 'Referral', tag: 'bg-orange-200 text-orange-900' },
  emergency: { label: 'Emergency', tag: 'bg-red-600 text-white' },
  error: { label: 'Error', tag: 'bg-red-100 text-red-800' },
}

function outcomeStyle(outcome: string) {
  // An outcome this page does not know about still needs a label and a colour.
  return OUTCOME_STYLES[outcome as AskOutcome] ?? { label: outcome, tag: 'bg-slate-100 text-slate-700' }
}

function sameLocalDay(iso: string, day: Date): boolean {
  const value = new Date(iso)
  return (
    value.getFullYear() === day.getFullYear() &&
    value.getMonth() === day.getMonth() &&
    value.getDate() === day.getDate()
  )
}

const timeFormat = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' })
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})

function formatTime(iso: string, today: Date): string {
  const value = new Date(iso)
  if (Number.isNaN(value.getTime())) return iso
  return sameLocalDay(iso, today) ? timeFormat.format(value) : dateTimeFormat.format(value)
}

const summaryCard = 'rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100'

export default function CaregiverLog({ profileId }: { profileId: number }) {
  const [entries, setEntries] = useState<QuestionLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    getQuestionLog(profileId)
      .then((rows) => {
        if (active) setEntries(rows)
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [profileId])

  const today = useMemo(() => new Date(), [])
  const counts = useMemo(
    () => ({
      questionsToday: entries.filter((entry) => sameLocalDay(entry.created_at, today)).length,
      referralsToday: entries.filter(
        (entry) => entry.outcome === 'referral' && sameLocalDay(entry.created_at, today),
      ).length,
      emergencies: entries.filter((entry) => entry.outcome === 'emergency').length,
    }),
    [entries, today],
  )

  // Emergencies are pinned above the rest so a caregiver cannot miss them.
  const rows = useMemo(
    () => [...entries].sort((a, b) => Number(b.outcome === 'emergency') - Number(a.outcome === 'emergency')),
    [entries],
  )

  return (
    <main className="min-h-screen bg-linear-to-b from-teal-50 via-white to-amber-50 px-4 py-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <Brand subtitle="Caregiver" />
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Question log</h1>
            <p className="mt-1 text-sm text-slate-600">
              What the elder asked and what the app answered, newest first.
            </p>
          </div>
          <a
            href="/"
            className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Back to setup
          </a>
        </header>

        <section className="grid gap-3 sm:grid-cols-3">
          <div className={summaryCard}>
            <p className="text-sm font-medium text-slate-600">Questions today</p>
            <p className="mt-1 text-3xl font-bold text-slate-900">{counts.questionsToday}</p>
          </div>
          <div className={summaryCard}>
            <p className="text-sm font-medium text-slate-600">Referrals today</p>
            <p className="mt-1 text-3xl font-bold text-orange-800">{counts.referralsToday}</p>
          </div>
          <div className={summaryCard}>
            <p className="text-sm font-medium text-slate-600">Emergencies</p>
            <p className="mt-1 text-3xl font-bold text-red-700">{counts.emergencies}</p>
          </div>
        </section>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-base text-red-800">
            {error}
          </p>
        )}

        <section className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
          {loading ? (
            <p className="px-5 py-8 text-base text-slate-600">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="px-5 py-8 text-base text-slate-600">
              No questions yet. They appear here after the elder uses their link.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th scope="col" className="px-4 py-3 font-semibold">
                      Time
                    </th>
                    <th scope="col" className="px-4 py-3 font-semibold">
                      Question
                    </th>
                    <th scope="col" className="px-4 py-3 font-semibold">
                      Outcome
                    </th>
                    <th scope="col" className="px-4 py-3 font-semibold">
                      Answer
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((entry) => {
                    const emergency = entry.outcome === 'emergency'
                    const style = outcomeStyle(entry.outcome)
                    return (
                      <tr
                        key={entry.id}
                        className={`border-b border-slate-100 align-top last:border-0 ${
                          emergency ? 'border-l-4 border-l-red-600 bg-red-50' : ''
                        }`}
                      >
                        <td
                          className={`whitespace-nowrap px-4 py-3 ${emergency ? 'font-semibold text-red-800' : 'text-slate-600'}`}
                        >
                          {formatTime(entry.created_at, today)}
                        </td>
                        <td className={`px-4 py-3 ${emergency ? 'font-medium text-red-900' : 'text-slate-900'}`}>
                          {entry.transcript || <span className="text-slate-400">(nothing heard)</span>}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${style.tag}`}>
                            {style.label}
                          </span>
                        </td>
                        <td className={`px-4 py-3 ${emergency ? 'text-red-900' : 'text-slate-700'}`}>
                          {entry.answer_text}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {!loading && rows.length > 0 && (
          <p className="text-xs text-slate-500">Showing the {rows.length} most recent questions.</p>
        )}
      </div>
    </main>
  )
}
