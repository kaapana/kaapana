"""Pure menu assembly: parses `kaapana.ai/ui.*` ingress annotations into a MenuResponse.

Deliberately free of kubernetes imports so unit tests run without the k8s client;
`ingress_source` is the only module that talks to the API server.

Annotation contract — `_KNOWN_KEYS` below is the complete set, and any other
`kaapana.ai/ui.*` key is ignored with a WARNING. An ingress joins the menu iff it
carries the `ui.name` key, the only required one. The first eleven keys describe
the entry; the last three describe the section it declares and are read from every
member of that section, including members whose own entry was skipped.

  key            req  accepted value              absent or invalid
  -------------  ---  --------------------------  -----------------------------------
  name           yes  non-blank text              entry skipped
  path            -   platform-relative path      the ingress' first rule path; if
                                                  that is unusable, entry skipped
  id              -   any text, used verbatim     slugified `name`; a duplicate
                                                  (section, id) skips the entry
  section         -   section id                  entry sits at the menu's top level
  icon            -   mdi-* name                  ""
  order           -   integer                     1000
  target          -   "iframe" | "tab"            "iframe"  (value NOT stripped)
  project         -   "path" | "none"             "none"    (value NOT stripped)
  default         -   "true", case-insensitive    false; see the determinism rules
  badge-path      -   platform-relative path      ""
  dev-links       -   "Label=/p,Other=/p2"        the offending pair is dropped
  section-label   -   display label               section id, first character upcased
  section-icon    -   mdi-* name                  ""
  section-order   -   integer                     1000, which then counts in the min

"Platform-relative path" is stricter than a leading slash: `_is_platform_relative`
also rejects "//host", "/\\host" and tab/newline/CR-smuggled authorities. Every
value is whitespace-stripped except `target` and `project`.

Determinism rules (all "smallest" = lexicographic (namespace, name)):
- duplicate (section, id) pairs: smallest ingress kept, WARNING for the rest
- `ui.default` on >1 entry: only the smallest keeps default=true, WARNING for the rest
  (platform-wide, not per section)
- section metadata: per field, first non-empty value from the smallest declaring ingress;
  section order = numeric minimum over the declared values, an unparseable one
  counting as 1000
Malformed annotations never fail the whole menu: WARNING + default or entry skip.
"""

import logging
import re
from dataclasses import dataclass, field

from app.models import DevLink, MenuEntry, MenuResponse, MenuSection

logger = logging.getLogger(__name__)

ANNOTATION_PREFIX = "kaapana.ai/ui."
DEFAULT_ORDER = 1000

_KNOWN_KEYS = {
    "name",
    "id",
    "section",
    "icon",
    "order",
    "path",
    "target",
    "default",
    "project",
    "badge-path",
    "dev-links",
    "section-label",
    "section-icon",
    "section-order",
}


@dataclass(frozen=True)
class IngressInfo:
    namespace: str
    name: str
    annotations: dict[str, str] = field(default_factory=dict)
    first_path: str | None = None


def _ann(key: str) -> str:
    return ANNOTATION_PREFIX + key


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _parse_order(raw: str | None, key: str, source: str) -> int:
    if raw is None:
        return DEFAULT_ORDER
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning(
            "ingress %s: %s=%r is not an integer, using %d",
            source,
            _ann(key),
            raw,
            DEFAULT_ORDER,
        )
        return DEFAULT_ORDER


def _is_platform_relative(path: str) -> bool:
    """A leading slash alone is not enough: the browser's URL parser strips ASCII
    tab/newline/CR before parsing and treats "\\" like "/" for special schemes,
    so "//host", "/\\host" and "/<tab>/host" all resolve to another origin."""
    cleaned = path.replace("\t", "").replace("\n", "").replace("\r", "")
    return cleaned.startswith("/") and (len(cleaned) < 2 or cleaned[1] not in "/\\")


def _parse_dev_links(raw: str | None, source: str) -> list[DevLink]:
    """Parse "Label=/path,Other=/other" — annotations are flat, hence one key."""
    if raw is None or not raw.strip():
        return []
    links = []
    for pair in raw.split(","):
        label, _, path = pair.partition("=")
        label, path = label.strip(), path.strip()
        if not label or not _is_platform_relative(path):
            logger.warning(
                "ingress %s: %s pair %r is not 'Label=/path', skipped",
                source,
                _ann("dev-links"),
                pair,
            )
            continue
        links.append(DevLink(label=label, path=path))
    return links


def _warn_unknown_keys(ingress: IngressInfo, source: str) -> None:
    for key in ingress.annotations:
        if (
            key.startswith(ANNOTATION_PREFIX)
            and key.removeprefix(ANNOTATION_PREFIX) not in _KNOWN_KEYS
        ):
            logger.warning("ingress %s: unknown ui annotation %s, ignored", source, key)


