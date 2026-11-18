import os, asyncio, uuid
from pathlib import Path

COOKIES = os.getenv("COOKIES_FILE", "/data/cookies.txt")
MAX_MB = int(os.getenv("MAX_FILE_MB", "2000"))

def cookie_args():
    p = Path(COOKIES)
    return ["--cookies", str(p)] if p.exists() and p.stat().st_size else []

async def run_ytdlp(args, context=None):
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    if context is not None:
        context.user_data["process"] = proc
    output = []
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        s = line.decode("utf-8", "replace").strip()
        if s:
            output.append(s)
    code = await proc.wait()
    if code != 0:
        raise RuntimeError("\n".join(output[-12:]) or f"yt-dlp exit code {code}")
    return output

async def get_info(url):
    args = ["yt-dlp", "--dump-single-json", "--no-warnings", "--no-playlist"] + cookie_args() + [url]
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    if proc.returncode:
        raise RuntimeError(err.decode("utf-8", "replace")[-700:])
    import json
    return json.loads(out)

async def download_video(url, height, folder, context):
    name = f"{uuid.uuid4().hex}.%(ext)s"
    template = str(folder / name)
    args = [
        "yt-dlp", "--no-playlist", "--no-warnings", "--newline",
        "-f", f"bv*[height<={height}]+ba/b[height<={height}]",
        "--merge-output-format", "mp4",
        "--max-filesize", f"{MAX_MB}M",
        "-o", template
    ] + cookie_args() + [url]
    await run_ytdlp(args, context)
    return newest_file(folder)

async def download_audio(url, fmt, folder, context):
    name = f"{uuid.uuid4().hex}.%(ext)s"
    template = str(folder / name)
    args = [
        "yt-dlp", "--no-playlist", "--no-warnings",
        "-f", "bestaudio/best",
        "-x", "--audio-format", "mp3" if fmt == "mp3" else "m4a",
        "--audio-quality", "192K",
        "-o", template
    ] + cookie_args() + [url]
    await run_ytdlp(args, context)
    return newest_file(folder)

def newest_file(folder):
    files = sorted(Path(folder).glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise RuntimeError("Downloaded file not found")
    return str(files[0])

def clean_file(path):
    try: Path(path).unlink(missing_ok=True)
    except Exception: pass
