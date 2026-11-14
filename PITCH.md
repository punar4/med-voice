# MedVoice: medicine questions, answered in spoken Kannada

**Solo entry, Gnani.ai Great Indian AI Internship Challenge** · Punarnava Viswanath, BMS College of Engineering, Bengaluru
**Code:** https://github.com/punar4/med-voice · **Demo video:** <VIDEO_LINK>

**Try it:** [Elder page](https://med-voice-afia.onrender.com/elder/FJ8uBWhh2cVQ5CTUUyPK2Q) (press and ask in Kannada) · [Caregiver page](https://med-voice-afia.onrender.com/) · [Question log](https://med-voice-afia.onrender.com/log/1)

## Problem
Many elders in India take four or five tablets a day but can't read their prescription, which is in English and handwritten. They ask questions like "Is the big white one before food?", "How many days more?" or "Why am I taking this?" in Kannada, often when no one is home. A wrong guess can mean a missed or doubled dose.

## Solution
A phone web page with **one big button**. The elder asks in spoken Kannada (or Kanglish) and hears the answer in Kannada.
- **Caregiver** adds each tablet once (how the elder describes it, dose, times, food, course length) and **confirms** it. They share a private link and see a log of every question.
- **Elder** just presses and speaks. No reading, no typing, no menus.

## How it works
Speech → **Gnani Prisma** (`prisma-v3.0`, kn-IN, code-mix, with the elder's medicine words as keyterms) → emergency check → question type → match to a *confirmed* tablet → fixed Kannada sentence filled with the caregiver's details → **Gnani Timbre** (`timbre-v2.5`, voice Saanvi) speaks it.

## Why it is safe
- **No AI-written medical advice.** Every answer is a fixed template filled with confirmed prescription data.
- **Emergency first.** "ಎದೆ ನೋವು", "ಉಸಿರು ಕಟ್ತಾ ಇದೆ", a fall or stroke signs bring up a red screen with a one-tap **108** call. A 108 button is always visible too.
- **Never guesses.** If two tablets match, it asks "which one?". An unconfirmed tablet, an unknown colour, a dose change, or a missed or doubled dose gets "ask your doctor".
- **Natural follow-ups.** "ಎಷ್ಟು ತಗೋಬೇಕು?" right after an answer stays on the same tablet, and every answer names the tablet.

## Results (real voice, via Gnani Prisma)
| Test | Score |
|---|---|
| First run on 38 clips, before any fixes | 25/38 |
| After fixing the general bugs it found | 37/38 (only miss: a whispered clip, which got a safe "please ask again") |
| **12 unseen clips, recorded after the fixes** | **12/12**, emergencies 2/2 |

All 10 emergency clips were caught, and there are 121 automated tests. Limit: one speaker so far.

## Users and impact
Elders who speak Kannada and live alone or with working children, and the caregivers who manage their medicines. It works on any phone with a browser: no app install and no literacy needed.

## Next
Phone-call access for feature phones, more Indian languages, more voices in testing, and compliance with India's DPDP Act (consent, data kept in India, deletion on request).

*Built with Claude (design, safety rules, review) and Freebuff (bulk coding). Build specs are in `docs/build/`.*
