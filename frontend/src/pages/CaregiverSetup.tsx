import { useEffect, useRef, useState, type FormEvent } from 'react'
import {
  addMedicine,
  confirmMedicine,
  createProfile,
  deleteMedicine,
  getProfile,
  updateMedicine,
  type Food,
  type Medicine,
  type MedicineInput,
  type Profile,
  type TimeOfDay,
} from '../lib/api'

const TIMES: { value: TimeOfDay; label: string }[] = [
  { value: 'morning', label: 'Morning' },
  { value: 'afternoon', label: 'Afternoon' },
  { value: 'night', label: 'Night' },
]

// Colour words are stored in Kannada script because Prisma writes the elder's
// speech in Kannada script; the backend adds the Roman form as an alias.
const COLOURS: { value: string; label: string }[] = [
  { value: 'ಬಿಳಿ', label: 'ಬಿಳಿ (white)' },
  { value: 'ಹಳದಿ', label: 'ಹಳದಿ (yellow)' },
  { value: 'ಕೆಂಪು', label: 'ಕೆಂಪು (red)' },
  { value: 'ನೀಲಿ', label: 'ನೀಲಿ (blue)' },
  { value: 'ಹಸಿರು', label: 'ಹಸಿರು (green)' },
  { value: 'ಕಿತ್ತಳೆ', label: 'ಕಿತ್ತಳೆ (orange)' },
  { value: 'ಗುಲಾಬಿ', label: 'ಗುಲಾಬಿ (pink)' },
  { value: 'ಕಪ್ಪು', label: 'ಕಪ್ಪು (black)' },
  { value: 'ಕಂದು', label: 'ಕಂದು (brown)' },
]

const FOODS: { value: Food; label: string }[] = [
  { value: 'before', label: 'Before food' },
  { value: 'after', label: 'After food' },
  { value: 'any', label: 'With or without food' },
]

// Where the browser remembers which profile this caregiver is editing.
const STORAGE_KEY = 'caregiverProfileId'

interface Draft {
  name: string
  aliases: string
  label: string
  color_word: string
  dose: string
  times: TimeOfDay[]
  food: Food
  days_total: string
  start_date: string
  purpose: string
  photo_path: string
}

const emptyDraft: Draft = {
  name: '',
  aliases: '',
  label: '',
  color_word: '',
  dose: '',
  times: [],
  food: 'any',
  days_total: '',
  start_date: '',
  purpose: '',
  photo_path: '',
}

function draftFromMedicine(medicine: Medicine): Draft {
  return {
    name: medicine.name,
    aliases: medicine.aliases.join(', '),
    label: medicine.label,
    color_word: medicine.color_word,
    dose: medicine.dose,
    times: medicine.times,
    food: medicine.food,
    days_total: medicine.days_total === null ? '' : String(medicine.days_total),
    start_date: medicine.start_date ?? '',
    purpose: medicine.purpose ?? '',
    photo_path: medicine.photo_path ?? '',
  }
}

// Blank optional fields become null so the database holds "not written" rather than "".
function toInput(draft: Draft): MedicineInput {
  return {
    name: draft.name.trim(),
    aliases: draft.aliases
      .split(',')
      .map((alias) => alias.trim())
      .filter((alias) => alias.length > 0),
    label: draft.label.trim(),
    color_word: draft.color_word.trim(),
    dose: draft.dose.trim(),
    times: draft.times,
    food: draft.food,
    days_total: draft.days_total === '' ? null : Number(draft.days_total),
    start_date: draft.start_date === '' ? null : draft.start_date,
    purpose: draft.purpose.trim() === '' ? null : draft.purpose.trim(),
    photo_path: draft.photo_path.trim() === '' ? null : draft.photo_path.trim(),
  }
}

const inputClass =
  'mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-base text-slate-900 focus:border-teal-600 focus:ring-2 focus:ring-teal-100 focus:outline-none'
// Same look as the elder page: soft teal-to-warm background, white cards.
const pageClass = 'min-h-screen bg-linear-to-b from-teal-50 via-white to-amber-50 px-4'
const cardClass = 'rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100'

