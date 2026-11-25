"""Shared, side-effect-free locations for each PDF's review artifacts."""
from pathlib import Path
import hashlib
import tempfile

# Application startup applies the persisted setting before opening PDFs.
enabled = True
_temporary = None
DISABLED_HINT = "外部データ保存がオフのため使用できません。「設定」で有効にできます。"

def temporary_index(pdf_path, mode):
    global _temporary
    if _temporary is None:
        _temporary = tempfile.TemporaryDirectory(prefix="kojiPDFviewer-")
    key = hashlib.sha256(str(Path(pdf_path).resolve()).encode("utf-8")).hexdigest()
    return str(Path(_temporary.name) / (key + "." + mode + ".sqlite3"))



def directory(pdf_path):
    pdf = Path(pdf_path)
    return pdf.with_name(pdf.stem + "_review")


def artifact(pdf_path, basename):
    return directory(pdf_path) / basename


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
