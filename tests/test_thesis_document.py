
from __future__ import annotations

import os
import zipfile
from pathlib import Path

from src.thesis.document import load_docx_paragraphs, practical_section_sentences
from src.thesis.generate_assets import ThesisAssetPaths, _load_or_build_validation_records
from src.thesis.validation import resolve_thesis_docx


def test_practical_section_sentences_accepts_current_heading_and_stops_at_next_main_heading(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "thesis.docx"
    _write_minimal_docx(
        docx_path,
        [
            ("Headingsworks", "IEVADS"),
            ("Normal", "Teorētiskā daļa netiek iekļauta."),
            (
                "Headingsworks",
                "Algoritmu izvēles eksperimentālā izpēte sporta turnīru kalendāru sastādīšanā",
            ),
            ("Stylexx", "Praktiskās daļas mērķis un vispārējā uzbūve"),
            ("Normal", "Pirmā praktiskās daļas sentence. Otrā praktiskās daļas sentence."),
            ("Headingsworks", "SECINĀJUMI"),
            ("Normal", "Šī sentence vairs nepieder praktiskajai daļai."),
        ],
    )

    sentences = practical_section_sentences(docx_path)

    assert [sentence.text for sentence in sentences] == [
        "Pirmā praktiskās daļas sentence.",
        "Otrā praktiskās daļas sentence.",
    ]


def test_practical_section_sentences_accepts_uppercase_current_heading(tmp_path: Path) -> None:
    docx_path = tmp_path / "thesis.docx"
    _write_minimal_docx(
        docx_path,
        [
            ("Headingsworks", "IEVADS"),
            (
                "Headingsworks",
                "ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ",
            ),
            ("Stylexx", "Eksperimentālās daļas mērķis un vispārējā uzbūve"),
            ("Normal", "Praktiskās daļas teikums."),
            ("Headingsworks", "SECINĀJUMI"),
            ("Normal", "Šis teikums netiek iekļauts."),
        ],
    )

    sentences = practical_section_sentences(docx_path)

    assert [sentence.text for sentence in sentences] == ["Praktiskās daļas teikums."]


def test_list_paragraph_captions_are_not_treated_as_subsection_headings(tmp_path: Path) -> None:
    docx_path = tmp_path / "thesis.docx"
    _write_minimal_docx(
        docx_path,
        [
            (
                "Headingsworks",
                "Algoritmu izvēles eksperimentālā izpēte sporta turnīru kalendāru sastādīšanā",
            ),
            ("Stylexx", "Datu avoti un datu sagatavošana"),
            ("ListParagraph", "Eksperimentā izmantotās datu kopas sastāvs"),
            ("Normal", "Šis teikums paliek iepriekšējā apakšnodaļā."),
        ],
    )

    paragraphs = load_docx_paragraphs(docx_path)
    list_caption = next(paragraph for paragraph in paragraphs if paragraph.style_name == "List Paragraph")
    sentence = practical_section_sentences(docx_path)[0]

    assert not list_caption.is_subsection_heading
    assert sentence.subsection_heading == "Datu avoti un datu sagatavošana"


def test_resolve_thesis_docx_uses_newest_numbered_copy(tmp_path: Path) -> None:
    older = tmp_path / "kg21071_magistra_darbs_ar_praktisko.docx"
    newer = tmp_path / "kg21071_magistra_darbs_ar_praktisko_3 (4) (1).docx"
    lock_file = tmp_path / "~$kg21071_magistra_darbs_ar_praktisko_3 (4) (1).docx"

    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    lock_file.write_bytes(b"lock")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))
    os.utime(lock_file, (3, 3))

    assert resolve_thesis_docx(tmp_path) == newer


def test_generate_assets_reuses_validation_csv_when_docx_is_not_in_repository(tmp_path: Path) -> None:
    paths = ThesisAssetPaths.from_workspace(tmp_path)
    paths.validation_csv.parent.mkdir(parents=True)
    paths.validation_csv.write_text(
        "\n".join(
            [
                "thesis_section,statement_text,value_in_text,source_file,source_column,actual_value,status,notes,data_reference",
                "4. Test,Checked sentence.,42,data/results/example.csv,value,42,OK,,DATA-1",
            ]
        ),
        encoding="utf-8",
    )

    records = _load_or_build_validation_records(paths)

    assert len(records) == 1
    assert records[0].statement_text == "Checked sentence."
    assert records[0].data_reference == "DATA-1"


def _write_minimal_docx(path: Path, paragraphs: list[tuple[str, str]]) -> None:
    document_paragraphs = "\n".join(
        "\n".join(
            [
                "        <w:p>",
                f'          <w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>',
                f"          <w:r><w:t>{text}</w:t></w:r>",
                "        </w:p>",
            ]
        )
        for style_id, text in paragraphs
    )
    document_xml = "\n".join(
        [
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            "  <w:body>",
            document_paragraphs,
            "  </w:body>",
            "</w:document>",
        ]
    )
    styles_xml = "\n".join(
        [
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            '  <w:style w:styleId="Headingsworks"><w:name w:val="Headings_works"/></w:style>',
            '  <w:style w:styleId="Stylexx"><w:name w:val="Style x.x"/></w:style>',
            '  <w:style w:styleId="ListParagraph"><w:name w:val="List Paragraph"/></w:style>',
            '  <w:style w:styleId="Normal"><w:name w:val="Normal"/></w:style>',
            "</w:styles>",
        ]
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles_xml)
