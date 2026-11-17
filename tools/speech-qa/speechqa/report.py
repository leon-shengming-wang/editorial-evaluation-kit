import base64
import json
import re
import mimetypes
from pathlib import Path


def render(data, audio):
    payload = (
        json.dumps(data, ensure_ascii=False, allow_nan=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    mime = mimetypes.guess_type(str(audio))[0] or "audio/octet-stream"
    replacements = {
        "DATA_PAYLOAD": payload,
        "AUDIO_PAYLOAD": "data:"
        + mime
        + ";base64,"
        + base64.b64encode(Path(audio).read_bytes()).decode(),
        "SCRIPT_PAYLOAD": Path(__file__).with_name("report.js").read_text(),
    }
    return re.sub(
        r"DATA_PAYLOAD|AUDIO_PAYLOAD|SCRIPT_PAYLOAD",
        lambda m: replacements[m.group(0)],
        Path(__file__).with_name("report.html").read_text(),
    )