def _parse_entry(ingress: IngressInfo, source: str) -> MenuEntry | None:
    ann = ingress.annotations

    label = ann.get(_ann("name"), "").strip()
    if not label:
        logger.warning("ingress %s: empty %s, entry skipped", source, _ann("name"))
        return None

    path = ann.get(_ann("path"), "").strip()
    if path and not _is_platform_relative(path):
        logger.warning(
            "ingress %s: %s=%r is not a platform-relative path, falling back to rule path",
            source,
            _ann("path"),
            path,
        )
        path = ""
    if not path:
        path = ingress.first_path or ""
    if not path or not _is_platform_relative(path):
        logger.warning(
            "ingress %s: no valid ui.path and no usable rule path, entry skipped",
            source,
        )
        return None

    entry_id = ann.get(_ann("id"), "").strip() or _slugify(label)
    if not entry_id:
        logger.warning(
            "ingress %s: ui.name %r slugifies to nothing, entry skipped", source, label
        )
        return None

    target = ann.get(_ann("target"), "iframe")
    if target not in ("iframe", "tab"):
        logger.warning(
            "ingress %s: unknown %s=%r, using 'iframe'", source, _ann("target"), target
        )
        target = "iframe"

    project = ann.get(_ann("project"), "none")
    if project not in ("path", "none"):
        logger.warning(
            "ingress %s: unknown %s=%r, using 'none'", source, _ann("project"), project
        )
        project = "none"

    badge_path = ann.get(_ann("badge-path"), "").strip()
    if badge_path and not _is_platform_relative(badge_path):
        logger.warning(
            "ingress %s: %s=%r is not a platform-relative path, ignored",
            source,
            _ann("badge-path"),
            badge_path,
        )
        badge_path = ""

    return MenuEntry(
        id=entry_id,
        label=label,
        icon=ann.get(_ann("icon"), "").strip(),
        path=path,
        target=target,
        project=project,
        default=ann.get(_ann("default"), "").strip().lower() == "true",
        order=_parse_order(ann.get(_ann("order")), "order", source),
        badgePath=badge_path,
        devLinks=_parse_dev_links(ann.get(_ann("dev-links")), source),
    )


def _first_nonempty(declarers: list[tuple[str, IngressInfo]], key: str) -> str:
    for _, ingress in declarers:
        value = ingress.annotations.get(_ann(key), "").strip()
        if value:
            return value
    return ""


def _section_order(declarers: list[tuple[str, IngressInfo]]) -> int:
    orders = [
        _parse_order(
            ingress.annotations[_ann("section-order")], "section-order", source
        )
        for source, ingress in declarers
        if _ann("section-order") in ingress.annotations
    ]
    return min(orders) if orders else DEFAULT_ORDER


def build_menu(ingresses: list[IngressInfo]) -> MenuResponse:
    # (namespace, name) order up front makes every "smallest wins" rule a "first wins".
    ordered = sorted(ingresses, key=lambda i: (i.namespace, i.name))

    entries: list[tuple[str | None, MenuEntry]] = []
    section_declarers: dict[str, list[tuple[str, IngressInfo]]] = {}
    seen_ids: set[tuple[str | None, str]] = set()

    for ingress in ordered:
        if _ann("name") not in ingress.annotations:
            continue
        source = f"{ingress.namespace}/{ingress.name}"
        _warn_unknown_keys(ingress, source)

        section_id = ingress.annotations.get(_ann("section"), "").strip() or None
        if section_id:
            section_declarers.setdefault(section_id, []).append((source, ingress))

        entry = _parse_entry(ingress, source)
        if entry is None:
            continue
        if (section_id, entry.id) in seen_ids:
            logger.warning(
                "ingress %s: duplicate menu id %r in section %r, entry skipped",
                source,
                entry.id,
                section_id,
            )
            continue
        seen_ids.add((section_id, entry.id))
        entries.append((section_id, entry))

    default_seen = False
    for section_id, entry in entries:
        if entry.default:
            if default_seen:
                logger.warning(
                    "entry %r in section %r: ui.default already claimed, cleared",
                    entry.id,
                    section_id,
                )
                entry.default = False
            default_seen = True

    sort_key = lambda item: (item.order, item.label)  # noqa: E731

    top_level: list[MenuSection | MenuEntry] = [e for s, e in entries if s is None]
    grouped: dict[str, list[MenuEntry]] = {}
    for section_id, entry in entries:
        if section_id:
            grouped.setdefault(section_id, []).append(entry)

    for section_id, section_entries in grouped.items():
        declarers = section_declarers[section_id]
        top_level.append(
            MenuSection(
                id=section_id,
                label=_first_nonempty(declarers, "section-label")
                or section_id[:1].upper() + section_id[1:],
                icon=_first_nonempty(declarers, "section-icon"),
                order=_section_order(declarers),
                entries=sorted(section_entries, key=sort_key),
            )
        )

    return MenuResponse(items=sorted(top_level, key=sort_key))
