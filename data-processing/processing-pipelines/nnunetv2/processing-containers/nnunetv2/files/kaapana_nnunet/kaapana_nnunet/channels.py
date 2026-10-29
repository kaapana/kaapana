"""Channel rules: which series of a study is input channel N.

A rule is ``segmented`` (the series the segmentation was drawn on) or conditions joined by ``&``::

    SeriesDescription ~ t2           regular expression, case-insensitive search
    Modality = MR                    equals, case-insensitive (for lists: one element equals)
    Tags = adc                       Kaapana tags work like any other field
    ImageType != DERIVED             does not equal

Fields are DICOM keywords as stored in the Kaapana metadata index (OpenSearch).
"""

import re
from dataclasses import dataclass, field

SEGMENTED = "segmented"
NNUNET_NORMALIZATIONS = ("CT", "zscore", "noNorm", "rescale_to_0_1", "rgb_to_0_1")
_COND_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*(!=|=|~)\s*(.*?)\s*$")


class RuleError(Exception):
    pass


@dataclass
class Condition:
    field: str
    op: str
    value: str

    def matches(self, meta: dict) -> bool:
        values = [str(v) for v in field_values(meta, self.field)]
        if self.op == "~":
            pattern = re.compile(self.value, re.IGNORECASE)
            return any(pattern.search(v) for v in values)
        equal = any(v.strip().lower() == self.value.lower() for v in values)
        return equal if self.op == "=" else not equal


@dataclass
class Channel:
    name: str
    rule: str
    normalization: str = ""
    conditions: list[Condition] = field(default_factory=list)

    @property
    def is_segmented(self) -> bool:
        return self.rule.strip().lower() == SEGMENTED

    def matches(self, meta: dict) -> bool:
        return all(c.matches(meta) for c in self.conditions)


def field_values(meta: dict, name: str) -> list:
    """Values of DICOM keyword ``name`` in an OpenSearch metadata document ("<tag> <Keyword>_<type>")."""
    wanted = name.lower()
    for key, value in meta.items():
        keyword = key.split(" ", 1)[-1].rsplit("_", 1)[0]
        if keyword.lower() == wanted:
            return value if isinstance(value, list) else [value]
    return []


def parse_channels(rows: list[dict]) -> list[Channel]:
    """Form rows [{name, rule, normalization}] -> channels. No rows = one channel: the segmented series."""
    if not rows:
        return [Channel(name="", rule=SEGMENTED)]
    channels, errors = [], []
    for n, row in enumerate(rows):
        name = str(row.get("name") or "").strip()
        rule = str(row.get("rule") or "").strip() or SEGMENTED
        norm = str(row.get("normalization") or "").strip()
        if not name:
            errors.append(f"channel {n}: a name is required")
        if norm and norm not in NNUNET_NORMALIZATIONS:
            errors.append(f"channel {n} ({name}): normalization must be one of {', '.join(NNUNET_NORMALIZATIONS)}")
        channel = Channel(name=name, rule=rule, normalization=norm)
        if not channel.is_segmented:
            for part in rule.split("&"):
                m = _COND_RE.match(part)
                if not m:
                    errors.append(f"channel {n} ({name}): cannot read the condition '{part.strip()}'")
                    continue
                cond = Condition(*m.groups())
                if cond.op == "~":
                    try:
                        re.compile(cond.value)
                    except re.error as e:
                        errors.append(f"channel {n} ({name}): invalid regular expression '{cond.value}': {e}")
                channel.conditions.append(cond)
        channels.append(channel)
    if sum(c.is_segmented for c in channels) > 1:
        errors.append("only one channel can use the rule 'segmented'")
    if len({c.name.lower() for c in channels}) != len(channels):
        errors.append("channel names must be unique")
    if errors:
        raise RuleError("\n".join(errors))
    return channels


def describe_series(meta: dict) -> str:
    """'#<SeriesNumber> <SeriesDescription>', how users recognise a series in the viewer."""
    number = field_values(meta, "SeriesNumber")
    description = field_values(meta, "SeriesDescription")
    return f"#{number[0] if number else '?'} {description[0] if description else '(no description)'}"


def assign(
    channels: list[Channel], segmented_uid: str, study_series: list[dict], series_uid_of, describe=None
) -> list[str]:
    """Series UID per channel for one case. Raises RuleError when a rule matches no or several series;
    ``describe(meta)`` names the series in that message (default: the UID)."""
    describe = describe or series_uid_of
    picked, problems = [], []
    for c in channels:
        if c.is_segmented:
            picked.append(segmented_uid)
            continue
        hits = [m for m in study_series if c.matches(m)]
        if len(hits) == 1:
            picked.append(series_uid_of(hits[0]))
        elif hits:
            problems.append(
                f"channel '{c.name}' ({c.rule}) matches {len(hits)} series: " + ", ".join(describe(m) for m in hits)
            )
        else:
            problems.append(
                f"channel '{c.name}' ({c.rule}) matches no series; the study has: "
                + ", ".join(describe(m) for m in study_series)
            )
    if len(set(picked)) != len(picked) and not problems:
        problems.append("two channels picked the same series")
    if problems:
        raise RuleError("; ".join(problems))
    return picked


def nnunet_channel_name(channel: Channel, modalities: set[str]) -> str:
    """dataset.json channel_names value. nnU-Net picks the normalization from it: 'CT' = CT
    normalization, unknown names = z-score."""
    if channel.normalization:
        return channel.normalization
    if modalities == {"CT"}:
        return "CT"
    # a name that happens to be a normalization scheme must not silently select it
    if not channel.name or channel.name.lower() in {n.lower() for n in NNUNET_NORMALIZATIONS}:
        return "zscore"
    return channel.name
