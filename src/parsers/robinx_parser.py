"""Utilities for parsing RobinX / ITC2021 XML instances."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Literal

from lxml import etree
from pydantic import BaseModel, Field


class TournamentMetadata(BaseModel):
    """High-level metadata describing a tournament instance."""

    name: str | None = None
    source_path: str | None = None
    objective_name: str | None = None
    objective_sense: str | None = None
    synthetic: bool | None = None
    generated_at: str | None = None
    generation_seed: int | None = None
    difficulty_level: str | None = None
    round_robin_mode: str | None = None


class ParserNote(BaseModel):
    """One structured note describing a parsing ambiguity or recovery event."""

    severity: Literal["info", "warning"] = "info"
    code: str
    message: str


class Team(BaseModel):
    """A team entry extracted from the instance."""

    identifier: str | None = None
    name: str | None = None


class Slot(BaseModel):
    """A time slot or round entry extracted from the instance."""

    identifier: str | None = None
    name: str | None = None


class Constraint(BaseModel):
    """A constraint entry extracted from the instance."""

    identifier: str | None = None
    category: str | None = None
    tag: str | None = None
    type_name: str | None = None


class InstanceSummary(BaseModel):
    """Summary view of a parsed sports timetabling instance."""

    metadata: TournamentMetadata
    teams: list[Team] = Field(default_factory=list)
    slots: list[Slot] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    team_count: int = 0
    slot_count: int = 0
    constraint_count: int = 0
    constraint_categories: list[str] = Field(default_factory=list)
    parser_notes: list[ParserNote] = Field(default_factory=list)


def load_instance(xml_path: str) -> InstanceSummary:
    """Load a RobinX / ITC2021 XML instance into a typed summary object.

    The parser is intentionally defensive. It extracts a compact summary from
    common RobinX / ITC2021-like XML layouts while tolerating missing fields,
    optional sections, XML namespaces, and recoverable XML syntax issues.

    Args:
        xml_path: Path to the XML instance file.

    Returns:
        Parsed instance summary with metadata, teams, slots, constraints,
        count-based aggregates, and structured parser notes for auditability.
    """

    path = Path(xml_path)
    parser = etree.XMLParser(remove_comments=True, recover=True)
    try:
        tree = etree.parse(str(path), parser)
    except (OSError, etree.XMLSyntaxError) as exc:
        raise ValueError(f"Failed to parse XML instance {path}: {exc}") from exc

    root = tree.getroot()
    if root is None:
        raise ValueError(f"XML instance {path} did not produce a root element.")

    teams, duplicate_team_count = _parse_teams(root)
    slots, duplicate_slot_count = _parse_slots(root)
    constraints, duplicate_constraint_count = _parse_constraints(root)

    team_count = _extract_count(root, teams, "Teams", "Team", "numberTeams", "teams")
    slot_count = _extract_count(root, slots, "Slots", "Slot", "numberSlots", "slots")
    constraint_count = _extract_count(
        root,
        constraints,
        "Constraints",
        "Constraint",
        "numberConstraints",
        "constraints",
    )

    metadata = TournamentMetadata(
        name=_extract_instance_name(root, path),
        source_path=str(path),
        objective_name=_extract_objective_name(root),
        objective_sense=_extract_objective_sense(root),
        synthetic=_extract_boolean(
            [
                _attribute_value(root, "synthetic"),
                _first_text(root, [".//*[local-name()='MetaData']/*[local-name()='Synthetic']"]),
            ]
        ),
        generated_at=_first_text(
            root,
            [
                ".//*[local-name()='MetaData']/*[local-name()='GeneratedAt']",
            ],
        ),
        generation_seed=_first_integer(
            [
                _first_text(root, [".//*[local-name()='MetaData']/*[local-name()='GenerationSeed']"]),
            ]
        ),
        difficulty_level=_first_text(
            root,
            [
                ".//*[local-name()='MetaData']/*[local-name()='Difficulty']",
                ".//*[local-name()='Difficulty']",
            ],
        ),
        round_robin_mode=_extract_round_robin_mode(root),
    )
    parser_notes = _build_parser_notes(
        root=root,
        path=path,
        parser=parser,
        metadata=metadata,
        teams=teams,
        slots=slots,
        constraints=constraints,
        team_count=team_count,
        slot_count=slot_count,
        constraint_count=constraint_count,
        duplicate_team_count=duplicate_team_count,
        duplicate_slot_count=duplicate_slot_count,
        duplicate_constraint_count=duplicate_constraint_count,
    )

    constraint_categories = sorted(
        {
            value
            for constraint in constraints
            for value in (constraint.category, constraint.tag, constraint.type_name)
            if value
        }
    )

    return InstanceSummary(
        metadata=metadata,
        teams=teams,
        slots=slots,
        constraints=constraints,
        team_count=team_count,
        slot_count=slot_count,
        constraint_count=constraint_count,
        constraint_categories=constraint_categories,
        parser_notes=parser_notes,
    )


def _build_parser_notes(
    *,
    root: etree._Element,
    path: Path,
    parser: etree.XMLParser,
    metadata: TournamentMetadata,
    teams: list[Team],
    slots: list[Slot],
    constraints: list[Constraint],
    team_count: int,
    slot_count: int,
    constraint_count: int,
    duplicate_team_count: int,
    duplicate_slot_count: int,
    duplicate_constraint_count: int,
) -> list[ParserNote]:
    """Build structured parser notes for recoveries and ambiguities."""

    notes: list[ParserNote] = []
    notes.extend(_notes_from_error_log(parser.error_log))

    if not _has_explicit_instance_name(root):
        notes.append(
            ParserNote(
                severity="info",
                code="missing_instance_name",
                message=(
                    "The instance name was missing in XML metadata, so the parser fell back to "
                    f"the file stem '{path.stem}'."
                ),
            )
        )

    notes.extend(_missing_section_notes(root, "Teams", "Team", optional=False))
    notes.extend(_missing_section_notes(root, "Slots", "Slot", optional=True))
    notes.extend(_missing_section_notes(root, "Constraints", "Constraint", optional=True))

    if duplicate_team_count > 0:
        notes.append(
            ParserNote(
                severity="warning",
                code="duplicate_team_entries",
                message=f"{duplicate_team_count} duplicate team entries were removed during parsing.",
            )
        )
    if duplicate_slot_count > 0:
        notes.append(
            ParserNote(
                severity="warning",
                code="duplicate_slot_entries",
                message=f"{duplicate_slot_count} duplicate slot entries were removed during parsing.",
            )
        )
    if duplicate_constraint_count > 0:
        notes.append(
            ParserNote(
                severity="warning",
                code="duplicate_constraint_entries",
                message=(
                    f"{duplicate_constraint_count} duplicate constraint entries were removed during parsing."
                ),
            )
        )

    notes.extend(
        _count_mismatch_notes(
            root=root,
            item_count=len(teams),
            resolved_count=team_count,
            section_name="Teams",
            item_name="Team",
            count_attribute="numberTeams",
            fallback_attribute="teams",
            code="team_count_mismatch",
            label="teams",
        )
    )
    notes.extend(
        _count_mismatch_notes(
            root=root,
            item_count=len(slots),
            resolved_count=slot_count,
            section_name="Slots",
            item_name="Slot",
            count_attribute="numberSlots",
            fallback_attribute="slots",
            code="slot_count_mismatch",
            label="slots",
        )
    )
    notes.extend(
        _count_mismatch_notes(
            root=root,
            item_count=len(constraints),
            resolved_count=constraint_count,
            section_name="Constraints",
            item_name="Constraint",
            count_attribute="numberConstraints",
            fallback_attribute="constraints",
            code="constraint_count_mismatch",
            label="constraints",
        )
    )

    notes.extend(_constraint_ambiguity_notes(constraints))

    return notes


def _notes_from_error_log(error_log: etree._ListErrorLog) -> list[ParserNote]:
    """Convert recoverable XML parser issues into structured notes."""

    notes: list[ParserNote] = []
    seen: set[tuple[str, int, int]] = set()
    for entry in error_log:
        message = _normalize_text(entry.message)
        if message is None:
            continue

        marker = (message, entry.line, entry.column)
        if marker in seen:
            continue
        seen.add(marker)

        notes.append(
            ParserNote(
                severity="warning",
                code="xml_recovery_applied",
                message=f"Recoverable XML issue at line {entry.line}, column {entry.column}: {message}",
            )
        )
    return notes


def _missing_section_notes(
    root: etree._Element,
    section_name: str,
    item_name: str,
    *,
    optional: bool,
) -> list[ParserNote]:
    """Create notes for missing or empty sections."""

    section_present = bool(root.xpath(f".//*[local-name()='{section_name}']"))
    items_present = bool(root.xpath(f".//*[local-name()='{item_name}']"))
    if section_present or items_present:
        return []

    severity: Literal["info", "warning"] = "info" if optional else "warning"
    label = section_name.casefold()
    message = (
        f"The XML instance does not contain a '{section_name}' section, so the parser used an empty "
        f"{label} list."
    )
    return [
        ParserNote(
            severity=severity,
            code=f"missing_{section_name.casefold()}_section",
            message=message,
        )
    ]


def _count_mismatch_notes(
    *,
    root: etree._Element,
    item_count: int,
    resolved_count: int,
    section_name: str,
    item_name: str,
    count_attribute: str,
    fallback_attribute: str,
    code: str,
    label: str,
) -> list[ParserNote]:
    """Create a note when a declared count does not match parsed items."""

    declared_count = _extract_declared_count(
        root,
        section_name=section_name,
        item_name=item_name,
        count_attribute=count_attribute,
        fallback_attribute=fallback_attribute,
    )
    if declared_count is None or declared_count == item_count:
        return []

    return [
        ParserNote(
            severity="warning",
            code=code,
            message=(
                f"The XML declared {declared_count} {label}, but the parser extracted {item_count}. "
                f"The summary count was resolved to {resolved_count}."
            ),
        )
    ]


def _constraint_ambiguity_notes(constraints: list[Constraint]) -> list[ParserNote]:
    """Summarize ambiguous or partially specified constraints."""

    missing_category_count = sum(1 for constraint in constraints if _read_text_field(constraint, "category") is None)
    missing_tag_count = sum(1 for constraint in constraints if _read_text_field(constraint, "tag") is None)
    missing_type_count = sum(1 for constraint in constraints if _read_text_field(constraint, "type_name") is None)

    notes: list[ParserNote] = []
    if missing_category_count > 0:
        notes.append(
            ParserNote(
                severity="info",
                code="constraints_missing_category",
                message=(
                    f"{missing_category_count} constraint entries do not declare an explicit category."
                ),
            )
        )
    if missing_tag_count > 0:
        notes.append(
            ParserNote(
                severity="info",
                code="constraints_missing_tag",
                message=f"{missing_tag_count} constraint entries do not declare an explicit tag.",
            )
        )
    if missing_type_count > 0:
        notes.append(
            ParserNote(
                severity="info",
                code="constraints_missing_type",
                message=(
                    f"{missing_type_count} constraint entries do not declare an explicit hard/soft type."
                ),
            )
        )
    return notes


def _extract_instance_name(root: etree._Element, path: Path) -> str | None:
    """Return the instance name if present, otherwise fall back to file stem."""

    candidates = [
        _attribute_value(root, "name"),
        _attribute_value(root, "InstanceName"),
        _first_text(
            root,
            [
                ".//*[local-name()='MetaData']/*[local-name()='Name']",
                ".//*[local-name()='Metadata']/*[local-name()='Name']",
                ".//*[local-name()='InstanceName']",
                ".//*[local-name()='Name']",
            ],
        ),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    return path.stem if path.stem else None


def _has_explicit_instance_name(root: etree._Element) -> bool:
    """Return whether the XML contains an explicit instance name field."""

    candidates = [
        _attribute_value(root, "name"),
        _attribute_value(root, "InstanceName"),
        _first_text(
            root,
            [
                ".//*[local-name()='MetaData']/*[local-name()='Name']",
                ".//*[local-name()='Metadata']/*[local-name()='Name']",
                ".//*[local-name()='InstanceName']",
            ],
        ),
    ]
    return any(candidate is not None for candidate in candidates)


def _extract_objective_name(root: etree._Element) -> str | None:
    """Return the objective label when present."""

    return _first_non_empty(
        [
            _attribute_value(root, "objective"),
            _first_text(
                root,
                [
                    ".//*[local-name()='Objective']/@name",
                    ".//*[local-name()='Objective']",
                    ".//*[local-name()='MetaData']/*[local-name()='ObjectiveName']",
                ],
            ),
        ]
    )


def _extract_objective_sense(root: etree._Element) -> str | None:
    """Return the optimization sense when present."""

    return _first_non_empty(
        [
            _first_text(
                root,
                [
                    ".//*[local-name()='Objective']/@sense",
                    ".//*[local-name()='MetaData']/*[local-name()='ObjectiveSense']",
                ],
            ),
        ]
    )


def _extract_round_robin_mode(root: etree._Element) -> str | None:
    """Return a normalized round-robin mode when present."""

    explicit_mode = _first_non_empty(
        [
            _first_text(
                root,
                [
                    ".//*[local-name()='MetaData']/*[local-name()='RoundRobinMode']",
                    ".//*[local-name()='Format']/@mode",
                ],
            )
        ]
    )
    if explicit_mode:
        normalized = explicit_mode.casefold()
        if "double" in normalized:
            return "double"
        if "single" in normalized:
            return "single"

    round_robin_count = _first_integer(
        [
            _first_text(root, [".//*[local-name()='Format']/*[local-name()='numberRoundRobin']"]),
        ]
    )
    if round_robin_count is None:
        return None
    if round_robin_count >= 2:
        return "double"
    if round_robin_count == 1:
        return "single"
    return None


def _parse_teams(root: etree._Element) -> tuple[list[Team], int]:
    """Parse team entries from likely team sections."""

    team_elements = _find_elements(root, section_names=("Teams",), element_names=("Team",))
    if not team_elements:
        team_elements = _matching_descendants(root, ("Team",))

    teams: list[Team] = []
    seen: set[tuple[str | None, str | None]] = set()
    duplicate_count = 0
    for element in team_elements:
        identifier = _first_non_empty(
            [
                _attribute_value(element, "id"),
                _attribute_value(element, "ID"),
                _attribute_value(element, "identifier"),
                _attribute_value(element, "name"),
                _first_text(element, ["./*[local-name()='Id']", "./*[local-name()='ID']"]),
            ]
        )
        name = _first_non_empty(
            [
                _attribute_value(element, "name"),
                _attribute_value(element, "label"),
                _attribute_value(element, "shortName"),
                _first_text(
                    element,
                    [
                        "./*[local-name()='Name']",
                        "./*[local-name()='Label']",
                        "./*[local-name()='ShortName']",
                    ],
                ),
            ]
        )
        key = (identifier, name)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        teams.append(Team(identifier=identifier, name=name))
    return teams, duplicate_count


def _parse_slots(root: etree._Element) -> tuple[list[Slot], int]:
    """Parse slot or round entries from likely slot sections."""

    slot_elements = _find_elements(
        root,
        section_names=("Slots", "Rounds"),
        element_names=("Slot", "Round"),
    )
    if not slot_elements:
        slot_elements = _matching_descendants(root, ("Slot", "Round"))

    slots: list[Slot] = []
    seen: set[tuple[str | None, str | None]] = set()
    duplicate_count = 0
    for element in slot_elements:
        identifier = _first_non_empty(
            [
                _attribute_value(element, "id"),
                _attribute_value(element, "ID"),
                _attribute_value(element, "identifier"),
                _attribute_value(element, "name"),
                _first_text(element, ["./*[local-name()='Id']", "./*[local-name()='ID']"]),
            ]
        )
        name = _first_non_empty(
            [
                _attribute_value(element, "name"),
                _attribute_value(element, "label"),
                _first_text(element, ["./*[local-name()='Name']", "./*[local-name()='Label']"]),
            ]
        )
        key = (identifier, name)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        slots.append(Slot(identifier=identifier, name=name))
    return slots, duplicate_count


def _parse_constraints(root: etree._Element) -> tuple[list[Constraint], int]:
    """Parse constraints from likely constraint sections."""

    constraint_elements = _find_elements(
        root,
        section_names=("Constraints",),
        element_names=("Constraint",),
    )
    if not constraint_elements:
        constraint_elements = _find_grouped_constraint_elements(root)

    constraints: list[Constraint] = []
    seen: set[tuple[tuple[tuple[str, str], ...], str | None, str | None, str | None, str | None]] = set()
    duplicate_count = 0
    for element in constraint_elements:
        parent = element.getparent()
        identifier = _first_non_empty(
            [
                _attribute_value(element, "id"),
                _attribute_value(element, "ID"),
                _attribute_value(element, "identifier"),
                _first_text(element, ["./*[local-name()='Id']", "./*[local-name()='ID']"]),
            ]
        )
        category = _first_non_empty(
            [
                _attribute_value(element, "category"),
                _attribute_value(element, "Category"),
                _attribute_value(element, "group"),
                _constraint_category_from_parent(parent),
                _first_text(
                    element,
                    [
                        "./*[local-name()='Category']",
                        "./*[local-name()='Group']",
                    ],
                ),
            ]
        )
        tag = _first_non_empty(
            [
                _attribute_value(element, "tag"),
                _attribute_value(element, "Tag"),
                _attribute_value(element, "name"),
                _first_text(
                    element,
                    [
                        "./*[local-name()='Tag']",
                        "./*[local-name()='Name']",
                    ],
                ),
                _constraint_tag_from_element(element),
            ]
        )
        type_name = _first_non_empty(
            [
                _attribute_value(element, "type"),
                _attribute_value(element, "Type"),
                _first_text(element, ["./*[local-name()='Type']"]),
            ]
        )
        attribute_signature = tuple(sorted((str(key), str(value)) for key, value in element.attrib.items()))
        key = (attribute_signature, identifier, category, tag, type_name)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        constraints.append(
            Constraint(
                identifier=identifier,
                category=category,
                tag=tag,
                type_name=type_name,
            )
        )
    return constraints, duplicate_count


def _extract_count(
    root: etree._Element,
    items: list[object],
    section_name: str,
    item_name: str,
    count_attribute: str,
    fallback_attribute: str,
) -> int:
    """Extract an explicit count when present, otherwise use parsed item count."""

    explicit_count = _extract_declared_count(
        root,
        section_name=section_name,
        item_name=item_name,
        count_attribute=count_attribute,
        fallback_attribute=fallback_attribute,
    )
    return explicit_count if explicit_count is not None else len(items)


def _extract_declared_count(
    root: etree._Element,
    *,
    section_name: str,
    item_name: str,
    count_attribute: str,
    fallback_attribute: str,
) -> int | None:
    """Extract an explicitly declared count from common XML layouts."""

    return _first_integer(
        [
            _attribute_value(root, count_attribute),
            _first_text(
                root,
                [
                    f".//*[local-name()='{section_name}']/@count",
                    f".//*[local-name()='{section_name}']/@number",
                    f".//*[local-name()='{section_name}']/*[local-name()='Count']",
                    f".//*[local-name()='{section_name}']/*[local-name()='Number']",
                    f".//*[local-name()='{item_name}Count']",
                    f".//*[local-name()='Number{item_name}s']",
                ],
            ),
            _attribute_value(root, fallback_attribute),
        ]
    )


def _find_elements(
    root: etree._Element,
    section_names: tuple[str, ...],
    element_names: tuple[str, ...],
) -> list[etree._Element]:
    """Find elements under the given section names while ignoring namespaces."""

    results: list[etree._Element] = []
    seen: set[int] = set()
    for section in _matching_descendants(root, section_names):
        for match in _matching_descendants(section, element_names):
            marker = id(match)
            if marker not in seen:
                seen.add(marker)
                results.append(match)
    return results


def _first_text(root: etree._Element, expressions: list[str]) -> str | None:
    """Return the first non-empty text value produced by the given XPaths."""

    for expression in expressions:
        values = root.xpath(expression)
        text = _coerce_xpath_result(values)
        if text:
            return text
    return None


def _coerce_xpath_result(value: object) -> str | None:
    """Normalize an XPath result into plain text if possible."""

    if isinstance(value, list):
        for item in value:
            text = _coerce_xpath_result(item)
            if text:
                return text
        return None
    if isinstance(value, etree._Element):
        return _normalize_text(value.text)
    if value is None:
        return None
    return _normalize_text(str(value))


def _attribute_value(element: etree._Element, attribute_name: str) -> str | None:
    """Return a normalized attribute value if present."""

    return _normalize_text(element.get(attribute_name))


def _read_text_field(source: object, field_name: str) -> str | None:
    """Read a text-like field from an object or mapping."""

    if source is None:
        return None

    value: object | None
    if isinstance(source, dict):
        value = source.get(field_name)
    else:
        value = getattr(source, field_name, None)

    if value is None:
        return None
    return _normalize_text(str(value))


def _first_non_empty(values: Iterable[str | None]) -> str | None:
    """Return the first non-empty string from an iterable of candidates."""

    for value in values:
        if value:
            return value
    return None


def _first_integer(values: Iterable[str | None]) -> int | None:
    """Return the first value that can be parsed as an integer."""

    for value in values:
        if value is None:
            continue
        try:
            return int(value)
        except ValueError:
            continue
    return None


def _extract_boolean(values: Iterable[str | None]) -> bool | None:
    """Return the first value that can be interpreted as a boolean."""

    for value in values:
        if value is None:
            continue
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def _normalize_text(value: str | None) -> str | None:
    """Strip whitespace and collapse empty strings to ``None``."""

    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _matching_descendants(
    root: etree._Element,
    names: tuple[str, ...],
) -> list[etree._Element]:
    """Return descendant elements whose local name matches any expected name."""

    expected_names = {name.casefold() for name in names}
    matches: list[etree._Element] = []
    for element in root.iterdescendants():
        if _element_name_matches(element, expected_names):
            matches.append(element)
    return matches


def _element_name_matches(element: etree._Element, expected_names: set[str]) -> bool:
    """Return whether one XML element matches any expected local name."""

    local_name = _element_local_name(element)
    return local_name is not None and local_name.casefold() in expected_names


def _element_local_name(element: etree._Element | None) -> str | None:
    """Return one element's local XML name while ignoring namespaces."""

    if element is None or not isinstance(element.tag, str):
        return None
    try:
        return _normalize_text(etree.QName(element).localname)
    except ValueError:
        return _normalize_text(str(element.tag))


