#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-./volumes/origin/ads}"
mkdir -p "${OUTPUT_DIR}"

ffmpeg -y \
  -f lavfi -i color=c=blue:s=1280x720:d=8 \
  -f lavfi -i sine=frequency=880:sample_rate=48000:d=8 \
  -vf "drawtext=text='Demo Ad Break':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -preset veryfast -g 48 -sc_threshold 0 \
  -c:a aac -b:a 128k \
  -f hls \
  -hls_time 4 \
  -hls_playlist_type vod \
  -hls_segment_filename "${OUTPUT_DIR}/segment_%03d.ts" \
  "${OUTPUT_DIR}/demo_ad.m3u8"

