"""Fix mojibake in app.py -- re-decode cp1252-mis-read UTF-8 bytes back to UTF-8."""
import re

with open("app.py", "rb") as f:
    raw = f.read()
if raw[:3] == b"\xef\xbb\xbf":
    raw = raw[3:]
text = raw.decode("utf-8")

def decode_segment(m):
    s = m.group(0)
    try:
        return s.encode("cp1252").decode("utf-8")
    except Exception:
        return s

# Regex matches sequences of 2-6 consecutive latin-supplement/extended chars
# that were originally multi-byte UTF-8 encoded as individual cp1252 codepoints.
text = re.sub(r"[\u00c2-\u00f4][\u0080-\u00bf]+", decode_segment, text)

with open("app.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

with open("app.py", encoding="utf-8") as f:
    c = f.read()
idx = c.find('"icon"')
print("icon check:", repr(c[idx : idx + 30]))
idx2 = c.find("Severe Temperature")
print("desc check:", repr(c[idx2 : idx2 + 80] if idx2 >= 0 else "not found"))
print("DONE")