def _find_grouped_constraint_elements(root: etree._Element) -> list[etree._Element]:
    """Find RobinX / ITC2021-style grouped constraint elements."""

    constraint_sections = _matching_descendants(root, ("Constraints",))
    results: list[etree._Element] = []
    seen: set[int] = set()

    for section in constraint_sections:
        for child in section:
            child_name = _element_local_name(child)
            if child_name is None:
                continue
            normalized = child_name.casefold()
            if normalized == "constraint":
                marker = id(child)
                if marker not in seen:
                    seen.add(marker)
                    results.append(child)
                continue
            if normalized.endswith("constraints"):
                for grandchild in child:
                    marker = id(grandchild)
                    if marker not in seen:
                        seen.add(marker)
                        results.append(grandchild)

    return results


def _constraint_category_from_parent(parent: etree._Element | None) -> str | None:
    """Infer a constraint category from the parent grouped-constraint section."""

    parent_name = _element_local_name(parent)
    if parent_name is None:
        return None
    if parent_name.casefold().endswith("constraints") and len(parent_name) > len("constraints"):
        return parent_name[: -len("Constraints")]
    return None


def _constraint_tag_from_element(element: etree._Element) -> str | None:
    """Infer a fallback constraint tag only for non-generic element names."""

    local_name = _element_local_name(element)
    if local_name is None or local_name.casefold() == "constraint":
        return None
    return local_name
