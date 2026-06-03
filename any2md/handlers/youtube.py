"""YouTube handler — yt-dlp extracts metadata + captions."""

import re
import shutil
from datetime import date

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_YT_RE = re.compile(r"^https?://(?:www\.)?(?:youtube\.com/(?:watch|shorts)|youtu\.be/)")


def _parse_vtt(vtt_text: str) -> str:
    """Strip VTT timestamps/headers → plain transcript text."""
    lines = []
    for line in vtt_text.splitlines():
        line = line.strip()
        if (
            not line
            or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE"))
            or "-->" in line
            or re.match(r"^\d+$", line)
        ):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)
    deduped: list[str] = []
    prev = None
    for line in lines:
        if line != prev:
            deduped.append(line)
        prev = line
    return "\n".join(deduped)


def _ydl_extract(url: str, ydl_opts: dict) -> dict:
    """Thin yt-dlp wrapper — isolated for mocking in tests."""
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _get_captions(info: dict) -> str:
    """Try to fetch English captions from VTT URL in yt-dlp info dict."""
    for caption_dict in (info.get("subtitles", {}), info.get("automatic_captions", {})):
        for lang in ("en", "en-US", "en-GB"):
            for fmt in caption_dict.get(lang, []):
                if fmt.get("ext") == "vtt" and fmt.get("url"):
                    try:
                        resp = httpx.get(fmt["url"], timeout=15)
                        resp.raise_for_status()
                        return _parse_vtt(resp.text)
                    except Exception:
                        continue
    return ""


def js_runtime_available() -> bool:
    """yt-dlp needs a JS runtime (deno/node) for reliable extraction on current YouTube."""
    return bool(shutil.which("deno") or shutil.which("node"))


class YouTubeHandler(Handler):
    source_type = "youtube"

    def matches(self, target: str) -> bool:
        return bool(_YT_RE.search(target))

    def extract(self, target: str) -> Document:
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        info = _ydl_extract(target, opts)

        title = info.get("title", "Untitled Video")
        channel = info.get("channel") or info.get("uploader", "")
        video_id = info.get("id", "")
        duration = info.get("duration")
        description = info.get("description", "")

        raw_date = info.get("upload_date", "")
        upload_date = None
        if raw_date and len(raw_date) == 8:
            upload_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"

        captions = _get_captions(info)
        body_markdown = captions or description or ""

        # No captions → Whisper audio transcription would be the fallback, but that needs ffmpeg
        # (which pipx can't install). Warn rather than silently leaving only the description.
        warnings: list[str] = []
        if not captions:
            if not js_runtime_available():
                warnings.append(
                    "youtube extraction is degraded without a JS runtime — install deno"
                )
            elif shutil.which("ffmpeg") is None:
                warnings.append("no captions found; install ffmpeg for audio transcription")

        return Document(
            title=title,
            source_url=target,
            source_type="youtube",
            upload_date=upload_date,
            extraction_date=date.today().isoformat(),
            body_markdown=body_markdown,
            warnings=warnings,
            metadata={
                k: v
                for k, v in {
                    "channel": channel,
                    "duration": duration,
                    "video_id": video_id,
                }.items()
                if v not in (None, "")
            },
        )
