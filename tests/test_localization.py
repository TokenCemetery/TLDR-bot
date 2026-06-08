from pathlib import Path
from unittest.mock import patch

import yaml
from src.localization import DEFAULT_LOCALE, _setup_i18n, normalize_locale, translate


def test_all_locales_define_openai_prompts() -> None:
    for locale_file in Path("locales").glob("locale.*.yml"):
        data = yaml.safe_load(locale_file.read_text(encoding="utf-8"))
        assert "system_prompt" in data["openai"], locale_file
        assert "user_prompt" in data["openai"], locale_file
        assert "prompt" not in data["openai"], locale_file


def testnormalize_locale_none() -> None:
    assert normalize_locale(None) == DEFAULT_LOCALE


def testnormalize_locale_empty() -> None:
    assert normalize_locale("") == DEFAULT_LOCALE


def testnormalize_locale_basic() -> None:
    assert normalize_locale("en") == "en"
    assert normalize_locale("fr") == "fr"


def testnormalize_locale_with_underscores() -> None:
    assert normalize_locale("en_US") == "en"
    assert normalize_locale("fr_FR") == "fr"
    assert normalize_locale("de_DE") == "de"


def testnormalize_locale_with_hyphens() -> None:
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("fr-FR") == "fr"
    assert normalize_locale("pt-BR") == "pt"


def testnormalize_locale_case_insensitive() -> None:
    assert normalize_locale("EN") == "en"
    assert normalize_locale("Fr") == "fr"
    assert normalize_locale("ZH-CN") == "zh"


def testnormalize_locale_with_extra_spaces() -> None:
    assert normalize_locale(" en ") == "en"
    assert normalize_locale(" fr-FR ") == "fr"


def test_setup_i18n_called_once() -> None:
    # Mock i18n module functions
    with patch("src.localization.i18n") as mock_i18n:
        # Call setup twice to ensure it only executes once
        _setup_i18n()
        _setup_i18n()

        # Check that the setup methods were called only once
        assert mock_i18n.load_path.append.called
        expected_set_calls = 6
        assert mock_i18n.set.call_count == expected_set_calls  # Exactly 6 set calls


def test_translate_basic() -> None:
    # Mock i18n translation
    with patch("src.localization.i18n") as mock_i18n:
        mock_i18n.t.return_value = "Translated text"
        mock_i18n.fallback = DEFAULT_LOCALE

        result = translate("some.key", locale="en")

        assert result == "Translated text"
        mock_i18n.t.assert_called_once_with("some.key", locale="en")


def test_translate_with_kwargs() -> None:
    # Mock i18n translation with kwargs
    with patch("src.localization.i18n") as mock_i18n:
        mock_i18n.t.return_value = "Hello John!"

        result = translate("greeting", locale="en", name="John")

        assert result == "Hello John!"
        mock_i18n.t.assert_called_once_with("greeting", locale="en", name="John")


def test_translate_fallback_to_default_locale() -> None:
    # Mock i18n to raise exception for first locale but succeed for fallback
    with patch("src.localization.i18n") as mock_i18n:
        mock_i18n.t.side_effect = [Exception("Not found"), "Fallback translation"]

        result = translate("some.key", locale="nonexistent")

        # Should try the requested locale first, then fall back to default
        assert result == "Fallback translation"
        expected_t_calls = 2
        assert mock_i18n.t.call_count == expected_t_calls


def test_translate_returns_key_if_not_found() -> None:
    # Mock i18n to raise exceptions for both locales
    with patch("src.localization.i18n") as mock_i18n:
        mock_i18n.t.side_effect = [
            Exception("Not found"),
            Exception("Default not found"),
        ]

        result = translate("some.key", locale="nonexistent")

        # Should return the key itself if no translation is found
        assert result == "some.key"


def test_translate_with_none_locale() -> None:
    with patch("src.localization.i18n") as mock_i18n:
        mock_i18n.t.return_value = "Default translation"

        result = translate("some.key")

        assert result == "Default translation"
        # Should use default locale when none provided
        mock_i18n.t.assert_called_once_with("some.key", locale=DEFAULT_LOCALE)
