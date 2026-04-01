# MediaTailor MVP

로컬 환경에서 `FFmpeg -> Nginx RTMP -> FFmpeg ABR -> Shaka Packager -> FastAPI SSAI` 흐름을 검증하기 위한 최소 프로젝트다.

## Components

- `ingest`: RTMP 수신과 HLS/DASH origin 파일 서빙
- `transcoder`: 단일 입력을 1080p/720p/480p MPEG-TS UDP로 변환
- `packager`: Shaka Packager로 live HLS + DASH 생성
- `ssai`: HLS manifest 프록시와 광고 구간 스티칭

## Quick Start

1. 데모 광고 asset 생성

```bash
bash scripts/generate-demo-ads.sh
```

2. SSAI 앱 테스트

```bash
python -m pytest
```

3. 전체 스택 실행

```bash
docker compose up --build
```

4. 테스트 영상 송출

```bash
ffmpeg -re -stream_loop -1 -i sample.mp4 \
  -c:v libx264 -preset veryfast -g 60 -keyint_min 60 \
  -c:a aac -b:a 128k -ar 48000 \
  -f flv rtmp://localhost:1935/live/stream
```

5. 세션 생성

```bash
curl http://localhost:8000/session
```

응답의 `master_url`을 플레이어에 넣으면 SSAI가 적용된 HLS master manifest를 받을 수 있다.

## Notes

- 기본 광고 삽입 위치는 `config/ad_breaks.yaml`에서 segment index 기준으로 제어한다.
- origin segment URL은 기본적으로 `http://localhost:8080`을 사용한다.
- CDN을 붙일 때는 `PUBLIC_ORIGIN_BASE_URL`을 CDN 도메인으로 바꿔야 한다.

