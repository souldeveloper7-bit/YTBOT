\
# Build the official Telegram Bot API server from upstream source.
FROM ubuntu:24.04 AS botapi-build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake g++ make gperf zlib1g-dev libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --recursive https://github.com/tdlib/telegram-bot-api.git
WORKDIR /src/telegram-bot-api
RUN mkdir build && cd build \
    && cmake -DCMAKE_BUILD_TYPE=Release .. \
    && cmake --build . --target install -j2

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates libssl3 zlib1g \
    && rm -rf /var/lib/apt/lists/*
COPY --from=botapi-build /usr/local/bin/telegram-bot-api /usr/local/bin/telegram-bot-api
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .
RUN chmod +x /app/start.sh && mkdir -p /data/downloads /data/telegram-bot-api
CMD ["/app/start.sh"]
