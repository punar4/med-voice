import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
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
import { Icon, type IconName } from '../lib/icons'

const TIMES: { value: TimeOfDay; label: { en: string; kn: string } }[] = [
  { value: 'morning', label: { en: 'Morning', kn: 'ಬೆಳಿಗ್ಗೆ' } },
  { value: 'afternoon', label: { en: 'Afternoon', kn: 'ಮಧ್ಯಾಹ್ನ' } },
  { value: 'night', label: { en: 'Night', kn: 'ರಾತ್ರಿ' } },
]

// Caregiver UI text: one language on screen at a time (switch at the top).
// Medicine details the caregiver types (labels, dose, purpose) stay as typed:
// they are what the elder hears, so they are always Kannada.
type CLang = 'en' | 'kn'
const CLANG_KEY = 'medvoice-caregiver-lang'

const T = {
  caregiver: { en: 'Caregiver', kn: 'ಕುಟುಂಬದವರು' },
  getStarted: { en: 'Get started', kn: 'ಶುರು ಮಾಡಿ' },
  heroTitle: { en: 'Help an elder with their medicines', kn: 'ಹಿರಿಯರಿಗೆ ಮಾತ್ರೆ ವಿಷಯದಲ್ಲಿ ಸಹಾಯ ಮಾಡಿ' },
  stepAdd: { en: 'Add each tablet once, the way the elder describes it.', kn: 'ಪ್ರತಿ ಮಾತ್ರೆಯನ್ನ ಒಂದ್ಸಲ ಸೇರಿಸಿ, ಹಿರಿಯರು ಹೇಳೋ ಹಾಗೆ.' },
  stepConfirm: { en: 'Confirm it. Only confirmed tablets are ever spoken about.', kn: 'ಖಚಿತ ಮಾಡಿ. ಖಚಿತ ಮಾಡಿದ ಮಾತ್ರೆ ಬಗ್ಗೆ ಮಾತ್ರ ಉತ್ತರ ಬರುತ್ತೆ.' },
  stepShare: { en: 'Send the elder their link. They ask in Kannada.', kn: 'ಹಿರಿಯರಿಗೆ ಲಿಂಕ್ ಕಳಿಸಿ. ಅವರು ಕನ್ನಡದಲ್ಲಿ ಕೇಳ್ತಾರೆ.' },
  elderName: { en: "Elder's name", kn: 'ಹಿರಿಯರ ಹೆಸರು' },
  namePlaceholder: { en: 'For example: Ajji', kn: 'ಉದಾ: ಅಜ್ಜಿ' },
  creating: { en: 'Creating…', kn: 'ಮಾಡ್ತಾ ಇದೀನಿ…' },
  createProfile: { en: 'Create profile', kn: 'ಪ್ರೊಫೈಲ್ ಮಾಡಿ' },
  speaksKannada: { en: 'Speaks Kannada', kn: 'ಕನ್ನಡ ಮಾತಾಡ್ತಾರೆ' },
  confirmedCount: { en: 'confirmed', kn: 'ಖಚಿತ' },
  waitingCount: { en: 'waiting', kn: 'ಬಾಕಿ' },
  linkTitle: { en: "Elder's page: send this link to their phone", kn: 'ಹಿರಿಯರ ಪೇಜ್: ಈ ಲಿಂಕ್ ಅವರ ಫೋನ್‌ಗೆ ಕಳಿಸಿ' },
  copyLink: { en: 'Copy link', kn: 'ಲಿಂಕ್ ಕಾಪಿ' },
  copied: { en: 'Copied', kn: 'ಕಾಪಿ ಆಯ್ತು' },
  open: { en: 'Open', kn: 'ತೆರೆಯಿರಿ' },
  questionLog: { en: 'Question log', kn: 'ಕೇಳಿದ ಪ್ರಶ್ನೆಗಳು' },
  copyFailed: { en: 'Could not copy the link. Select it and copy it by hand.', kn: 'ಲಿಂಕ್ ಕಾಪಿ ಆಗ್ಲಿಲ್ಲ. ಕೈಯಲ್ಲೇ ಕಾಪಿ ಮಾಡಿ.' },
  needsTitle: { en: 'Needs your confirmation:', kn: 'ನೀವು ಖಚಿತ ಮಾಡಬೇಕು:' },
  needsBodyOne: { en: 'tablet is hidden from the elder until you check and confirm.', kn: 'ಮಾತ್ರೆ ನೀವು ನೋಡಿ ಖಚಿತ ಮಾಡೋವರೆಗೂ ಹಿರಿಯರಿಗೆ ಕಾಣಲ್ಲ.' },
  needsBodyMany: { en: 'tablets are hidden from the elder until you check and confirm.', kn: 'ಮಾತ್ರೆಗಳು ನೀವು ನೋಡಿ ಖಚಿತ ಮಾಡೋವರೆಗೂ ಹಿರಿಯರಿಗೆ ಕಾಣಲ್ಲ.' },
  todaysPlan: { en: "Today's plan", kn: 'ಇವತ್ತಿನ ಪ್ಲಾನ್' },
  nothing: { en: 'Nothing', kn: 'ಏನೂ ಇಲ್ಲ' },
  medicines: { en: 'Medicines', kn: 'ಮಾತ್ರೆಗಳು' },
  addMedicine: { en: 'Add medicine', kn: 'ಮಾತ್ರೆ ಸೇರಿಸಿ' },
  noMedicines: { en: 'No medicines yet. Add the first one below.', kn: 'ಇನ್ನೂ ಮಾತ್ರೆ ಇಲ್ಲ. ಕೆಳಗೆ ಮೊದಲನೆಯದು ಸೇರಿಸಿ.' },
  confirmed: { en: 'Confirmed', kn: 'ಖಚಿತ' },
  notConfirmed: { en: 'Not confirmed', kn: 'ಖಚಿತ ಆಗಿಲ್ಲ' },
  daysLeft: { en: 'days left', kn: 'ದಿನ ಬಾಕಿ' },
  courseOver: { en: 'Course over', kn: 'ಕೋರ್ಸ್ ಮುಗೀತು' },
  purposeFor: { en: 'For', kn: 'ಯಾಕೆ' },
  alsoCalled: { en: 'Also called', kn: 'ಬೇರೆ ಹೆಸರು' },
  checkConfirm: { en: 'Check & confirm', kn: 'ನೋಡಿ ಖಚಿತ ಮಾಡಿ' },
  edit: { en: 'Edit', kn: 'ಬದಲಾಯಿಸಿ' },
  remove: { en: 'Remove', kn: 'ತೆಗೆಯಿರಿ' },
  removeAsk: { en: 'Remove this medicine from the list?', kn: 'ಈ ಮಾತ್ರೆಯನ್ನ ಪಟ್ಟಿಯಿಂದ ತೆಗೆಯಲಾ?' },
  addTitle: { en: 'Add a medicine', kn: 'ಹೊಸ ಮಾತ್ರೆ ಸೇರಿಸಿ' },
  editing: { en: 'Editing', kn: 'ಬದಲಾಯಿಸ್ತಾ ಇದೀರಿ' },
  editWarning: {
    en: 'Saving changes marks this medicine as not confirmed, so the elder stays silent about it until you confirm again.',
    kn: 'ಬದಲಾವಣೆ ಉಳಿಸಿದ್ರೆ ಈ ಮಾತ್ರೆ "ಖಚಿತ ಆಗಿಲ್ಲ" ಆಗುತ್ತೆ. ಮತ್ತೆ ಖಚಿತ ಮಾಡೋವರೆಗೂ ಹಿರಿಯರಿಗೆ ಇದರ ಬಗ್ಗೆ ಉತ್ತರ ಬರಲ್ಲ.',
  },
  step1: { en: 'How the elder knows it', kn: 'ಹಿರಿಯರು ಇದನ್ನ ಹೇಗೆ ಕರೀತಾರೆ' },
  step1Hint: { en: 'In Kannada, the way they would say it out loud.', kn: 'ಅವರು ಮಾತಾಡೋ ಹಾಗೆ, ಕನ್ನಡದಲ್ಲಿ.' },
  fieldLabel: { en: 'What the elder calls it', kn: 'ಹಿರಿಯರು ಕರೆಯೋ ಹೆಸರು' },
  fieldColour: { en: 'Colour', kn: 'ಬಣ್ಣ' },
  chooseColour: { en: "Choose the tablet's colour", kn: 'ಮಾತ್ರೆಯ ಬಣ್ಣ ಆರಿಸಿ' },
  fieldName: { en: 'Name on the prescription', kn: 'ಚೀಟೀಲಿರೋ ಹೆಸರು' },
  fieldAliases: { en: 'Other names they may use', kn: 'ಬೇರೆ ಹೆಸರುಗಳು' },
  aliasesPlaceholder: { en: 'BP tablet, amlo', kn: 'ಬಿಪಿ ಮಾತ್ರೆ' },
  commas: { en: 'Separate with commas.', kn: 'ಕಾಮಾ ಹಾಕಿ ಬೇರೆ ಮಾಡಿ.' },
  step2: { en: 'Dose and timing', kn: 'ಡೋಸ್ ಮತ್ತೆ ಸಮಯ' },
  step2Hint: { en: 'Write the dose in Kannada: the elder hears it.', kn: 'ಡೋಸ್ ಕನ್ನಡದಲ್ಲಿ ಬರೀರಿ: ಹಿರಿಯರಿಗೆ ಇದೇ ಕೇಳಿಸುತ್ತೆ.' },
  fieldDose: { en: 'Dose each time', kn: 'ಒಂದ್ಸಲಕ್ಕೆ ಎಷ್ಟು' },
  fieldFood: { en: 'With food', kn: 'ಊಟದ ಜೊತೆ' },
  fieldWhen: { en: 'When to take it', kn: 'ಯಾವಾಗ ತಗೋಬೇಕು' },
  step3: { en: 'Course and extras', kn: 'ಕೋರ್ಸ್ ಮತ್ತೆ ಇತರೆ' },
  step3Hint: { en: "Optional. Leave blank if it isn't on the prescription.", kn: 'ಬೇಕಾದ್ರೆ ಮಾತ್ರ. ಚೀಟೀಲಿ ಇಲ್ಲದಿದ್ರೆ ಖಾಲಿ ಬಿಡಿ.' },
  fieldDays: { en: 'Total days', kn: 'ಒಟ್ಟು ದಿನ' },
  fieldStart: { en: 'Start date', kn: 'ಶುರು ಆದ ದಿನ' },
  fieldPurpose: { en: 'Purpose (only if written)', kn: 'ಯಾಕೆ (ಬರೆದಿದ್ರೆ ಮಾತ್ರ)' },
  purposeHint: { en: 'Spoken as "ಇದು …", so write it to fit that sentence.', kn: '"ಇದು …" ಅಂತ ಹೇಳುತ್ತೆ, ಅದಕ್ಕೆ ಸರಿಹೊಂದೋ ಹಾಗೆ ಬರೀರಿ.' },
  fieldPhoto: { en: 'Photo link', kn: 'ಫೋಟೋ ಲಿಂಕ್' },
  saveMedicine: { en: 'Save medicine', kn: 'ಮಾತ್ರೆ ಉಳಿಸಿ' },
  saveChanges: { en: 'Save changes', kn: 'ಬದಲಾವಣೆ ಉಳಿಸಿ' },
  cancel: { en: 'Cancel', kn: 'ಬೇಡ' },
  newStartsUnconfirmed: {
    en: 'New medicines start as not confirmed. Check them against the prescription, then press Check & confirm.',
    kn: 'ಹೊಸ ಮಾತ್ರೆ "ಖಚಿತ ಆಗಿಲ್ಲ" ಅಂತ ಶುರು ಆಗುತ್ತೆ. ಚೀಟಿ ಜೊತೆ ಹೋಲಿಸಿ, ಆಮೇಲೆ "ನೋಡಿ ಖಚಿತ ಮಾಡಿ" ಒತ್ತಿ.',
  },
} satisfies Record<string, { en: string; kn: string }>

