#!/usr/bin/env bash
set -euo pipefail

INPUT_URL="${INPUT_URL:-rtmp://ingest:1935/live/stream}"
GOP_SECONDS="${GOP_SECONDS:-2}"
FPS="${FPS:-30}"
GOP_SIZE="$((GOP_SECONDS * FPS))"

mkdir -p /tmp/mediatailor

while true; do
  ffmpeg -y -loglevel info -rw_timeout 10000000 -i "${INPUT_URL}" \
    -filter_complex "[0:v]split=3[v1][v2][v3];[v1]scale=w=1920:h=1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v1080];[v2]scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2[v720];[v3]scale=w=854:h=480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2[v480]" \
    -map "[v1080]" -map 0:a? -c:v libx264 -preset veryfast -tune zerolatency -profile:v high -b:v 5000k -maxrate:v 5350k -bufsize:v 7500k -g "${GOP_SIZE}" -keyint_min "${GOP_SIZE}" -sc_threshold 0 -c:a aac -b:a 128k -ar 48000 -ac 2 -f mpegts "udp://packager:5000?pkt_size=1316" \
    -map "[v720]" -map 0:a? -c:v libx264 -preset veryfast -tune zerolatency -profile:v high -b:v 2800k -maxrate:v 2996k -bufsize:v 4200k -g "${GOP_SIZE}" -keyint_min "${GOP_SIZE}" -sc_threshold 0 -c:a aac -b:a 128k -ar 48000 -ac 2 -f mpegts "udp://packager:5001?pkt_size=1316" \
    -map "[v480]" -map 0:a? -c:v libx264 -preset veryfast -tune zerolatency -profile:v main -b:v 1400k -maxrate:v 1498k -bufsize:v 2100k -g "${GOP_SIZE}" -keyint_min "${GOP_SIZE}" -sc_threshold 0 -c:a aac -b:a 96k -ar 48000 -ac 2 -f mpegts "udp://packager:5002?pkt_size=1316"
  sleep 2
done
