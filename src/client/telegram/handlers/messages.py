import logging

from aiogram import F, Router
from aiogram.types import LinkPreviewOptions, Message

from src.client.telegram.handlers.helpers import get_language
from src.config import Settings
from src.load.video_loader import VideoDataLoader
from src.load.video_provider import extract_urls
from src.localization import translate
from src.rate_limiter import UserRateLimiter
from src.transform.summarization import OpenAISummarizer
from src.utils.markdown import markdown_to_telegram_html
from src.utils.text import to_lexical_chunks

logger = logging.getLogger(__name__)

message_router = Router()


@message_router.message(F.text & ~F.text.startswith("/"))
async def handle_message(  # noqa: C901, PLR0911
    message: Message,
    loader: VideoDataLoader,
    summarizer: OpenAISummarizer,
    rate_limiter: UserRateLimiter,
    settings: Settings,
) -> None:
    """Load URL content, summarize it, and send the summary to the user."""

    user = message.from_user
    if user is None:
        return

    language = get_language(user)
    if user.is_bot:
        logger.warning("Ignored bot message", extra={"userID": user.id})
        return

    if message.text is None:
        logger.warning("Got no message from ", extra={"userID": user.id})
        return

    logger.info(
        "Processing message",
        extra={
            "userID": user.id,
            "username": user.username,
            "language": language,
            "message_id": message.message_id,
        },
    )

    if await rate_limiter.is_limited(user.id):
        logger.warning(
            "Rate Limit exceeded",
            extra={
                "userID": user.id,
                "username": user.username,
                "language": language,
            },
        )
        await message.reply(
            translate(
                "telegram.error.rate_limited",
                locale=language,
                rateLimitWindow=settings.rate_limit_window_seconds,
            )
        )
        return

    text = message.text or ""
    urls = extract_urls(text)
    if not urls:
        logger.info(
            "No URL found in message",
            extra={
                "userID": user.id,
                "username": user.username,
                "message_id": message.message_id,
                "text": message.text,
            },
        )
        await message.reply(translate("telegram.error.no_url_found", locale=language))
        return

    processing_message = await message.reply(translate("telegram.progress.processing", locale=language))

    if len(urls) > 1:
        logger.info(
            "Multiple URLs detected",
            extra={
                "userID": user.id,
                "username": user.username,
                "message_id": message.message_id,
                "url_count": len(urls),
            },
        )
        await processing_message.edit_text(translate("telegram.error.multiple_urls", locale=language))
        return

    source_url = urls[0]
    logger.info(
        "Processing video URL",
        extra={
            "userID": user.id,
            "username": user.username,
            "message_id": message.message_id,
            "url": source_url,
        },
    )

    await processing_message.edit_text(translate("telegram.progress.fetching_info", locale=language))

    try:
        document = await loader.load(source_url)
    except Exception as exc:
        logger.exception(
            "Failed to load transcript",
            extra={
                "userID": user.id,
                "username": user.username,
                "message_id": message.message_id,
                "url": source_url,
                "error": str(exc),
            },
        )
        await processing_message.edit_text(translate("telegram.error.transcript_failed", locale=language))
        return

    logger.info(
        "Content loaded",
        extra={
            "userID": user.id,
            "username": user.username,
            "message_id": message.message_id,
        },
    )

    await processing_message.edit_text(translate("telegram.progress.summarizing", locale=language))

    try:
        summary = await summarizer.summarize(document, language)
    except Exception as exc:
        logger.exception(
            "Failed to summarize content",
            extra={
                "userID": user.id,
                "username": user.username,
                "message_id": message.message_id,
                "error": str(exc),
            },
        )
        await processing_message.edit_text(translate("telegram.error.summary_failed", locale=language))
        return

    logger.info(
        "Summary generated",
        extra={
            "userID": user.id,
            "username": user.username,
            "message_id": message.message_id,
            "summary_length": len(summary),
        },
    )

    title = translate(
        "telegram.response.title",
        locale=language,
        title=document.title,
        url=document.url,
    )
    response = f"{title}\n{summary}".strip()
    chunks = to_lexical_chunks(response, settings.max_telegram_message_length)
    for i, chunk in enumerate(chunks):
        logger.debug(
            "Sending response chunk",
            extra={
                "userID": user.id,
                "username": user.username,
                "message_id": message.message_id,
                "chunk_index": i,
            },
        )
        await message.reply(
            text=markdown_to_telegram_html(chunk),
            link_preview_options=LinkPreviewOptions(is_disabled=False, url=document.url, show_above_text=True, prefer_small_media=True),
        )

    logger.info(
        "Response sent",
        extra={
            "userID": user.id,
            "username": user.username,
            "message_id": message.message_id,
            "url": document.url,
        },
    )

    try:
        await processing_message.delete()
    except Exception as exc:
        logger.exception(
            "Failed to delete processing message",
            extra={
                "userID": user.id,
                "username": user.username,
                "message_id": message.message_id,
                "error": str(exc),
            },
        )
