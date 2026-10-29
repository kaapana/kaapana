"""Rule engine of nnunetv2-harmonize-segmentations: the segments of one image series -> harmonized segments
that do not overlap.

Works on boolean masks (z, y, x) on the grid of the segmented image; sizes are in mm³, never in voxels, because
slices are often much thicker than pixels. The rule rows of the form can come in any order: they are applied in
fixed stages, so the result never depends on the order of the rows.

    1 choose version   several segmentation objects provide the same segment name: pick one (or unite them)
    2 rename           names (with * wildcards) -> one name; segments with the same name are united
    3 drop, keep only
    4 combine          the listed segments are replaced by their union under a new name
    5 cut out          the target loses the voxels of the listed segments
    6 remove specks    connected pieces (26-neighbourhood) smaller than a volume
    7 priority         where listed segments overlap, the earlier one keeps the voxels
    8 inner wins       (switch) a segment lying mostly inside another one keeps the shared voxels
    9 check            any overlap left over refuses the case: nothing is decided silently

No nnU-Net imports: the engine can move to a generic Kaapana workflow.
"""

import fnmatch
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

KINDS = {
    "choose_version": "choose version",
    "rename": "rename",
    "drop": "drop",
    "keep_only": "keep only",
    "combine": "combine",
    "cut_out": "cut out",
    "remove_specks": "remove specks",
    "priority": "priority",
}
STAGE = {kind: n for n, kind in enumerate(KINDS)}
VERSION_RE = re.compile(r"^\s*(newest|union|(description|author)\s*~\s*(.+?))\s*$", re.IGNORECASE)
INNER_FRACTION = 0.8  # 'inner wins': at least this part of the smaller segment lies inside the larger one
LOSS_WARNING = 0.1  # report segments that lost more than this part of their voxels after combining


class RuleError(Exception):
    pass


@dataclass
class Rule:
    row: int  # 1-based row in the form
    kind: str
    patterns: list[str]
    target: str = ""
    value: str = ""

    def matches(self, name: str) -> bool:
        return any(fnmatch.fnmatchcase(name.lower(), p.lower()) for p in self.patterns)

    def text(self) -> str:
        names = ", ".join(self.patterns)
        return {
            "choose_version": f"choose version of {names}: {self.value}",
            "rename": f"rename {names} -> {self.target}",
            "drop": f"drop {names}",
            "keep_only": f"keep only {names}",
            "combine": f"combine {names} -> {self.target}",
            "cut_out": f"cut out {names} from {self.target}",
            "remove_specks": f"remove specks < {self.value} mm³ from {names}",
            "priority": f"priority {' > '.join(self.patterns)}",
        }[self.kind]


def parse_rules(rows: list[dict]) -> list[Rule]:
    """Form rows [{rule, segments, target, value}] -> rules in stage order (row order within a stage)."""
    rules, errors = [], []
    for row_number, row in enumerate(rows, start=1):
        kind = str(row.get("rule") or "").strip()
        patterns = [p.strip() for p in str(row.get("segments") or "").split(",") if p.strip()]
        # a row keeps the fields of a rule type chosen earlier in the form: read only those of its own type
        target = str(row.get("target") or "").strip() if kind in ("rename", "combine", "cut_out") else ""
        value = str(row.get("value") or "").strip() if kind in ("choose_version", "remove_specks") else ""
        where = f"rule {row_number} ({KINDS.get(kind, kind or '?')})"
        if kind not in KINDS:
            errors.append(f"{where}: unknown rule, use one of {', '.join(KINDS)}")
            continue
        if not patterns:
            errors.append(f"{where}: 'Segments' is empty (use * for all)")
        if kind in ("rename", "combine", "cut_out") and not target:
            errors.append(f"{where}: the second name ('New name' or 'from') is empty")
        if kind == "choose_version":
            m = VERSION_RE.match(value)
            if not m:
                errors.append(f"{where}: 'Keep' must be newest, union, 'description ~ <regex>' or 'author ~ <regex>'")
            elif m.group(3):
                try:
                    re.compile(m.group(3))
                except re.error as e:
                    errors.append(f"{where}: invalid regular expression '{m.group(3)}': {e}")
        if kind == "remove_specks":
            try:
                if float(value) <= 0:
                    raise ValueError
            except ValueError:
                errors.append(f"{where}: 'Smallest piece to keep' must be a volume in mm³ greater than 0")
        if kind == "priority" and len(patterns) < 2:
            errors.append(f"{where}: list at least two segments, the first one wins")
        rules.append(Rule(row_number, kind, patterns, target, value))
    if errors:
        raise RuleError("\n".join(errors))
    return sorted(rules, key=lambda r: (STAGE[r.kind], r.row))


