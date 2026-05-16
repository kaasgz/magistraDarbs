# Helpers for extracting thesis text from the repository DOCX file.

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final
import xml.etree.ElementTree as ET


WORD_NAMESPACE: Final[str] = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NAMESPACES: Final[dict[str, str]] = {"w": WORD_NAMESPACE}
MAIN_HEADING_STYLE: Final[str] = "Headings_works"
SUBSECTION_HEADING_STYLES: Final[frozenset[str]] = frozenset(
    {
        "Style x.x",
        "Heading 2",
        "Virsraksts 2",
    }
)
NON_CLAIM_PARAGRAPH_STYLES: Final[frozenset[str]] = frozenset({"List Paragraph"})
PRACTICAL_SECTION_TITLES: Final[frozenset[str]] = frozenset(
    {
        "Algoritmu izvēles eksperimentālā izpēte sporta turnīru kalendāru sastādīšanā",
        "Algoritmu izvēles eksperimentālā izpēte sporta turnīru plānošanā",
    }
)
SENTENCE_SPLIT_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True, slots=True)
class ThesisParagraph:

    # One extracted paragraph with lightweight structural metadata.
    paragraph_index: int
    text: str
    style_name: str | None
    main_heading: str | None
    subsection_heading: str | None
    is_main_heading: bool = False
    is_subsection_heading: bool = False


@dataclass(frozen=True, slots=True)
class ThesisSentence:

    # One extracted sentence from the thesis practical section.
    paragraph_index: int
    sentence_index: int
    text: str
    main_heading: str | None
    subsection_heading: str | None

    @property
    def thesis_section(self) -> str:

        # Return one human-readable section label for reports.
        if self.subsection_heading:
            return f"4. {self.subsection_heading}"
        if self.main_heading:
            return self.main_heading
        return "4. Praktiskā daļa"


def load_docx_paragraphs(docx_path: str | Path) -> list[ThesisParagraph]:

    # Extract paragraphs from one DOCX thesis file.
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(f"Thesis DOCX file not found: {path}")

    with zipfile.ZipFile(path) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        styles_xml = ET.fromstring(archive.read("word/styles.xml"))

    style_map = _build_style_map(styles_xml)
    paragraphs: list[ThesisParagraph] = []
    current_main_heading: str | None = None
    current_subsection_heading: str | None = None

    for paragraph_index, paragraph_node in enumerate(
        document_xml.findall(".//w:body/w:p", NAMESPACES),
        start=1,
    ):
        text = _paragraph_text(paragraph_node)
        if not text:
            continue

        style_name = style_map.get(_paragraph_style_id(paragraph_node))
        is_main_heading = style_name == MAIN_HEADING_STYLE
        is_subsection_heading = False

        if is_main_heading:
            current_main_heading = text
            current_subsection_heading = None
        elif current_main_heading is not None and _is_subsection_heading(text, style_name):
            current_subsection_heading = text
            is_subsection_heading = True

        paragraphs.append(
            ThesisParagraph(
                paragraph_index=paragraph_index,
                text=text,
                style_name=style_name,
                main_heading=current_main_heading,
                subsection_heading=current_subsection_heading,
                is_main_heading=is_main_heading,
                is_subsection_heading=is_subsection_heading,
            )
        )

    return paragraphs


def practical_section_sentences(docx_path: str | Path) -> list[ThesisSentence]:

    # Return sentence records from the practical section only.
    paragraphs = load_docx_paragraphs(docx_path)
    in_practical_section = False
    sentences: list[ThesisSentence] = []

    for paragraph in paragraphs:
        if paragraph.is_main_heading:
            if _is_practical_section_title(paragraph.text):
                in_practical_section = True
                continue
            if in_practical_section:
                break
        if not in_practical_section:
            continue
        if paragraph.is_subsection_heading:
            continue
        if paragraph.style_name in NON_CLAIM_PARAGRAPH_STYLES:
            continue

        split_sentences = [
            candidate.strip()
            for candidate in SENTENCE_SPLIT_PATTERN.split(paragraph.text)
            if candidate.strip()
        ]
        for sentence_index, sentence in enumerate(split_sentences, start=1):
            sentences.append(
                ThesisSentence(
                    paragraph_index=paragraph.paragraph_index,
                    sentence_index=sentence_index,
                    text=sentence,
                    main_heading=paragraph.main_heading,
                    subsection_heading=paragraph.subsection_heading,
                )
            )

    return sentences


def thesis_markdown(docx_path: str | Path, sentence_references: dict[str, list[str]] | None = None) -> str:

    # Render the DOCX thesis into lightweight Markdown.
    paragraphs = load_docx_paragraphs(docx_path)
    sentence_references = sentence_references or {}
    lines: list[str] = []

    for paragraph in paragraphs:
        text = paragraph.text
        if paragraph.is_main_heading:
            lines.append(f"# {text}")
            lines.append("")
            continue
        if paragraph.is_subsection_heading:
            lines.append(f"## {text}")
            lines.append("")
            continue

        lines.append(_append_references_to_paragraph(text, sentence_references))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _append_references_to_paragraph(text: str, sentence_references: dict[str, list[str]]) -> str:

    # Append `[DATA-x]` references after matching sentences inside one paragraph.
    sentences = [candidate.strip() for candidate in SENTENCE_SPLIT_PATTERN.split(text) if candidate.strip()]
    rendered_sentences: list[str] = []
    for sentence in sentences:
        references = sentence_references.get(sentence, [])
        if references:
            rendered_sentences.append(f"{sentence} {' '.join(references)}")
        else:
            rendered_sentences.append(sentence)
    return " ".join(rendered_sentences)


def _is_practical_section_title(text: str) -> bool:

    # Return whether one main heading names the thesis practical section.
    normalized = text.casefold()
    return normalized in {title.casefold() for title in PRACTICAL_SECTION_TITLES}


def _build_style_map(styles_xml: ET.Element) -> dict[str, str]:

    # Return a Word style-id to style-name lookup.
    style_map: dict[str, str] = {}
    for style in styles_xml.findall("w:style", NAMESPACES):
        style_id = style.get(f"{{{WORD_NAMESPACE}}}styleId")
        name_node = style.find("w:name", NAMESPACES)
        if style_id:
            style_map[style_id] = (
                name_node.get(f"{{{WORD_NAMESPACE}}}val") if name_node is not None else style_id
            )
    return style_map


def _paragraph_text(paragraph_node: ET.Element) -> str:

    # Concatenate text nodes inside one Word paragraph.
    chunks = [node.text for node in paragraph_node.findall(".//w:t", NAMESPACES) if node.text]
    return "".join(chunks).strip()


def _paragraph_style_id(paragraph_node: ET.Element) -> str | None:

    # Return the style id for one Word paragraph when available.
    properties = paragraph_node.find("w:pPr", NAMESPACES)
    if properties is None:
        return None
    style_node = properties.find("w:pStyle", NAMESPACES)
    if style_node is None:
        return None
    return style_node.get(f"{{{WORD_NAMESPACE}}}val")


def _is_subsection_heading(text: str, style_name: str | None) -> bool:

    # Heuristically identify thesis subsection headings from plain paragraphs.
    if style_name not in SUBSECTION_HEADING_STYLES:
        return False

    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith((".", "!", "?", ";", ":")):
        return False
    if len(stripped) > 110:
        return False
    if stripped.isupper():
        return False
    return True
