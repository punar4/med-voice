#!/usr/bin/env bash
# Convert every audio file in a folder to 8 kHz mono WAV (phone-call quality).
#
#   scripts/to_8khz.sh test_audio test_audio_8khz
#
# Needs ffmpeg on PATH. Non-audio files (e.g. expected.csv) are skipped.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <input-folder> <output-folder>" >&2
  exit 2
fi

in_dir=$1
out_dir=$2

if [ ! -d "$in_dir" ]; then
  echo "not a folder: $in_dir" >&2
  exit 2
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is not installed (Windows: winget install ffmpeg)" >&2
  exit 2
fi

mkdir -p "$out_dir"

converted=0
skipped=0
shopt -s nullglob
for file in "$in_dir"/*; do
  [ -f "$file" ] || continue
  case "${file,,}" in
    *.wav | *.mp3 | *.m4a | *.aac | *.ogg | *.flac | *.webm) ;;
    *)
      skipped=$((skipped + 1))
      continue
      ;;
  esac

  name=$(basename "$file")
  ffmpeg -hide_banner -loglevel error -y -i "$file" \
    -ac 1 -ar 8000 -c:a pcm_s16le "$out_dir/${name%.*}.wav"
  converted=$((converted + 1))
done

if [ "$converted" -eq 0 ]; then
  echo "no audio files found in $in_dir" >&2
  exit 1
fi

echo "converted $converted file(s) to $out_dir (8 kHz mono WAV), skipped $skipped"
