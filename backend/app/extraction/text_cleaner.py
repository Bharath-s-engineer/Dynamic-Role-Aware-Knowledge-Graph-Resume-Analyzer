"""
app/extraction/text_cleaner.py
Text normalisation after PDF extraction.
"""

import re
import unicodedata

_LIGATURES = {"\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff", "\ufb03": "ffi", "\ufb04": "ffl"}


def clean_extracted_text(raw: str) -> str:
    text = raw
    # 1. Replace ligatures
    for lig, rep in _LIGATURES.items():
        text = text.replace(lig, rep)
    # 2. Unicode NFC
    text = unicodedata.normalize("NFC", text)
    # 3. Remove non-printable (keep newline + tab)
    text = re.sub(r"[^\x09\x0a\x20-\x7e\u0080-\uFFFF]", "", text)
    # 4. Fix broken hyphenation
    text = re.sub(r"-\s*\n\s*", "", text)
    # 5. Collapse whitespace (preserve single newlines as sentence breaks)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
