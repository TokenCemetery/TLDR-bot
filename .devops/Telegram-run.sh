#!/bin/bash

image_name="ghcr.io/tokencemetery/tldr-bot"
container_name="tldr-bot"

docker build -t "$image_name" --file .devops/Telegram.Dockerfile .
docker stop "$container_name" &>/dev/null || true
docker rm "$container_name" &>/dev/null || true

docker run -d \
    --env-file .env \
    --volume "./data:/app/data" \
    --name "$container_name" \
    "$image_name"

docker image prune -f
