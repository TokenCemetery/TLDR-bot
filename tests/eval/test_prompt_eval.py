from prompt_eval import dominant_script, find_unsupported_numbers


def test_find_unsupported_numbers_ignores_thousands_separators() -> None:
    source = "The well reached 12262 meters in 1989 and the image shrank to 250 MB."

    assert find_unsupported_numbers("It reached 12 262 m (12,262) in 1989; the image is 250 MB.", source) == []


def test_find_unsupported_numbers_accepts_decimal_comma() -> None:
    assert find_unsupported_numbers("Образ весил 1,2 ГБ.", "The image was 1.2GB.") == []


def test_find_unsupported_numbers_reports_numbers_missing_from_source() -> None:
    source = "The image shrank to 250 MB."

    assert find_unsupported_numbers("Alpine is 5 MB, the image 250 MB, then 5 MB again; built in 2021, 3 times.", source) == ["5", "2021", "3"]


def test_dominant_script() -> None:
    assert dominant_script("Кольская скважина, 12 km") == "CYRILLIC"
    assert dominant_script("Kola Superdeep Borehole (Кольская)") == "LATIN"
    assert dominant_script("123") == "NONE"
