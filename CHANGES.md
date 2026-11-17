# CHANGES

Built for the Gnani.ai Great Indian AI Internship Challenge (deadline extended from 10 Nov to 15 Nov 2026, 6 PM IST). Submitted on 15 Nov 2026; that version is tagged `submission-2026-11-15`.

## 2026-11-07
- Created repo with MIT license and Python .gitignore
- Added task spec for the coding agent

## 2026-11-08 to 2026-11-09
- T0: project setup and learning log
- T1: Gnani wrappers (Prisma speech-to-text, Timbre text-to-speech), first in mock mode, then real mode
- T2: database models and seed data

## 2026-11-10
- T3: caregiver setup
- T4: emergency detection (spoken Kannada, word pairs, fuzzy), intent rules, confirmed-only matching, Kannada answer templates, `/ask` pipeline with ask-back follow-ups, Prisma keyterms, audio format detection + WebM→WAV, caregiver log route, Kannada colour dropdown, Kannada seed data; 60 tests passing
- T5: elder page (Kannada and English, tap to call 108); T6: caregiver question log; fixed a false emergency on single words
- T7: batch test on real voice clips and general fixes (25/38 → 37/38, emergencies 8/8)
- 12 new clips, written and recorded after the fixes: 12/12, emergencies 2/2
- T8: Docker, health check, README; T9: keep-alive workflow
- Safety review: more emergency phrasings, missed-dose referral, always-visible 108 button
- UI: one language at a time, new colours, MedVoice icon

## 2026-11-14
- UI redesign: caregiver language toggle, line icons, day plan, step-by-step form
- A follow-up question right after an answer keeps the same tablet; answer audio stops when recording starts
- English answers, review fixes, README, pitch (`PITCH.md`), build specs in `docs/build/`
- "Which tablets today" is answered from confirmed tablets only

## 2026-11-15
- Demo tablets distinguished by colour; colour-based examples
- Fix: removing a tablet that has questions in the log
- A tablet's name alone gives a summary; "ಎಷ್ಟು ಸಾರಿ" (how many times) lists the times
- Follow-up memory set to 5 minutes
- Caregiver can rename the elder and upload tablet photos; every mentioned tablet's photo is shown
- README rewritten (problem first, results, architecture); demo video added
- Tests: 140, all pass
- Submitted
