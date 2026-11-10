"""Run a folder of recorded clips through `/ask` and score them (T7).

Start the server in real mode from `backend/` first:

    uvicorn app.main:app --reload

(The server reads GNANI_API_KEY / GNANI_BASE_URL from the repo-root `.env`.
This script never reads, needs or prints the key itself; it only warns if the
environment says the server would answer in mock mode.)

Then, from the repo root:

    ../venv/Scripts/python.exe scripts/batch_test.py --profile-id 1

It reads `test_audio/expected.csv` (`file,say,expected,tablet,note`), posts every
clip to `POST /api/elder/{token}/ask`, and writes `test_audio/results.csv` with
the transcript, the outcome, the matched tablet and a pass/fail column, then
prints an accuracy summary.

Isolation: the pipeline treats a question within two minutes of the profile's
last one as a follow-up, so each clip is asked on its own throwaway profile that
copies the source profile's confirmed medicines. That copy is what keeps one
clip from changing the answer to the next. The throwaway profiles stay in the
database (there is no delete-profile route); they are named `Batch <file>`.
"""

import argparse
import csv
import mimetypes
import sys
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_COLUMNS = ("file", "say", "expected", "tablet")
RESULT_COLUMNS = (
    "file",
    "say",
    "expected",
    "tablet_expected",
    "transcript",
    "outcome",
    "tablet_found",
    "pass",
    "error",
    "note",
)

# MedicineInput in main.py accepts exactly these fields from a profile's medicine.
MEDICINE_FIELDS = (
    "name",
    "aliases",
    "label",
    "color_word",
    "photo_path",
    "dose",
    "times",
    "food",
    "days_total",
    "start_date",
    "purpose",
)


def utf8_console() -> None:
    """Let Windows consoles print Kannada labels instead of crashing on cp1252."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def read_expected(path: Path) -> list[dict]:
    """Read the expected-results CSV. utf-8-sig drops the BOM Excel writes."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"{path} has no rows")
    missing = [column for column in EXPECTED_COLUMNS if column not in rows[0]]
    if missing:
        raise SystemExit(f"{path} is missing column(s): {', '.join(missing)}")
    return rows


def accepted_outcomes(expected: str, note: str) -> set[str]:
    """Outcomes that count as right for this clip.

    A few clips are marked "referral is also right if ..." because the seeded
    prescription leaves that field empty; refusing to answer is then correct.
    """
    allowed = {expected.strip()}
    if "referral is also right" in (note or "").lower():
        allowed.add("referral")
    return allowed


def check_mock_mode(allow_mock: bool) -> None:
    """Warn/stop when this machine's .env would make results meaningless."""
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from app import config
    except ImportError as exc:  # the venv that runs the server also runs this
        raise SystemExit(f"could not import backend config: {exc}") from None

    print(f"GNANI_API_KEY: {'set (not shown)' if config.GNANI_API_KEY else 'MISSING'}")
    print(f"MOCK_GNANI: {config.MOCK_GNANI}")
    if not config.MOCK_GNANI:
        return
    print(
        "MOCK_GNANI=true, so /ask would return the fixed mock transcript and these "
        "results would be meaningless. Set MOCK_GNANI=false in .env (and restart "
        "the server), or pass --allow-mock to test the script itself.",
        file=sys.stderr,
    )
    if not allow_mock:
        raise SystemExit(2)


def fetch_source_medicines(client: httpx.Client, base_url: str, profile_id: int) -> list[dict]:
    """Confirmed medicines of the seeded profile, ready to copy into a scratch profile."""
    response = client.get(f"{base_url}/api/profiles/{profile_id}")
    if response.status_code == 404:
        raise SystemExit(
            f"no profile {profile_id} on the server. Run `python seed.py` in backend/ "
            "and use the id it prints."
        )
    response.raise_for_status()
    medicines = [
        {field: medicine.get(field) for field in MEDICINE_FIELDS}
        for medicine in response.json()["medicines"]
        if medicine.get("confirmed")
    ]
    if not medicines:
        raise SystemExit(f"profile {profile_id} has no confirmed medicines to test against")
    return medicines


def scratch_profile(client: httpx.Client, base_url: str, name: str, medicines: list[dict]) -> str:
    """Copy the medicines onto a fresh profile and return its elder token."""
    created = client.post(f"{base_url}/api/profiles", json={"elder_name": name, "language": "kn"})
    created.raise_for_status()
    profile = created.json()

    for medicine in medicines:
        added = client.post(f"{base_url}/api/profiles/{profile['id']}/medicines", json=medicine)
        added.raise_for_status()
        confirmed = client.post(f"{base_url}/api/medicines/{added.json()['id']}/confirm")
        confirmed.raise_for_status()

    return profile["share_token"]


