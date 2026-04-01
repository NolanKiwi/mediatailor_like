#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_FILE="${INPUT_FILE:-${ROOT_DIR}/testclip.mp4}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1:1935/live/stream}"
LOG_PREFIX="${LOG_PREFIX:-ingest_ffmpeg}"
ROTATE_SIZE="${ROTATE_SIZE:-200M}"
FONT_FILE="${FONT_FILE:-/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf}"

exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3

if [[ ! -f "${INPUT_FILE}" ]]; then
  echo "input file not found: ${INPUT_FILE}" >&2
  exit 1
fi

if command -v rotatelogs >/dev/null 2>&1; then
  exec > >(rotatelogs "${LOG_PREFIX}-%Y%m%d-%H%M%S.log" "${ROTATE_SIZE}" 2>&1 | gzip -f) 2>&1
else
  exec >> "${LOG_PREFIX}.log" 2>&1
fi

echo "[$(date -Is)] starting RTMP loop push"
echo "[$(date -Is)] input=${INPUT_FILE}"
echo "[$(date -Is)] target=${RTMP_URL}"

drawtext_filter="drawtext=text='%{localtime}':x=24:y=18:fontsize=42:fontcolor=black:box=1:boxcolor=white@0.92:boxborderw=16"

if [[ -f "${FONT_FILE}" ]]; then
  drawtext_filter="drawtext=fontfile=${FONT_FILE}:text='%{localtime}':x=24:y=18:fontsize=42:fontcolor=black:box=1:boxcolor=white@0.92:boxborderw=16"
fi

exec ffmpeg \
  -hide_banner \
  -loglevel info \
  -re \
  -stream_loop -1 \
  -i "${INPUT_FILE}" \
  -vf "drawbox=x=0:y=0:w=1180:h=84:color=white@0.92:t=fill,${drawtext_filter}" \
  -pix_fmt yuv420p \
  -c:v libx264 \
  -preset veryfast \
  -g 60 \
  -keyint_min 60 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 128k \
  -ar 48000 \
  -ac 2 \
  -f flv \
  "${RTMP_URL}"
