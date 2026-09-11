import os
import asyncio
import tempfile
import structlog
import yt_dlp

logger = structlog.get_logger()

class YtDlpService:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    async def download(self, url: str) -> dict:
        info = {"title": "", "description": "", "file_path": None, "file_size": 0, "is_too_big": False}

        ydl_opts = {
            "outtmpl": os.path.join(self.temp_dir, "%(id)s.%(ext)s"),
            "format": "best[filesize<50M]/best",
            "quiet": True,
            "no_warnings": True,
        }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(url, download=False)
                info["title"] = meta.get("title", "")
                info["description"] = meta.get("description", "")

                filesize = meta.get("filesize") or meta.get("filesize_approx", 0)
                if filesize and filesize > 50 * 1024 * 1024:
                    info["is_too_big"] = True
                    info["file_size"] = filesize
                    logger.info("File too big for Telegram", url=url, size=filesize)
                    return info

                ydl.download([url])
                filename = ydl.prepare_filename(meta)
                info["file_path"] = filename
                if os.path.exists(filename):
                    info["file_size"] = os.path.getsize(filename)
            return info

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error("yt-dlp error", url=url, error=str(e))
            info["error"] = str(e)
            return info
