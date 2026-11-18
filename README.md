# YouTube Telegram Downloader — Railway (single-service local Bot API)

This deployment runs the downloader and the official Telegram Bot API server in **one container**. That is important: local Bot API mode uploads by local file path, so the API server must see the same filesystem as the downloader.

## Deploy
1. Push this project to a private GitHub repository. Keep `cookies.txt`, `.env`, and tokens out of Git.
2. Railway: New Project → Deploy from GitHub Repo → choose this repository.
3. Railway detects the root `Dockerfile`. It compiles the official Telegram Bot API server from upstream source during image build; the first build can take several minutes.
4. Add a Railway Volume to this same service, mount it at `/data`. Use a paid plan/volume large enough for the download, merged output, API data, and headroom. For a 2 GB file, 10 GB is a safer starting point than 2 GB.
5. Add Variables:
   - `BOT_TOKEN` = BotFather token
   - `TELEGRAM_API_ID` = API ID from https://my.telegram.org
   - `TELEGRAM_API_HASH` = API hash from https://my.telegram.org
   - `ADMIN_IDS` = your numeric Telegram user ID (optional)
   - `DATA_DIR` = `/data`
   - `COOKIES_FILE` = `/data/cookies.txt`
   - `MAX_FILE_MB` = `2000`
   - `TELEGRAM_API_BASE_URL` = `http://127.0.0.1:8081/bot`
   - `TELEGRAM_FILE_BASE_URL` = `http://127.0.0.1:8081/file/bot`
6. Upload your Netscape-format cookies file to `/data/cookies.txt` on the mounted Railway Volume. Use Railway CLI volume file upload/browse. Do not commit it to GitHub or bake it into the image.
7. Before first local-server use, call Bot API `logOut` once against the official cloud endpoint (see below). Then deploy/restart the Railway service.
8. Check deployment logs for `Local Telegram Bot API ready` and `Bot is starting...`, then message your bot with a video URL you are authorized to download.

## One-time migration from the hosted Bot API
Telegram documents that a bot should be logged out from the hosted Bot API before moving it to a local Bot API server. Do this once, before starting this deployment, using a secure terminal where `BOT_TOKEN` is already set as an environment variable:

```sh
curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/logOut"
```

Do not paste the token into chat, screenshots, shell history, or GitHub. If this bot has never used the hosted Bot API, follow Telegram's current migration guidance anyway.

## Obtain Telegram API ID/hash
Open https://my.telegram.org → API development tools → create an application. Add `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` as Railway Variables. These are separate from the BotFather token.

## Railway volume files
Install Railway CLI, link the project, then upload from your computer:

```sh
railway login
railway link
railway volume files upload ./cookies.txt /cookies.txt
```

Run the upload command with the downloader service selected and the `/data` volume mounted there. If the CLI prompts for a target, select the correct project/environment/service/volume. Check with:

```sh
railway volume files list /
```

Railway CLI volume commands and syntax can change; consult the current Railway volume docs if your CLI version differs.

## Important limits and operations
- Telegram local Bot API mode supports uploads up to 2000 MB, not unlimited 2 GB-plus files. A file at exactly the ceiling may fail due to size accounting; keep below the cap.
- A 2 GB download may need substantially more than 2 GB free disk for separate audio/video streams, merging, and Bot API working data. Monitor the `/data` volume and Railway ephemeral storage.
- Railway bills compute, storage, and network usage. Check plan limits before enabling 2 GB downloads.
- The starter bot is intended for low-volume use; it does not yet implement a global concurrency queue or per-user rate limits.
- Keep yt-dlp updated. YouTube extractor changes can temporarily break downloads.
- Use cookies only for legitimate access to videos you are authorized to download. Never share or publish cookies.

## Local testing
Set the same environment variables locally, install Python 3.12, FFmpeg, and yt-dlp, then run `./start.sh`. For a real local API server, the Dockerfile is the easiest reproducible setup.