def rules_hash(rules: list[Rule]) -> str:
    canonical = json.dumps([[r.kind, r.patterns, r.target, r.value] for r in rules], separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class Source:
    """A segmentation object (DICOM SEG or RTSTRUCT)."""

    uid: str
    label: str  # how the user recognises it: "SEG #300 Liver manual (uid)"
    description: str = ""
    author: str = ""
    date: str = ""  # sortable, e.g. 20240131120000; empty if unknown


@dataclass
class Segment:
    name: str
    mask: np.ndarray
    source: str  # Source.uid
    codes: Optional[tuple] = None  # (category item, type item) of the original segment, if any


@dataclass
class Outcome:
    segments: dict[str, np.ndarray] = field(default_factory=dict)  # final name -> mask
    codes: dict[str, Optional[tuple]] = field(default_factory=dict)
    sources: dict[str, set] = field(default_factory=dict)  # final name -> source uids
    applied: set = field(default_factory=set)  # rows whose segments matched something in this case
    changed_mm3: Counter = field(default_factory=Counter)  # row -> volume added or removed
    notes: list[str] = field(default_factory=list)  # decisions the user should see (inner wins, losses)
    problems: list[str] = field(default_factory=list)  # non-empty: the case is refused


def _volume(mask: np.ndarray, voxel_mm3: float) -> float:
    return float(np.count_nonzero(mask)) * voxel_mm3


def apply(
    rules: list[Rule], segments: list[Segment], sources: dict[str, Source], spacing: tuple, inner_wins: bool = False
) -> Outcome:
    """Run the rules on the segments of one image series. ``spacing`` is (x, y, z) in mm as SimpleITK reports it."""
    out = Outcome()
    voxel_mm3 = float(np.prod(spacing))
    by_kind = {kind: [r for r in rules if r.kind == kind] for kind in KINDS}

    # 1 choose version
    by_name: dict[str, list[Segment]] = {}
    for s in segments:
        by_name.setdefault(s.name.lower(), []).append(s)
    kept: list[Segment] = []
    for group in by_name.values():
        objects = sorted({s.source for s in group})
        if len(objects) < 2:
            kept += group
            continue
        name = group[0].name
        rule = next((r for r in by_kind["choose_version"] if r.matches(name)), None)
        labels = ", ".join(sources[u].label for u in objects)
        if rule is None:
            out.problems.append(
                f"segment '{name}' comes from {len(objects)} segmentation objects ({labels}). "
                "Add a rule 'choose version' (newest, union, description ~ ..., author ~ ...)."
            )
            continue
        out.applied.add(rule.row)
        chosen = _choose(rule.value, [sources[u] for u in objects])
        if isinstance(chosen, str):
            out.problems.append(f"segment '{name}' ({labels}): rule {rule.row} {chosen}")
            continue
        kept += [s for s in group if s.source in chosen]
    if out.problems:
        return out

    # 2 rename, then unite segments with the same name
    names: dict[str, list[Segment]] = {}
    for s in kept:
        new = s.name
        for rule in by_kind["rename"]:
            if rule.matches(s.name):
                out.applied.add(rule.row)
                new = rule.target
                break
        names.setdefault(new.lower(), []).append(Segment(new, s.mask, s.source, s.codes))
    current: dict[str, np.ndarray] = {}
    for group in names.values():
        spelling = Counter(s.name for s in group).most_common(1)[0][0]
        current[spelling] = np.logical_or.reduce([s.mask for s in group])
        out.codes[spelling] = next((s.codes for s in group if s.codes), None)
        out.sources[spelling] = {s.source for s in group}

    def matching(rule, exclude=()):
        hits = [n for n in current if rule.matches(n) and n.lower() not in {e.lower() for e in exclude}]
        if hits:
            out.applied.add(rule.row)
        return hits

    def find(name):
        return next((n for n in current if n.lower() == name.lower()), None)

    # 3 drop, keep only
    for rule in by_kind["drop"]:
        for n in matching(rule):
            out.changed_mm3[rule.row] += _volume(current.pop(n), voxel_mm3)
    if by_kind["keep_only"]:
        keep = {n for rule in by_kind["keep_only"] for n in matching(rule)}
        for n in [n for n in current if n not in keep]:
            out.changed_mm3[by_kind["keep_only"][0].row] += _volume(current.pop(n), voxel_mm3)

    # 4 combine
    for rule in by_kind["combine"]:
        members = matching(rule)
        if not members:
            continue
        existing = find(rule.target)
        union = np.logical_or.reduce([current[n] for n in members] + ([current[existing]] if existing else []))
        merged_sources = set().union(*(out.sources.get(n, set()) for n in members + ([existing] if existing else [])))
        codes = next((out.codes.get(n) for n in members if out.codes.get(n)), None)
        for n in set(members + ([existing] if existing else [])):
            current.pop(n)
        current[rule.target] = union
        out.sources[rule.target], out.codes[rule.target] = merged_sources, codes

    before = {n: int(np.count_nonzero(m)) for n, m in current.items()}

    # 5 cut out
    for rule in by_kind["cut_out"]:
        target = find(rule.target)
        cutters = matching(rule, exclude=[rule.target])
        if target is None or not cutters:
            continue
        out.applied.add(rule.row)
        cut = current[target] & np.logical_or.reduce([current[n] for n in cutters])
        out.changed_mm3[rule.row] += _volume(cut, voxel_mm3)
        current[target] = current[target] & ~cut

    # 6 remove specks
    for rule in by_kind["remove_specks"]:
        min_voxels = float(rule.value) / voxel_mm3
        for n in matching(rule):
            cleaned = _remove_small(current[n], min_voxels)
            out.changed_mm3[rule.row] += _volume(current[n] & ~cleaned, voxel_mm3)
            current[n] = cleaned

    # 7 priority: earlier names keep contested voxels
    for rule in by_kind["priority"]:
        order = []
        for pattern in rule.patterns:
            order += [n for n in sorted(current) if fnmatch.fnmatchcase(n.lower(), pattern.lower()) and n not in order]
        if len(order) > 1:
            out.applied.add(rule.row)
        for i, winner in enumerate(order):
            for loser in order[i + 1 :]:
                shared = current[winner] & current[loser]
                if shared.any():
                    out.changed_mm3[rule.row] += _volume(shared, voxel_mm3)
                    current[loser] = current[loser] & ~shared

    # 8 inner wins (switch): smaller structures first, so nested ones (zone in gland in body) resolve inside out
    def inside(a, b):
        """(smaller, larger, part of the smaller one inside the larger one)"""
        small, large = sorted((a, b), key=lambda n: (np.count_nonzero(current[n]), n))
        part = np.count_nonzero(current[small] & current[large]) / max(1, np.count_nonzero(current[small]))
        return small, large, part

    if inner_wins:
        for a, b, _ in sorted(_overlaps(current), key=lambda p: min(np.count_nonzero(current[n]) for n in p[:2])):
            small, large, part = inside(a, b)
            shared = current[small] & current[large]
            if part >= INNER_FRACTION and shared.any():
                current[large] = current[large] & ~shared
                out.notes.append(
                    f"inner wins: '{small}' lies {part:.0%} inside '{large}', "
                    f"{_volume(shared, voxel_mm3):.0f} mm³ went to '{small}'"
                )

    # 9 check: whatever still overlaps refuses the case
    for a, b, shared in _overlaps(current):
        small, large, part = inside(a, b)
        hint = f" ({part:.0%} of '{small}' lies inside '{large}', 'Inner structure wins' needs {INNER_FRACTION:.0%})"
        out.problems.append(
            f"OVERLAP: '{a}' and '{b}' share {shared} voxels ({shared * voxel_mm3:.0f} mm³)"
            + (hint if inner_wins else "")
            + f". Add a rule 'priority' ({small}, {large}) or 'cut out', or enable 'Inner structure wins'."
        )

    for n, mask in list(current.items()):
        count = int(np.count_nonzero(mask))
        if n in before and before[n] and count < (1 - LOSS_WARNING) * before[n]:
            empty = " (now empty)" if not count else ""
            out.notes.append(f"'{n}' lost {1 - count / before[n]:.0%} of its voxels{empty}")
        if not count:
            current.pop(n)
    out.segments = current
    out.codes = {n: out.codes.get(n) for n in current}
    out.sources = {n: out.sources.get(n, set()) for n in current}
    return out


def _choose(value: str, candidates: list[Source]):
    """The sources to keep, or an error text."""
    m = VERSION_RE.match(value)
    if m.group(1).lower() == "union":
        return {c.uid for c in candidates}
    if m.group(1).lower() == "newest":
        dated = sorted((c.date, c.uid) for c in candidates)
        if not dated[-1][0] or (len(dated) > 1 and dated[-1][0] == dated[-2][0]):
            return "cannot tell which one is newest (missing or equal dates)"
        return {dated[-1][1]}
    attribute, pattern = m.group(2).lower(), re.compile(m.group(3), re.IGNORECASE)
    hits = [c.uid for c in candidates if pattern.search(getattr(c, attribute) or "")]
    if len(hits) != 1:
        return f"'{value}' matches {len(hits)} of them, it must match exactly one"
    return set(hits)


def _remove_small(mask: np.ndarray, min_voxels: float) -> np.ndarray:
    from scipy import ndimage

    labelled, n = ndimage.label(mask, structure=np.ones((3, 3, 3), bool))
    if not n:
        return mask
    sizes = np.bincount(labelled.ravel())
    small = np.flatnonzero(sizes < min_voxels)
    small = small[small != 0]
    return mask & ~np.isin(labelled, small)


def _overlaps(current: dict[str, np.ndarray]):
    """[(a, b, shared voxels)] for every pair of segments that share voxels."""
    if len(current) < 2:
        return []
    names = sorted(current)
    count = np.zeros(next(iter(current.values())).shape, np.uint16)
    for n in names:
        count += current[n]
    contested = count > 1
    if not contested.any():
        return []
    picked = {n: current[n][contested] for n in names}
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = int(np.count_nonzero(picked[a] & picked[b]))
            if shared:
                pairs.append((a, b, shared))
    return pairs
