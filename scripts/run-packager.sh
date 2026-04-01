#!/usr/bin/env sh
set -eu

mkdir -p /var/www/origin/live/audio /var/www/origin/live/video_720p /var/www/origin/live/video_480p

exec packager \
  'in=udp://0.0.0.0:5001?reuse=1,stream=video,init_segment=/var/www/origin/live/video_720p/init.mp4,segment_template=/var/www/origin/live/video_720p/segment_$Number$.m4s,playlist_name=/var/www/origin/live/video_720p/index.m3u8,iframe_playlist_name=/var/www/origin/live/video_720p/iframes.m3u8' \
  'in=udp://0.0.0.0:5001?reuse=1,stream=audio,init_segment=/var/www/origin/live/audio/init.mp4,segment_template=/var/www/origin/live/audio/segment_$Number$.m4s,playlist_name=/var/www/origin/live/audio/index.m3u8,hls_group_id=audio,hls_name=ENGLISH' \
  'in=udp://0.0.0.0:5002?reuse=1,stream=video,init_segment=/var/www/origin/live/video_480p/init.mp4,segment_template=/var/www/origin/live/video_480p/segment_$Number$.m4s,playlist_name=/var/www/origin/live/video_480p/index.m3u8,iframe_playlist_name=/var/www/origin/live/video_480p/iframes.m3u8' \
  --hls_master_playlist_output /var/www/origin/live/master.m3u8 \
  --mpd_output /var/www/origin/live/manifest.mpd \
  --hls_playlist_type LIVE \
  --segment_duration 4 \
  --time_shift_buffer_depth 120 \
  --preserved_segments_outside_live_window 20 \
  --minimum_update_period 8