def ask(client: httpx.Client, base_url: str, token: str, clip: Path) -> dict:
    """Post one clip to /ask and return the JSON answer."""
    content_type = mimetypes.guess_type(clip.name)[0] or "application/octet-stream"
    with clip.open("rb") as handle:
        response = client.post(
            f"{base_url}/api/elder/{token}/ask",
            files={"audio": (clip.name, handle, content_type)},
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile-id", type=int, required=True,
                        help="id of the seeded profile whose confirmed medicines to test against")
    parser.add_argument("--expected", type=Path, default=ROOT / "test_audio" / "expected.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "test_audio" / "results.csv")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, help="only the first N clips (quick check)")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="seconds per clip (speech-to-text plus text-to-speech)")
    parser.add_argument("--allow-mock", action="store_true",
                        help="run even if MOCK_GNANI=true (plumbing test only)")
    args = parser.parse_args()

    utf8_console()
    expected_path = args.expected.resolve()
    audio_dir = expected_path.parent
    base_url = args.base_url.rstrip("/")

    check_mock_mode(args.allow_mock)

    rows = read_expected(expected_path)
    if args.limit:
        rows = rows[: args.limit]
    for row in rows:
        clip = audio_dir / row["file"]
        if not clip.suffix:
            clip = clip.with_suffix(".m4a")
        row["_clip"] = clip
        if not clip.is_file():
            raise SystemExit(f"missing clip: {clip}")

    results: list[dict] = []
    with httpx.Client(timeout=args.timeout) as client:
        try:
            health = client.get(f"{base_url}/api/health")
        except httpx.HTTPError as exc:
            raise SystemExit(
                f"cannot reach {base_url} ({type(exc).__name__}). Start the server in "
                "backend/ with `uvicorn app.main:app --reload`."
            ) from None
        if health.status_code != 200:
            raise SystemExit(
                f"{base_url}/api/health returned {health.status_code}. Start the server in "
                "backend/ with `uvicorn app.main:app --reload`."
            )
        try:
            medicines = fetch_source_medicines(client, base_url, args.profile_id)
        except httpx.HTTPError as exc:
            raise SystemExit(f"could not read profile {args.profile_id}: {exc}") from None
        print(f"Testing {len(rows)} clip(s) against {len(medicines)} confirmed medicine(s).\n")

        for index, row in enumerate(rows, start=1):
            expected = row["expected"].strip()
            expected_tablet = (row.get("tablet") or "").strip()
            result = {
                "file": row["file"],
                "say": row.get("say", ""),
                "expected": expected,
                "tablet_expected": expected_tablet,
                "transcript": "",
                "outcome": "",
                "tablet_found": "",
                "pass": "no",
                "error": "",
                "note": row.get("note", ""),
            }
            try:
                token = scratch_profile(client, base_url, f"Batch {row['file']}", medicines)
                answer = ask(client, base_url, token, row["_clip"])
                result["transcript"] = answer.get("transcript") or ""
                result["outcome"] = answer.get("outcome") or ""
                result["tablet_found"] = (answer.get("medicine") or {}).get("label") or ""
                right_outcome = result["outcome"] in accepted_outcomes(expected, row.get("note", ""))
                right_tablet = not expected_tablet or result["tablet_found"] == expected_tablet
                result["pass"] = "yes" if right_outcome and right_tablet else "no"
            except httpx.HTTPError as exc:
                # Keep going: one bad clip must not throw away the whole batch.
                result["error"] = f"{type(exc).__name__}: {exc}"[:200]

            results.append(result)
            print(f"[{index}/{len(rows)}] {result['file']}: "
                  f"expected {expected or '?'}, got {result['outcome'] or 'error'} "
                  f"-> {'PASS' if result['pass'] == 'yes' else 'FAIL'}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)

    print_summary(results, args.out)
    return 0


def print_summary(results: list[dict], out_path: Path) -> None:
    total = len(results)
    passed = sum(1 for result in results if result["pass"] == "yes")
    emergency_rows = [result for result in results if result["expected"] == "emergency"]
    emergency_hits = sum(1 for result in emergency_rows if result["outcome"] == "emergency")
    outcomes = Counter(result["outcome"] or "error" for result in results)

    print(f"\nResults written to {out_path}")
    print(f"Overall pass: {passed}/{total} ({(100 * passed / total) if total else 0:.1f}%)")
    if emergency_rows:
        share = 100 * emergency_hits / len(emergency_rows)
        print(f"Emergency recall: {emergency_hits}/{len(emergency_rows)} ({share:.1f}%)")
    print("Outcomes seen: " + ", ".join(f"{name}={count}" for name, count in outcomes.most_common()))

    failed = [result for result in results if result["pass"] != "yes"]
    if failed:
        print("Failures:")
        for result in failed:
            got = result["outcome"] or result["error"] or "no answer"
            tablet = f", tablet {result['tablet_found']}" if result["tablet_found"] else ""
            print(f"  {result['file']}: expected {result['expected']}, got {got}{tablet}")


if __name__ == "__main__":
    raise SystemExit(main())
