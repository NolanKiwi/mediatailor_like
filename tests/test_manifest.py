import asyncio
import json

from app.main import create_session, demo_page
from app.manifest import parse_media_playlist, rewrite_master_playlist, stitch_media_playlist


MASTER = """#EXTM3U
#EXT-X-VERSION:7
#EXT-X-MEDIA:TYPE=AUDIO,URI="audio/index.m3u8",GROUP-ID="audio",NAME="ENGLISH"
#EXT-X-STREAM-INF:BANDWIDTH=2800000,RESOLUTION=1280x720
video_720p/index.m3u8
#EXT-X-I-FRAME-STREAM-INF:BANDWIDTH=120000,RESOLUTION=1280x720,URI="video_720p/iframes.m3u8"
"""


MEDIA = """#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:4
#EXT-X-MEDIA-SEQUENCE:6
#EXT-X-MAP:URI="init.mp4"
#EXTINF:4.000,
segment_6.m4s
#EXTINF:4.000,
segment_7.m4s
#EXT-X-ENDLIST
"""


AD = """#EXTM3U
#EXT-X-TARGETDURATION:4
#EXTINF:4.000,
ad_000.ts
#EXTINF:4.000,
ad_001.ts
#EXT-X-ENDLIST
"""


def test_parse_media_playlist():
    playlist = parse_media_playlist(MEDIA)
    assert playlist.media_sequence == 6
    assert len(playlist.segments) == 2
    assert playlist.segments[0].uri == "segment_6.m4s"


def test_rewrite_master_playlist():
    output = rewrite_master_playlist(MASTER, "abc123")
    assert "/ssai/media.m3u8?session=abc123&variant=video_720p%2Findex.m3u8" in output
    assert 'URI="/ssai/media.m3u8?session=abc123&variant=audio%2Findex.m3u8"' in output
    assert 'URI="/ssai/media.m3u8?session=abc123&variant=video_720p%2Fiframes.m3u8"' in output


def test_stitch_media_playlist(tmp_path):
    ads_dir = tmp_path / "ads"
    ads_dir.mkdir()
    (ads_dir / "demo_ad.m3u8").write_text(AD, encoding="utf-8")

    output = stitch_media_playlist(
        MEDIA,
        variant="video_720p/index.m3u8",
        public_origin_base_url="http://localhost:8080",
        ad_breaks=[{"id": "break-1", "after_segments": 6, "asset_playlist": "demo_ad.m3u8"}],
        ads_dir=ads_dir,
    )

    assert "#EXT-X-CUE-OUT:DURATION=8.000" in output
    assert "http://localhost:8080/ads/ad_000.ts" in output
    assert "http://localhost:8080/live/video_720p/segment_6.m4s" in output
    assert '#EXT-X-MAP:URI="http://localhost:8080/live/video_720p/init.mp4"' in output


def test_audio_playlist_keeps_origin_segments_without_ad_insertion(tmp_path):
    ads_dir = tmp_path / "ads"
    ads_dir.mkdir()
    (ads_dir / "demo_ad.m3u8").write_text(AD, encoding="utf-8")

    output = stitch_media_playlist(
        MEDIA,
        variant="audio/index.m3u8",
        public_origin_base_url="http://localhost:8080",
        ad_breaks=[{"id": "break-1", "after_segments": 6, "asset_playlist": "demo_ad.m3u8"}],
        ads_dir=ads_dir,
    )

    assert "#EXT-X-CUE-OUT" not in output
    assert '#EXT-X-MAP:URI="http://localhost:8080/live/audio/init.mp4"' in output
    assert "http://localhost:8080/live/audio/segment_6.m4s" in output


def test_demo_page_served():
    response = asyncio.run(demo_page())

    assert response.status_code == 200
    assert "SSAI Debug Console" in response.body.decode("utf-8")


def test_session_response_contains_master_url():
    response = asyncio.run(create_session())
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert payload["master_url"].startswith("/ssai/master.m3u8?session=")
    assert isinstance(payload["breaks"], list)