function savedCLang(): CLang {
  try {
    return window.localStorage.getItem(CLANG_KEY) === 'kn' ? 'kn' : 'en'
  } catch {
    return 'en'
  }
}

function CLangSwitch({ lang, onChange }: { lang: CLang; onChange: (lang: CLang) => void }) {
  const option = (value: CLang, text: string) => (
    <button
      type="button"
      onClick={() => onChange(value)}
      aria-pressed={lang === value}
      className={`min-h-9 rounded-full px-3 text-sm font-semibold transition-colors ${
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


// Colour words are stored in Kannada script because Prisma writes the elder's
// speech in Kannada script; the backend adds the Roman form as an alias.
const COLOURS: { value: string; label: { en: string; kn: string } }[] = [
  { value: 'ಬಿಳಿ', label: { en: 'White', kn: 'ಬಿಳಿ' } },
  { value: 'ಹಳದಿ', label: { en: 'Yellow', kn: 'ಹಳದಿ' } },
  { value: 'ಕೆಂಪು', label: { en: 'Red', kn: 'ಕೆಂಪು' } },
  { value: 'ನೀಲಿ', label: { en: 'Blue', kn: 'ನೀಲಿ' } },
  { value: 'ಹಸಿರು', label: { en: 'Green', kn: 'ಹಸಿರು' } },
  { value: 'ಕಿತ್ತಳೆ', label: { en: 'Orange', kn: 'ಕಿತ್ತಳೆ' } },
  { value: 'ಗುಲಾಬಿ', label: { en: 'Pink', kn: 'ಗುಲಾಬಿ' } },
  { value: 'ಕಪ್ಪು', label: { en: 'Black', kn: 'ಕಪ್ಪು' } },
  { value: 'ಕಂದು', label: { en: 'Brown', kn: 'ಕಂದು' } },
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
  'mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-base text-slate-900 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 focus:outline-none'
// Same look as the elder page: soft blue-to-warm background, white cards.
const pageClass = 'min-h-screen bg-linear-to-b from-blue-50 via-white to-slate-100 px-4'
const cardClass = 'rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100'

/** The MedVoice mark shared with the elder page. */
export function Brand({ subtitle, right }: { subtitle: string; right?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
    <div className="flex items-center gap-2 text-[#0C2451]">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0C2451] text-white">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-4 w-4">
          <path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z" />
        </svg>
      </span>
      <span className="text-xl font-bold tracking-tight">MedVoice</span>
      <span className="ml-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-[#0C2451] ring-1 ring-blue-100">
        {subtitle}
      </span>
    </div>
    {right}
    </div>
  )
}
const labelClass = 'block text-sm font-semibold text-slate-700'
// 48px-high controls throughout: easy to hit for older caregivers too.
const primaryButton =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#0C2451] px-5 text-base font-semibold text-white shadow-sm hover:bg-[#13306b] disabled:opacity-50'
const secondaryButton =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-base font-medium text-slate-700 hover:bg-slate-50'

// The colour the caregiver picked, shown as a pill so tablets are recognisable at a glance.
const PILL_COLOURS: Record<string, string> = {
  'ಬಿಳಿ': '#ffffff',
  'ಹಳದಿ': '#facc15',
  'ಕೆಂಪು': '#ef4444',
  'ನೀಲಿ': '#3b82f6',
  'ಹಸಿರು': '#22c55e',
  'ಕಿತ್ತಳೆ': '#f97316',
  'ಗುಲಾಬಿ': '#ec4899',
  'ಕಪ್ಪು': '#111827',
  'ಕಂದು': '#92400e',
}

function Pill({ colour, size = 'h-12 w-12' }: { colour: string; size?: string }) {
  return (
    <span
      className={`flex ${size} shrink-0 items-center justify-center rounded-2xl bg-slate-50 ring-1 ring-slate-200`}
      aria-hidden="true"
    >
      <span
        className={`${size.includes('h-8') ? 'h-2.5 w-5' : 'h-4 w-8'} rounded-full shadow-inner ring-1 ring-slate-300`}
        style={{ backgroundColor: PILL_COLOURS[colour] ?? '#cbd5e1' }}
      />
    </span>
  )
}

const TIME_ICONS: Record<TimeOfDay, IconName> = {
  morning: 'sunrise',
  afternoon: 'sun',
  night: 'moon',
}

const FOOD_TEXT: Record<Food, { en: string; kn: string }> = {
  before: { en: 'Before food', kn: 'ಊಟಕ್ಕೆ ಮುಂಚೆ' },
  after: { en: 'After food', kn: 'ಊಟ ಆದ್ಮೇಲೆ' },
  any: { en: 'Any time', kn: 'ಯಾವಾಗ ಬೇಕಾದ್ರೂ' },
}

// Coloured like the things they stand for, so they read as fast as emoji.
const TIME_ICON_COLOURS: Record<TimeOfDay, string> = {
  morning: 'text-amber-500',
  afternoon: 'text-orange-500',
  night: 'text-indigo-500',
}

function daysLeft(medicine: Medicine): number | null {
  if (!medicine.days_total || !medicine.start_date) return null
  const start = new Date(medicine.start_date + 'T00:00:00')
  const used = Math.floor((Date.now() - start.getTime()) / 86_400_000)
  return medicine.days_total - used
}

function StepTitle({ number, title, hint }: { number: number; title: string; hint?: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-bold text-[#0C2451] ring-1 ring-blue-100">
        {number}
      </span>
      <div>
        <p className="text-base font-bold text-slate-900">{title}</p>
        {hint && <p className="text-sm text-slate-500">{hint}</p>}
      </div>
    </div>
  )
}

export default function CaregiverSetup() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [medicines, setMedicines] = useState<Medicine[]>([])
  const [elderName, setElderName] = useState('')
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [lang, setLang] = useState<CLang>(savedCLang)
  const t = (key: keyof typeof T) => T[key][lang]
  function chooseLang(next: CLang) {
    setLang(next)
    try {
      window.localStorage.setItem(CLANG_KEY, next)
    } catch {
      // Private mode: the choice just isn't remembered.
    }
  }
  const langSwitch = <CLangSwitch lang={lang} onChange={chooseLang} />
  const formRef = useRef<HTMLFormElement>(null)
  const [formOpen, setFormOpen] = useState(false)

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
    setFormOpen(true)
    setEditingId(medicine.id)
    setDraft(draftFromMedicine(medicine))
    setError(null)
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleCancelEdit() {
    setEditingId(null)
    setDraft(emptyDraft)
    setFormOpen(false)
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
    if (!window.confirm(`${t('removeAsk')}\n${medicine.name}`)) return
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
      () => setError(t('copyFailed')),
    )
  }

  if (!profile) {
    return (
      <main className={`${pageClass} py-8`}>
        <div className="mx-auto max-w-md">
          <Brand subtitle={t('caregiver')} right={langSwitch} />
          <section className={`mt-8 ${cardClass}`}>
            <p className="text-sm font-semibold tracking-wide text-blue-700 uppercase">{t('getStarted')}</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">{t('heroTitle')}</h1>
            <ul className="mt-4 space-y-2 text-base text-slate-700">
              <li className="flex items-start gap-2"><span className="mt-0.5 text-blue-600"><Icon name="pill" /></span> {t('stepAdd')}</li>
              <li className="flex items-start gap-2"><span className="mt-0.5 text-emerald-600"><Icon name="shield" /></span> {t('stepConfirm')}</li>
              <li className="flex items-start gap-2"><span className="mt-0.5 text-blue-600"><Icon name="link" /></span> {t('stepShare')}</li>
            </ul>

            <form onSubmit={handleCreateProfile} className="mt-6 border-t border-slate-100 pt-5">
              {error && (
                <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-base text-red-800 ring-1 ring-red-100">
                  {error}
                </p>
              )}
              <label className={labelClass} htmlFor="elder-name">
                {t('elderName')}
              </label>
              <input
                id="elder-name"
                required
                value={elderName}
                onChange={(event) => setElderName(event.target.value)}
                className={inputClass}
                placeholder={t('namePlaceholder')}
              />
              <button type="submit" disabled={busy} className={`mt-4 w-full ${primaryButton}`}>
                {busy ? t('creating') : t('createProfile')}
              </button>
            </form>
          </section>
        </div>
      </main>
    )
  }

  const confirmed = medicines.filter((medicine) => medicine.confirmed)
  const waiting = medicines.filter((medicine) => !medicine.confirmed)
  const showForm = formOpen || medicines.length === 0

  return (
    <main className={`${pageClass} py-6`}>
      <div className="mx-auto max-w-3xl space-y-5">
        <Brand subtitle={t('caregiver')} right={langSwitch} />

        {/* Who this is for, and the one link that matters. */}
        <header className={cardClass}>
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-[#3395FF] to-[#0C2451] text-2xl font-bold text-white">
              {profile.elder_name.trim().charAt(0).toUpperCase() || 'E'}
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-2xl font-bold text-slate-900">{profile.elder_name}</h1>
              <p className="text-sm text-slate-600">
                {profile.language === 'kn' ? t('speaksKannada') : profile.language} · {confirmed.length} {t('confirmedCount')}
                {waiting.length > 0 && <> · {waiting.length} {t('waitingCount')}</>}
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-2xl bg-blue-50/60 p-4 ring-1 ring-blue-100">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-[#0C2451]"><Icon name="link" className="h-4 w-4" /> {t('linkTitle')}</p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              <button type="button" onClick={handleCopyLink} className={primaryButton}>
                {copied ? <><Icon name="check" /> {t('copied')}</> : <><Icon name="copy" /> {t('copyLink')}</>}
              </button>
              <a href={elderLink} target="_blank" rel="noreferrer" className={`${secondaryButton} no-underline`}>
                <Icon name="external" /> {t('open')}
              </a>
              <a href={`/log/${profile.id}`} className={`${secondaryButton} col-span-2 no-underline sm:col-span-1`}>
                <Icon name="list" /> {t('questionLog')}
              </a>
            </div>
          </div>
        </header>

        {error && (
          <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-base text-red-800 ring-1 ring-red-100">
            {error}
          </p>
        )}

        {waiting.length > 0 && (
          <div className="flex items-start gap-3 rounded-2xl bg-amber-50 px-4 py-3 ring-1 ring-amber-200">
            <span className="mt-0.5 text-amber-700"><Icon name="alert" className="h-6 w-6" /></span>
            <p className="text-base text-amber-900">
              <span className="font-semibold">{t('needsTitle')}</span> {waiting.length}{' '}
              {waiting.length === 1 ? t('needsBodyOne') : t('needsBodyMany')}
            </p>
          </div>
        )}

        {/* At-a-glance day plan, built from confirmed tablets only. */}
        {confirmed.length > 0 && (
          <section className={cardClass}>
            <h2 className="text-lg font-bold text-slate-900">{t('todaysPlan')}</h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {TIMES.map((time) => {
                const due = confirmed.filter((medicine) => medicine.times.includes(time.value))
                return (
                  <div key={time.value} className="rounded-2xl bg-slate-50 p-3 ring-1 ring-slate-100">
                    <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-600">
                      <Icon name={TIME_ICONS[time.value]} className={`h-5 w-5 ${TIME_ICON_COLOURS[time.value]}`} /> {time.label[lang]}
                    </p>
                    {due.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-400">{t('nothing')}</p>
                    ) : (
                      <ul className="mt-2 space-y-2">
                        {due.map((medicine) => (
                          <li key={medicine.id} className="flex items-center gap-2">
                            <Pill colour={medicine.color_word} size="h-8 w-8" />
                            <span className="text-base font-medium text-slate-900">{medicine.label}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        )}

        <section className={cardClass}>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-slate-900">{t('medicines')}</h2>
            {!showForm && (
              <button
                type="button"
                onClick={() => {
                  setFormOpen(true)
                  setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
                }}
                className={primaryButton}
              >
                <Icon name="plus" /> {t('addMedicine')}
              </button>
            )}
          </div>

          {medicines.length === 0 ? (
            <p className="mt-2 text-base text-slate-600">{t('noMedicines')}</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {medicines.map((medicine) => {
                const left = daysLeft(medicine)
                return (
                  <li
                    key={medicine.id}
                    className={`rounded-2xl p-4 ring-1 ${
                      medicine.confirmed ? 'bg-white ring-slate-200' : 'bg-amber-50/60 ring-amber-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <Pill colour={medicine.color_word} />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-lg font-bold text-slate-900">{medicine.label}</p>
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold ring-1 ${
                              medicine.confirmed
                                ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
                                : 'bg-amber-100 text-amber-900 ring-amber-300'
                            }`}
                          >
                            {medicine.confirmed ? <><Icon name="check" className="h-4 w-4" /> {t('confirmed')}</> : <><Icon name="clock" className="h-4 w-4" /> {t('notConfirmed')}</>}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600">
                          {medicine.name} · {medicine.dose}
                        </p>

                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {medicine.times.map((time) => (
                            <span key={time} className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-sm font-medium text-[#0C2451] ring-1 ring-blue-100">
                              <Icon name={TIME_ICONS[time]} className={`h-4 w-4 ${TIME_ICON_COLOURS[time]}`} /> {TIMES.find((item) => item.value === time)?.label[lang]}
                            </span>
                          ))}
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-sm font-medium text-slate-700">
                            <Icon name="utensils" className="h-4 w-4 text-slate-500" /> {FOOD_TEXT[medicine.food][lang]}
                          </span>
                          {left !== null && (
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium ${
                                left > 0 ? 'bg-slate-100 text-slate-700' : 'bg-red-50 text-red-800'
                              }`}
                            >
                              <Icon name="calendar" className="h-4 w-4 text-blue-600" /> {left > 0 ? `${left} ${t('daysLeft')}` : t('courseOver')}
                            </span>
                          )}
                        </div>

                        {(medicine.purpose || medicine.aliases.length > 0) && (
                          <p className="mt-2 text-sm text-slate-500">
                            {medicine.purpose && <>{t('purposeFor')}: {medicine.purpose}</>}
                            {medicine.purpose && medicine.aliases.length > 0 && ' · '}
                            {medicine.aliases.length > 0 && <>{t('alsoCalled')}: {medicine.aliases.join(', ')}</>}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                      {!medicine.confirmed && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleConfirm(medicine)}
                          className={primaryButton}
                        >
                          <Icon name="check" /> {t('checkConfirm')}
                        </button>
                      )}
                      <button type="button" onClick={() => handleEdit(medicine)} className={secondaryButton}>
                        {t('edit')}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleDelete(medicine)}
                        className="inline-flex min-h-12 items-center rounded-xl border border-red-200 bg-white px-4 text-base font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        {t('remove')}
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        {showForm && (
          <form ref={formRef} onSubmit={handleSubmitMedicine} className={`space-y-6 ${cardClass}`}>
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                {editingId === null ? t('addTitle') : `${t('editing')}: ${draft.name}`}
              </h2>
              {editingId !== null && (
                <p className="mt-1 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-200">
                  {t('editWarning')}
                </p>
              )}
            </div>

            <fieldset className="space-y-4">
              <StepTitle number={1} title={t('step1')} hint={t('step1Hint')} />
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="med-label">
                    {t('fieldLabel')}
                  </label>
                  <input
                    id="med-label"
                    required
                    value={draft.label}
                    onChange={(event) => setDraft({ ...draft, label: event.target.value })}
                    className={inputClass}
                    placeholder={medicines.length === 0 ? 'ಬಿಳಿ ಮಾತ್ರೆ' : 'ಹಳದಿ ಮಾತ್ರೆ'}
                  />
                </div>
                <div>
                  <label className={labelClass} htmlFor="med-color">
                    {t('fieldColour')}
                  </label>
                  <select
                    id="med-color"
                    required
                    value={draft.color_word}
                    onChange={(event) => setDraft({ ...draft, color_word: event.target.value })}
                    className={inputClass}
                  >
                    <option value="" disabled>
                      {t('chooseColour')}
                    </option>
                    {COLOURS.map((colour) => (
                      <option key={colour.value} value={colour.value}>
                        {colour.label[lang]}
                      </option>
                    ))}
                    {draft.color_word !== '' && !COLOURS.some((colour) => colour.value === draft.color_word) && (
                      <option value={draft.color_word}>{draft.color_word}</option>
                    )}
                  </select>
                </div>
                <div>
                  <label className={labelClass} htmlFor="med-name">
                    {t('fieldName')}
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
                    {t('fieldAliases')}
                  </label>
                  <input
                    id="med-aliases"
                    value={draft.aliases}
                    onChange={(event) => setDraft({ ...draft, aliases: event.target.value })}
                    className={inputClass}
                    placeholder={t('aliasesPlaceholder')}
                  />
                  <p className="mt-1 text-sm text-slate-500">{t('commas')}</p>
                </div>
              </div>
            </fieldset>

            <fieldset className="space-y-4 border-t border-slate-100 pt-5">
              <StepTitle number={2} title={t('step2')} hint={t('step2Hint')} />
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="med-dose">
                    {t('fieldDose')}
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
                  <span className={labelClass}>{t('fieldFood')}</span>
                  <div className="mt-1 grid grid-cols-3 gap-2" role="radiogroup" aria-label={t('fieldFood')}>
                    {FOODS.map((food) => (
                      <button
                        key={food.value}
                        type="button"
                        role="radio"
                        aria-checked={draft.food === food.value}
                        onClick={() => setDraft({ ...draft, food: food.value })}
                        className={`min-h-12 rounded-xl px-2 text-sm font-semibold ring-1 ${
                          draft.food === food.value
                            ? 'bg-[#0C2451] text-white ring-[#0C2451]'
                            : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        {FOOD_TEXT[food.value][lang]}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="sm:col-span-2">
                  <span className={labelClass}>{t('fieldWhen')}</span>
                  <div className="mt-1 grid grid-cols-3 gap-2">
                    {TIMES.map((time) => {
                      const on = draft.times.includes(time.value)
                      return (
                        <button
                          key={time.value}
                          type="button"
                          aria-pressed={on}
                          onClick={() => toggleTime(time.value)}
                          className={`inline-flex min-h-12 items-center justify-center gap-1.5 rounded-xl px-2 text-base font-semibold ring-1 ${
                            on ? 'bg-[#0C2451] text-white ring-[#0C2451]' : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50'
                          }`}
                        >
                          <Icon name={TIME_ICONS[time.value]} className={`h-5 w-5 ${on ? "text-white" : TIME_ICON_COLOURS[time.value]}`} /> {time.label[lang]}
                          {on && <span className="sr-only"> (selected)</span>}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            </fieldset>

            <fieldset className="space-y-4 border-t border-slate-100 pt-5">
              <StepTitle number={3} title={t('step3')} hint={t('step3Hint')} />
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="med-days">
                    {t('fieldDays')}
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
                    {t('fieldStart')}
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
                    {t('fieldPurpose')}
                  </label>
                  <input
                    id="med-purpose"
                    value={draft.purpose}
                    onChange={(event) => setDraft({ ...draft, purpose: event.target.value })}
                    className={inputClass}
                    placeholder="ಬಿಪಿ ಮಾತ್ರೆ"
                  />
                  <p className="mt-1 text-sm text-slate-500">{t('purposeHint')}</p>
                </div>
                <div>
                  <label className={labelClass} htmlFor="med-photo">
                    {t('fieldPhoto')}
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
            </fieldset>

            <div className="flex flex-wrap gap-3 border-t border-slate-100 pt-5">
              <button type="submit" disabled={busy} className={primaryButton}>
                {editingId === null ? t('saveMedicine') : t('saveChanges')}
              </button>
              {(editingId !== null || medicines.length > 0) && (
                <button type="button" onClick={handleCancelEdit} className={secondaryButton}>
                  {t('cancel')}
                </button>
              )}
            </div>
            <p className="text-sm text-slate-500">{t('newStartsUnconfirmed')}</p>
          </form>
        )}
      </div>
    </main>
  )
}
