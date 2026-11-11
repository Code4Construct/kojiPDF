"""Shared, side-effect-free locations for each PDF's review artifacts."""
from pathlib import Path


def directory(pdf_path):
    pdf = Path(pdf_path)
    return pdf.with_name(pdf.stem + "_review")


def artifact(pdf_path, basename):
    return directory(pdf_path) / basename


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
