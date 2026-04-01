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
bash scripts/push-loop-source.sh
```

기본값은 루트의 `testclip.mp4`를 무한 반복 송출하고, 화면 좌측 상단에 현재 시각을 오버레이한다.
다른 입력 파일이나 RTMP URL을 쓰려면 환경변수로 지정하면 된다.

```bash
INPUT_FILE=/path/to/clip.mp4 RTMP_URL=rtmp://46.250.255.39:1935/live/stream bash scripts/push-loop-source.sh
```

5. 세션 생성

```bash
curl http://localhost:8000/session
```

응답의 `master_url`을 플레이어에 넣으면 SSAI가 적용된 HLS master manifest를 받을 수 있다.

6. 데모 플레이어 열기

브라우저에서 `http://localhost:8000/demo`를 열면 stitched manifest 기반 HLS 재생과 광고 구간 타임라인을 함께 볼 수 있다.
페이지는 다음을 한 화면에서 보여준다.

- SSAI 세션 생성
- HLS master/media manifest 분석
- 광고 break와 cue 태그 시각화
- 실제 stitched stream 재생

## External Access

외부 브라우저에서 접속할 때는 stitched media playlist 안의 origin URL이 `localhost`가 아니어야 한다.
이 프로젝트는 `docker-compose.yml`의 `PUBLIC_ORIGIN_BASE_URL` 값을 사용한다.

예시:

```bash
export PUBLIC_ORIGIN_BASE_URL=http://46.250.255.39:8080
docker compose up -d --build ssai
```

그 다음 외부에서 아래 주소로 접속하면 된다.

- 플레이어: `http://46.250.255.39:8000/demo`
- 세션 API: `http://46.250.255.39:8000/session`
- origin HLS: `http://46.250.255.39:8080/live/master.m3u8`

주의:

- 서버 보안그룹이나 방화벽에서 `8000/tcp`, `8080/tcp`를 열어야 한다.
- `PUBLIC_ORIGIN_BASE_URL`만 바뀐 경우 `ssai` 컨테이너만 재생성하면 된다.
- `ingest`는 이미 `0.0.0.0:8080`으로 publish 되어 있으므로 보통 재시작이 필요 없다.

## Notes

- 기본 광고 삽입 위치는 `config/ad_breaks.yaml`에서 segment index 기준으로 제어한다.
- origin segment URL은 기본적으로 `http://localhost:8080`을 사용한다.
- CDN을 붙일 때는 `PUBLIC_ORIGIN_BASE_URL`을 CDN 도메인으로 바꿔야 한다.
