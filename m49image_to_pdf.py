from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


@dataclass
class ImageConversionResult:
    success: bool
    source: Path
    output: Path | None = None
    error: str | None = None


def unique_pdf_path(image_path: Path) -> Path:
    candidate = image_path.with_suffix(".pdf")
    if not candidate.exists():
        return candidate

    index = 1
    while True:
        candidate = image_path.with_name(f"{image_path.stem}_{index}.pdf")
        if not candidate.exists():
            return candidate
        index += 1


def image_frame_to_rgb(frame: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(frame)
    if image.mode in ("RGB", "L"):
        return image.convert("RGB")

    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        return background.convert("RGB")

    return image.convert("RGB")


def convert_image_to_pdf(image_path: str | Path, delete_source: bool = True) -> ImageConversionResult:
    image_path = Path(image_path)
    output_path = unique_pdf_path(image_path)

    try:
        with Image.open(image_path) as image:
            frames = [image_frame_to_rgb(frame.copy()) for frame in ImageSequence.Iterator(image)]

        if not frames:
            raise RuntimeError("画像ファイルにPDF化できるページがありません。")

        first_frame, extra_frames = frames[0], frames[1:]
        first_frame.save(output_path, "PDF", save_all=bool(extra_frames), append_images=extra_frames)

        for frame in frames:
            frame.close()

        if delete_source:
            image_path.unlink(missing_ok=True)

        return ImageConversionResult(success=True, source=image_path, output=output_path)
    except Exception as exc:
        return ImageConversionResult(success=False, source=image_path, output=output_path, error=str(exc))


def convert_all_images_to_pdf(folder_path: str | Path, issue_report=None) -> list[ImageConversionResult]:
    folder_path = Path(folder_path)
    image_files = sorted(
        path
        for path in folder_path.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )

    results = []
    for image_file in image_files:
        print(f"Converting image file: {image_file}")
        result = convert_image_to_pdf(image_file)
        results.append(result)
        if result.success:
            print(f"Image conversion complete: {result.output}")
            continue

        message = f"画像ファイルのPDF変換に失敗しました: {result.source} -> {result.error}"
        print(message)
        if issue_report is not None:
            issue_report.append(
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "category": "Image conversion error",
                    "message": message,
                }
            )

    return results