/** The MedVoice mark shared with the elder page. */
export function Brand({ subtitle }: { subtitle: string }) {
  return (
    <div className="flex items-center gap-2 text-teal-800">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-700 text-white">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-4 w-4">
          <path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z" />
        </svg>
      </span>
      <span className="text-xl font-bold tracking-tight">MedVoice</span>
      <span className="ml-1 rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-semibold text-teal-800 ring-1 ring-teal-100">
        {subtitle}
      </span>
    </div>
  )
}
const labelClass = 'block text-sm font-medium text-slate-700'
const primaryButton =
  'rounded-xl bg-teal-700 px-4 py-2 text-base font-semibold text-white shadow-sm hover:bg-teal-800 disabled:opacity-50'
const secondaryButton =
  'rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50'

export default function CaregiverSetup() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [medicines, setMedicines] = useState<Medicine[]>([])
  const [elderName, setElderName] = useState('')
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    const savedId = Number(localStorage.getItem(STORAGE_KEY))
    if (!savedId) return
    getProfile(savedId)
      .then((data) => {
        setProfile(data.profile)
        setMedicines(data.medicines)
      })
      .catch(() => localStorage.removeItem(STORAGE_KEY))
  }, [])

  async function refresh(profileId: number) {
    const data = await getProfile(profileId)
    setProfile(data.profile)
    setMedicines(data.medicines)
  }

  async function run(action: () => Promise<void>) {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  function handleCreateProfile(event: FormEvent) {
    event.preventDefault()
    void run(async () => {
      const created = await createProfile(elderName)
      localStorage.setItem(STORAGE_KEY, String(created.id))
      setElderName('')
      await refresh(created.id)
    })
  }

  function handleSubmitMedicine(event: FormEvent) {
    event.preventDefault()
    if (!profile) return
    const input = toInput(draft)
    void run(async () => {
      if (editingId === null) await addMedicine(profile.id, input)
      else await updateMedicine(editingId, input)
      setDraft(emptyDraft)
      setEditingId(null)
      await refresh(profile.id)
    })
  }

  function handleEdit(medicine: Medicine) {
    setEditingId(medicine.id)
    setDraft(draftFromMedicine(medicine))
    setError(null)
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleCancelEdit() {
    setEditingId(null)
    setDraft(emptyDraft)
  }

  function handleConfirm(medicine: Medicine) {
    if (!profile) return
    void run(async () => {
      await confirmMedicine(medicine.id)
      await refresh(profile.id)
    })
  }

  function handleDelete(medicine: Medicine) {
    if (!profile) return
    if (!window.confirm(`Remove ${medicine.name} from the list?`)) return
    void run(async () => {
      await deleteMedicine(medicine.id)
      if (editingId === medicine.id) handleCancelEdit()
      await refresh(profile.id)
    })
  }

  function toggleTime(time: TimeOfDay) {
    setDraft((current) => ({
      ...current,
      times: current.times.includes(time)
        ? current.times.filter((value) => value !== time)
        : [...current.times, time],
    }))
  }

  const elderLink = profile ? `${window.location.origin}/elder/${profile.share_token}` : ''

  function handleCopyLink() {
    navigator.clipboard.writeText(elderLink).then(
      () => {
        setCopied(true)
        setError(null)
      },
      () => setError('Could not copy the link — select it and copy it by hand.'),
    )
  }

  if (!profile) {
    return (
      <main className={`${pageClass} py-10`}>
        <div className="mx-auto max-w-md">
          <Brand subtitle="Caregiver" />
          <h1 className="mt-6 text-2xl font-bold text-slate-900">Set up an elder</h1>
          <p className="mt-2 text-base text-slate-600">
            Caregiver setup: enter the elder&apos;s prescription once, then confirm every medicine so it can be
            spoken back in Kannada.
          </p>

          <form onSubmit={handleCreateProfile} className={`mt-6 ${cardClass}`}>
            <label className={labelClass} htmlFor="elder-name">
              Elder&apos;s name
            </label>
            <input
              id="elder-name"
              required
              value={elderName}
              onChange={(event) => setElderName(event.target.value)}
              className={inputClass}
              placeholder="For example: Test Elder"
            />
            <button type="submit" disabled={busy} className={`mt-4 w-full ${primaryButton}`}>
              {busy ? 'Creating…' : 'Create profile'}
            </button>
          </form>

          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-base text-red-800">
              {error}
            </p>
          )}
        </div>
      </main>
    )
  }

  return (
    <main className={`${pageClass} py-6`}>
      <div className="mx-auto max-w-3xl space-y-6">
        <Brand subtitle="Caregiver" />
        <header className={cardClass}>
          <h1 className="text-2xl font-bold text-slate-900">{profile.elder_name}</h1>
          <p className="mt-1 text-sm text-slate-600">
            Language: {profile.language} · Elder link for this profile
          </p>

          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
            <code className="flex-1 overflow-x-auto rounded-xl bg-slate-50 ring-1 ring-slate-100 px-3 py-2 text-sm text-slate-800">
              {elderLink}
            </code>
            <button type="button" onClick={handleCopyLink} className={secondaryButton}>
              {copied ? 'Copied' : 'Copy link'}
            </button>
            <a href={`/log/${profile.id}`} className={`${secondaryButton} text-center`}>
              Question log
            </a>
          </div>
        </header>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-base text-red-800">
            {error}
          </p>
        )}

        <form ref={formRef} onSubmit={handleSubmitMedicine} className={cardClass}>
          <h2 className="text-lg font-semibold text-slate-900">
            {editingId === null ? 'Add a medicine' : `Editing: ${draft.name}`}
          </h2>
          {editingId !== null && (
            <p className="mt-1 text-sm text-amber-700">
              Saving changes marks this medicine as not confirmed, so the elder stays silent about it until you confirm
              again.
            </p>
          )}

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass} htmlFor="med-name">
                Name as written on the prescription
              </label>
              <input
                id="med-name"
                required
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                className={inputClass}
                placeholder="Amlodipine 5mg"
              />
            </div>

            <div>
              <label className={labelClass} htmlFor="med-aliases">
                Other names the elder may use
              </label>
              <input
                id="med-aliases"
                value={draft.aliases}
                onChange={(event) => setDraft({ ...draft, aliases: event.target.value })}
                className={inputClass}
                placeholder="BP tablet, ಬಿಪಿ ಮಾತ್ರೆ, amlo"
              />
              <p className="mt-1 text-xs text-slate-500">Separate with commas.</p>
            </div>

            <div>
              <label className={labelClass} htmlFor="med-label">
                How the elder knows it
              </label>
              <input
                id="med-label"
                required
                value={draft.label}
                onChange={(event) => setDraft({ ...draft, label: event.target.value })}
                className={inputClass}
                placeholder="ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ"
              />
              <p className="mt-1 text-xs text-slate-500">In Kannada, the way the elder says it.</p>
            </div>

            <div>
              <label className={labelClass} htmlFor="med-color">
                Colour word
              </label>
              <select
                id="med-color"
                required
                value={draft.color_word}
                onChange={(event) => setDraft({ ...draft, color_word: event.target.value })}
                className={inputClass}
              >
                <option value="" disabled>
                  Choose the tablet's colour
                </option>
                {COLOURS.map((colour) => (
                  <option key={colour.value} value={colour.value}>
                    {colour.label}
                  </option>
                ))}
                {draft.color_word !== '' && !COLOURS.some((colour) => colour.value === draft.color_word) && (
                  // An older free-text value (e.g. "bili") stays selectable until changed.
                  <option value={draft.color_word}>{draft.color_word}</option>
                )}
              </select>
            </div>

            <div>
              <label className={labelClass} htmlFor="med-dose">
                Dose
              </label>
              <input
                id="med-dose"
                required
                value={draft.dose}
                onChange={(event) => setDraft({ ...draft, dose: event.target.value })}
                className={inputClass}
                placeholder="1 ಮಾತ್ರೆ"
              />
            </div>

            <div>
              <label className={labelClass} htmlFor="med-food">
                With food
              </label>
              <select
                id="med-food"
                value={draft.food}
                onChange={(event) => setDraft({ ...draft, food: event.target.value as Food })}
                className={inputClass}
              >
                {FOODS.map((food) => (
                  <option key={food.value} value={food.value}>
                    {food.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <span className={labelClass}>When to take it</span>
              <div className="mt-2 flex flex-wrap gap-4">
                {TIMES.map((time) => (
                  <label key={time.value} className="flex items-center gap-2 text-base text-slate-800">
                    <input
                      type="checkbox"
                      checked={draft.times.includes(time.value)}
                      onChange={() => toggleTime(time.value)}
                      className="h-5 w-5 rounded border-slate-300"
                    />
                    {time.label}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className={labelClass} htmlFor="med-days">
                Total days (optional)
              </label>
              <input
                id="med-days"
                type="number"
                min={1}
                value={draft.days_total}
                onChange={(event) => setDraft({ ...draft, days_total: event.target.value })}
                className={inputClass}
                placeholder="30"
              />
            </div>

            <div>
              <label className={labelClass} htmlFor="med-start">
                Start date (optional)
              </label>
              <input
                id="med-start"
                type="date"
                value={draft.start_date}
                onChange={(event) => setDraft({ ...draft, start_date: event.target.value })}
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass} htmlFor="med-purpose">
                Purpose, only if written on the prescription (optional)
              </label>
              <input
                id="med-purpose"
                value={draft.purpose}
                onChange={(event) => setDraft({ ...draft, purpose: event.target.value })}
                className={inputClass}
                placeholder="ಬಿಪಿ ಮಾತ್ರೆ"
              />
              <p className="mt-1 text-xs text-slate-500">Spoken as "ಇದು …", so write it to fit that sentence.</p>
            </div>

            <div>
              <label className={labelClass} htmlFor="med-photo">
                Photo link or file name (optional)
              </label>
              <input
                id="med-photo"
                value={draft.photo_path}
                onChange={(event) => setDraft({ ...draft, photo_path: event.target.value })}
                className={inputClass}
                placeholder="/photos/amlo.jpg"
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button type="submit" disabled={busy} className={primaryButton}>
              {editingId === null ? 'Add medicine' : 'Save changes'}
            </button>
            {editingId !== null && (
              <button type="button" onClick={handleCancelEdit} className={secondaryButton}>
                Cancel edit
              </button>
            )}
          </div>
        </form>

        <section className={cardClass}>
          <h2 className="text-lg font-semibold text-slate-900">
            Medicines ({medicines.filter((medicine) => medicine.confirmed).length} confirmed of {medicines.length})
          </h2>

          {medicines.length === 0 ? (
            <p className="mt-2 text-base text-slate-600">No medicines yet. Add the first one above.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {medicines.map((medicine) => (
                <li
                  key={medicine.id}
                  className={`rounded-xl border p-4 ${
                    medicine.confirmed ? 'border-teal-200 bg-teal-50/40' : 'border-amber-300 bg-amber-50'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-base font-semibold text-slate-900">{medicine.name}</p>
                      <p className="text-sm text-slate-700">
                        {medicine.label} · {medicine.color_word} · {medicine.dose}
                      </p>
                      <p className="text-sm text-slate-700">
                        Times: {medicine.times.length > 0 ? medicine.times.join(', ') : 'not set'} · Food:{' '}
                        {medicine.food}
                      </p>
                      {medicine.aliases.length > 0 && (
                        <p className="text-sm text-slate-600">Also called: {medicine.aliases.join(', ')}</p>
                      )}
                      {(medicine.purpose || medicine.days_total || medicine.start_date) && (
                        <p className="text-sm text-slate-600">
                          {medicine.purpose && <>Purpose: {medicine.purpose} · </>}
                          {medicine.days_total && <>Days: {medicine.days_total} · </>}
                          {medicine.start_date && <>Started: {medicine.start_date}</>}
                        </p>
                      )}
                    </div>

                    <span
                      className={`rounded-full px-3 py-1 text-sm font-medium ${
                        medicine.confirmed ? 'bg-teal-700 text-white' : 'bg-amber-600 text-white'
                      }`}
                    >
                      {medicine.confirmed ? 'Confirmed' : 'Not confirmed'}
                    </span>
                  </div>

                  {!medicine.confirmed && (
                    <p className="mt-2 text-sm font-medium text-amber-800">
                      Hidden from the elder until you confirm it.
                    </p>
                  )}

                  <div className="mt-3 flex flex-wrap gap-2">
                    {!medicine.confirmed && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleConfirm(medicine)}
                        className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                      >
                        Confirm
                      </button>
                    )}
                    <button type="button" onClick={() => handleEdit(medicine)} className={secondaryButton}>
                      Edit
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDelete(medicine)}
                      className="rounded-xl border border-red-200 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  )
}
