# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    # data.json and logs/ live here, on a volume, so they survive rebuilds.
    DATA_DIR=/data \
    # Echo logs to stderr so `docker logs` shows them (there is no tty in a container).
    LOG_TO_CONSOLE=1

# ffmpeg + libopus: needed for voice playback (music.py).
# tini: a proper PID 1, so `docker stop` shuts the bot down promptly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libopus0 tini ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Run as a normal user, not root. The virtualenv is owned by that user so the
# bot's start-up `pip install -U yt-dlp` (see AUTO_UPDATE_YTDLP) can work.
RUN useradd --create-home --uid 1000 bot \
    && mkdir -p /app /data \
    && python -m venv /opt/venv \
    && chown -R bot:bot /app /data /opt/venv

USER bot
WORKDIR /app

# Dependencies first so this layer is cached until requirements.txt changes.
# `deno` is the JavaScript runtime yt-dlp needs to extract YouTube formats.
COPY --chown=bot:bot requirements.txt .
RUN pip install -r requirements.txt deno

COPY --chown=bot:bot *.py ./

VOLUME /data

ENTRYPOINT ["tini", "--"]
CMD ["python", "bot.py"]
