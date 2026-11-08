#!/bin/bash

image_name="ghcr.io/tokencemetery/tldr-bot"

docker build -t "$image_name" --file .devops/Telegram.Dockerfile .
