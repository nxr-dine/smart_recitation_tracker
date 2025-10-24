from app import normalize_arabic, highlight_differences, get_diff_words
from app import normalize_arabic, highlight_differences, get_diff_words


def test_normalize_basic():
    s = "إِنَّ اللَّهَ"
    norm = normalize_arabic(s, normalize_ta=False)
    # Ensure alef variants and tashkeel removed
    assert 'إ' not in norm
    assert 'َ' not in norm


def test_highlight_and_diff():
    orig = "بسم الله الرحمن الرحيم"
    rec = "بسم الله الرحمن"
    o_html, r_html = highlight_differences(orig, rec)
    diffs = get_diff_words(orig, rec)
    # The recognized text is missing the final word 'الرحيم'
    assert 'الرحيم' in diffs['missing']
    assert isinstance(diffs, dict)
