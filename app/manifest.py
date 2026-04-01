from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urljoin


@dataclass
class HlsSegment:
    duration: float
    uri: str
    title: str = ""


@dataclass
class MediaPlaylist:
    header_lines: list[str]
    segments: list[HlsSegment]
    footer_lines: list[str]
    media_sequence: int = 0
    target_duration: int = 4


def parse_media_playlist(content: str) -> MediaPlaylist:
    header_lines: list[str] = []
    footer_lines: list[str] = []
    segments: list[HlsSegment] = []
    media_sequence = 0
    target_duration = 4
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    current_extinf: tuple[float, str] | None = None
    seen_segment = False

    for line in lines:
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            media_sequence = int(line.split(":", 1)[1])
        if line.startswith("#EXT-X-TARGETDURATION:"):
            target_duration = int(float(line.split(":", 1)[1]))

        if line.startswith("#EXTINF:"):
            duration_part = line.split(":", 1)[1]
            duration_text, _, title = duration_part.partition(",")
            current_extinf = (float(duration_text), title)
            continue

        if current_extinf and not line.startswith("#"):
            duration, title = current_extinf
            segments.append(HlsSegment(duration=duration, uri=line, title=title))
            current_extinf = None
            seen_segment = True
            continue

        if not seen_segment:
            header_lines.append(line)
        else:
            footer_lines.append(line)

    return MediaPlaylist(
        header_lines=header_lines,
        segments=segments,
        footer_lines=footer_lines,
        media_sequence=media_sequence,
        target_duration=target_duration,
    )


def load_ad_segments(ads_dir: str | Path, asset_playlist: str, public_base_url: str) -> list[HlsSegment]:
    playlist_path = Path(ads_dir) / asset_playlist
    content = playlist_path.read_text(encoding="utf-8")
    playlist = parse_media_playlist(content)
    base_url = public_base_url.rstrip("/") + "/ads/"
    return [
        HlsSegment(duration=segment.duration, uri=urljoin(base_url, segment.uri), title=segment.title)
        for segment in playlist.segments
    ]


def _build_ssai_variant_uri(session_id: str, variant: str) -> str:
    return f"/ssai/media.m3u8?session={quote(session_id)}&variant={quote(variant, safe='')}"


def rewrite_tag_uri(line: str, base_url: str) -> str:
    if 'URI="' not in line:
        return line
    prefix, remainder = line.split('URI="', 1)
    original_uri, suffix = remainder.split('"', 1)
    return f'{prefix}URI="{urljoin(base_url, original_uri)}"{suffix}'


def rewrite_master_playlist(content: str, session_id: str) -> str:
    rewritten: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-MEDIA:") and 'URI="' in line:
            prefix, remainder = line.split('URI="', 1)
            original_uri, suffix = remainder.split('"', 1)
            rewritten.append(f'{prefix}URI="{_build_ssai_variant_uri(session_id, original_uri)}"{suffix}')
            continue
        if line.startswith("#EXT-X-I-FRAME-STREAM-INF:") and 'URI="' in line:
            prefix, remainder = line.split('URI="', 1)
            original_uri, suffix = remainder.split('"', 1)
            rewritten.append(f'{prefix}URI="{_build_ssai_variant_uri(session_id, original_uri)}"{suffix}')
            continue
        if line.startswith("#"):
            rewritten.append(line)
            continue
        rewritten.append(_build_ssai_variant_uri(session_id, line))
    return "\n".join(rewritten) + "\n"


def stitch_media_playlist(
    content: str,
    *,
    variant: str,
    public_origin_base_url: str,
    ad_breaks: Iterable[dict],
    ads_dir: str | Path,
) -> str:
    playlist = parse_media_playlist(content)
    variant_base = f"{public_origin_base_url.rstrip('/')}/live/{variant.rsplit('/', 1)[0].strip('/')}/"
    if variant.count("/") == 0:
        variant_base = f"{public_origin_base_url.rstrip('/')}/live/"
    lines = [rewrite_tag_uri(line, variant_base) for line in playlist.header_lines]

    scheduled_breaks = {int(item["after_segments"]): item for item in ad_breaks}
    is_audio_variant = variant.startswith("audio/")

    for offset, segment in enumerate(playlist.segments):
        absolute_index = playlist.media_sequence + offset
        if not is_audio_variant and absolute_index in scheduled_breaks:
            ad_break = scheduled_breaks[absolute_index]
            ad_segments = load_ad_segments(
                ads_dir=ads_dir,
                asset_playlist=ad_break["asset_playlist"],
                public_base_url=public_origin_base_url,
            )
            total_ad_duration = sum(item.duration for item in ad_segments)
            lines.append("#EXT-X-DISCONTINUITY")
            lines.append(
                f'#EXT-X-DATERANGE:ID="{ad_break["id"]}",CLASS="ad",START-DATE="1970-01-01T00:00:00Z",DURATION={total_ad_duration:.3f}'
            )
            lines.append(f"#EXT-X-CUE-OUT:DURATION={total_ad_duration:.3f}")
            for ad_segment in ad_segments:
                lines.append(f"#EXTINF:{ad_segment.duration:.3f},{ad_segment.title}")
                lines.append(ad_segment.uri)
            lines.append("#EXT-X-CUE-IN")
            lines.append("#EXT-X-DISCONTINUITY")

        lines.append(f"#EXTINF:{segment.duration:.3f},{segment.title}")
        lines.append(urljoin(variant_base, segment.uri))

    lines.extend(rewrite_tag_uri(line, variant_base) for line in playlist.footer_lines)
    return "\n".join(lines) + "\n"
