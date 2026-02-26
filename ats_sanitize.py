import re
import unicodedata

ZERO_WIDTH = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]")

def sanitize_text(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = ZERO_WIDTH.sub("", s)

    # normalize quotes/dashes
    s = s.replace("“","\"").replace("”","\"").replace("’","'").replace("–","-").replace("—","-")

    # normalize whitespace
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
