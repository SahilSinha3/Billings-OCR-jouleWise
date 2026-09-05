import io
import os
from dataclasses import dataclass, field
from typing import Any

import pdf2image
import pytesseract
from PIL import Image

from app.core.config import settings
from app.core.logging import logger

if os.path.exists(settings.TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


@dataclass
class WordBox:
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float


@dataclass
class PageExtraction:
    page_number: int
    text: str
    words: list[WordBox] = field(default_factory=list)


@dataclass
class DocumentExtractionResult:
    text: str
    pages: list[PageExtraction]
    confidence_score: float
    bounding_boxes: dict[str, Any] = field(default_factory=dict)


class TesseractOcrEngine:
    def extract(self, file_bytes: bytes, file_name: str) -> DocumentExtractionResult:
        logger.info(f"Executing document text extraction for {file_name}")

        # 1. For digital PDFs, attempt direct Poppler text extraction (100% digital fidelity, <0.05s)
        if file_name.lower().endswith(".pdf"):
            try:
                import subprocess

                proc = subprocess.run(
                    ["pdftotext", "-", "-"],
                    input=file_bytes,
                    capture_output=True,
                    timeout=5,
                )
                digital_text = proc.stdout.decode("utf-8", errors="ignore").strip()
                if len(digital_text) > 150:
                    logger.info(f"Digital PDF text extracted via Poppler for {file_name} ({len(digital_text)} chars)")
                    return DocumentExtractionResult(
                        text=digital_text,
                        pages=[PageExtraction(page_number=1, text=digital_text)],
                        confidence_score=0.99,
                    )
            except Exception as e:
                logger.info(f"Poppler digital text extraction bypassed: {e}")

        # 2. For scanned documents or images, execute neural Tesseract OCR at 200 DPI
        if file_name.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
            images = [Image.open(io.BytesIO(file_bytes))]
        else:
            poppler_path = settings.POPPLER_PATH if os.path.exists(settings.POPPLER_PATH) else None
            images = pdf2image.convert_from_bytes(
                file_bytes,
                dpi=200,
                thread_count=4,
                poppler_path=poppler_path,
                last_page=5,
            )

        pages: list[PageExtraction] = []
        all_text_chunks: list[str] = []
        confidence_samples: list[float] = []

        for page_idx, img in enumerate(images):
            gray_img = img.convert("L")
            ocr_data = pytesseract.image_to_data(
                gray_img,
                output_type=pytesseract.Output.DICT,
                config="--oem 1",
            )
            page_words: list[WordBox] = []
            page_tokens: list[str] = []
            lines: dict[tuple[int, int, int], list[str]] = {}

            for i in range(len(ocr_data["text"])):
                token = ocr_data["text"][i].strip()
                conf = float(ocr_data["conf"][i])
                if token and conf >= 0:
                    page_tokens.append(token)
                    confidence_samples.append(conf / 100.0)
                    page_words.append(
                        WordBox(
                            text=token,
                            x=float(ocr_data["left"][i]),
                            y=float(ocr_data["top"][i]),
                            width=float(ocr_data["width"][i]),
                            height=float(ocr_data["height"][i]),
                            confidence=round(conf / 100.0, 2),
                        )
                    )
                    key = (
                        int(ocr_data.get("block_num", [0])[i]),
                        int(ocr_data.get("par_num", [0])[i]),
                        int(ocr_data.get("line_num", [0])[i]),
                    )
                    lines.setdefault(key, []).append(token)

            if lines:
                full_page_text = "\n".join(" ".join(words) for words in lines.values())
            else:
                full_page_text = pytesseract.image_to_string(gray_img, config="--oem 1")

            pages.append(
                PageExtraction(
                    page_number=page_idx + 1,
                    text=full_page_text or " ".join(page_tokens),
                    words=page_words,
                )
            )
            all_text_chunks.append(full_page_text or " ".join(page_tokens))

        avg_confidence = sum(confidence_samples) / len(confidence_samples) if confidence_samples else 0.85

        return DocumentExtractionResult(
            text="\n\n--- PAGE BREAK ---\n\n".join(all_text_chunks),
            pages=pages,
            confidence_score=round(avg_confidence, 2),
        )


ocr_engine = TesseractOcrEngine()
