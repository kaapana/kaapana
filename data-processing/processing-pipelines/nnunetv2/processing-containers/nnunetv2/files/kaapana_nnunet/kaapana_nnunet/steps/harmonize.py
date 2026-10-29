"""Segmentations of a Kaapana dataset -> one harmonized DICOM SEG per image series, in a new Kaapana dataset.

The originals stay untouched. The rules (kaapana_nnunet/harmonize.py) rename, drop, combine and cut segments
and resolve overlaps; an overlap no rule resolves refuses the series. The result can be checked in the viewer
next to the original and is what nnunetv2-create-dataset reads.
"""

import json
import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from pydicom.uid import generate_uid

from kaapana_nnunet import channels as ch
from kaapana_nnunet import dicom, sources
from kaapana_nnunet import harmonize as hz
from kaapana_nnunet.context import Context, StepError, provenance
from kaapana_nnunet.pacs import check_aetitle, send_to_pacs
from kaapana_nnunet.sources import MODALITY, STUDY

logger = logging.getLogger(__name__)

DOCS = "/docs/user_guide/extensions/nnunet.html"
HELP = {"rules": f"{DOCS}#harmonize-rules", "report": f"{DOCS}#reading-the-harmonize-report"}
CONTENT_LABEL = "HARMONIZED"
SERIES_NUMBER = 901


def _source(uid: str, ds, meta: dict) -> hz.Source:
    date = ""
    for prefix in ("Content", "Series", "StructureSet"):
        if ds.get(f"{prefix}Date"):
            date = f"{ds.get(f'{prefix}Date')}{ds.get(f'{prefix}Time', '')}".split(".")[0]
            break
    return hz.Source(
        uid=uid,
        label=f"{ds.Modality} {ch.describe_series(meta)} ({uid})",
        description=str(ds.get("SeriesDescription", "")),
        author=str(ds.get("ContentCreatorName", "")),
        date=date,
    )


def run(ctx: Context):
    aetitle = str(ctx.require("aetitle")).strip()
    check_aetitle(aetitle)
    try:
        rules = hz.parse_rules(ctx.get("rules") or [])
    except hz.RuleError as e:
        raise StepError(f"Rule problems:\n{e}\nSee {HELP['rules']}")
    inner_wins = ctx.flag("inner_wins")
    check_only = ctx.flag("check_only")
    skip_invalid = ctx.flag("skip_invalid_cases")
    rhash = hz.rules_hash(rules) + ("-inner" if inner_wins else "")

    identifiers = ctx.identifiers
    if not identifiers:
        raise StepError("The selected Kaapana dataset is empty.")
    meta = sources.Metadata(ctx.project["opensearch_index"])
    series_meta = meta.series(identifiers)
    seg_uids = [uid for uid, m in series_meta.items() if m.get(MODALITY) in dicom.SEG_MODALITIES]
    if not seg_uids:
        raise StepError("The dataset contains no DICOM SEG or RTSTRUCT.")
    download = sources.downloader(ctx.scratch / "dicom")

    # segmentation objects -> the image series they were drawn on
    cases: dict[str, dict] = {}
    problems, skipped = [], []

    def load(uid):
        m = series_meta[uid]
        try:
            return uid, m, dicom.read_segmentation_object(download(uid, m[STUDY])), None
        except Exception as e:  # a broken object is a problem of the data, not a crash
            return uid, m, None, e

    with ThreadPoolExecutor(8) as pool:
        for uid, m, ds, error in pool.map(load, seg_uids):
            label = f"{m.get(MODALITY)} {ch.describe_series(m)} ({uid})"
            if error is not None:
                problems.append(f"{label}: cannot be read: {error}")
                continue
            if str(ds.get("ContentLabel", "")) == CONTENT_LABEL:
                skipped.append(label)  # an earlier result of this workflow
                continue
            ref = dicom.referenced_series_uid(ds)
            if not ref:
                problems.append(f"{label}: does not reference an image series")
                continue
            case = cases.setdefault(ref, {"study": m[STUDY], "objects": []})
            case["objects"].append((uid, ds, _source(uid, ds, m)))
    if not cases:
        earlier = f" Skipped earlier results: {len(skipped)}." if skipped else ""
        raise StepError("No segmentation to harmonize." + earlier)

    out_dir = ctx.scratch / "harmonized"

    def harmonize_case(item):
        ref, case = item
        image, files = dicom.read_image_series(download(ref, case["study"]), with_files=True)
        segments, objects = [], {}
        for uid, ds, source in case["objects"]:
            objects[uid] = source
            codes = dicom.segment_codes(ds)
            for name, mask in dicom.segment_masks(ds, image).items():
                segments.append(hz.Segment(name, mask, uid, codes.get(name)))
        outcome = hz.apply(rules, segments, objects, image.GetSpacing(), inner_wins)
        written = None
        if not outcome.problems and outcome.segments and not check_only:
            first = objects[sorted(objects)[0]]
            entropy = [ref, rhash, *sorted(objects)]
            series_uid = generate_uid(entropy_srcs=[*entropy, "series"])
            segs = [
                dicom.SegSegment(n, m, *(outcome.codes.get(n) or (None, None)))
                for n, m in sorted(outcome.segments.items())
            ]
            description = ctx.get("seg_description") or f"Harmonized {first.description or 'segmentation'}"
            dicom.write_seg_segments(
                segs,
                files,
                out_dir / ref / "seg.dcm",
                description,
                algorithm=f"Kaapana harmonize {rhash[:8]}",
                algorithm_type="SEMIAUTOMATIC",
                series_uid=series_uid,
                sop_uid=generate_uid(entropy_srcs=[*entropy, "instance"]),
                series_number=SERIES_NUMBER,
                content_label=CONTENT_LABEL,
                content_description=f"rules {rhash[:8]}, {len(objects)} sources"[:64],
            )
            written = series_uid
        return outcome, image.GetSpacing(), written

    results = {}
    with ThreadPoolExecutor(4) as pool:
        futures = {pool.submit(harmonize_case, item): item for item in sorted(cases.items())}
        for future, (ref, case) in futures.items():
            try:
                results[ref] = future.result()
            except (dicom.ConversionError, RuntimeError) as e:
                problems.append(f"series {ref}: {e}")

    # rules whose segments match nothing anywhere are almost always typos
    applied = Counter(row for outcome, _, _ in results.values() for row in outcome.applied)
    fatal = [
        f"rule {r.row} ({r.text()}) matches no segment in any series (typo?)"
        for r in rules
        if not applied[r.row] and r.kind != "choose_version"
    ]
    refused = {ref: o for ref, (o, _, _) in results.items() if o.problems}
    for ref, outcome in refused.items():
        problems += [f"series {ref}: {p}" for p in outcome.problems]
    ok = {ref: r for ref, r in results.items() if ref not in refused}

    report = [
        f"Harmonize: {len(cases)} image series, {sum(len(c['objects']) for c in cases.values())} segmentation objects"
        + (f" ({len(skipped)} earlier results skipped)" if skipped else ""),
        f"Result:    {len(ok)} series" + ("" if check_only else f" -> Kaapana dataset '{aetitle}'"),
        "Rules (applied in this order):",
    ]
    changed = Counter()
    for outcome, _, _ in results.values():
        changed.update(outcome.changed_mm3)
    for r in rules:
        effect = f", {changed[r.row] / 1000:.1f} ml changed" if changed[r.row] else ""
        report.append(f"  {r.row:>2} {r.text()}: matched in {applied[r.row]} of {len(results)} series{effect}")
    if inner_wins:
        report.append(f"     inner structure wins (>= {hz.INNER_FRACTION:.0%} inside)")
    report.append("Segments:")
    volumes, present = Counter(), Counter()
    for outcome, spacing, _ in ok.values():
        voxel = float(spacing[0] * spacing[1] * spacing[2])
        for n, m in outcome.segments.items():
            present[n] += 1
            volumes[n] += int(m.sum()) * voxel
    for n in sorted(present):
        report.append(f"  {n}: in {present[n]} of {len(ok)} series, {volumes[n] / 1000:.1f} ml in total")
    notes = [f"series {ref}: {note}" for ref, (o, _, _) in ok.items() for note in o.notes]
    if notes:
        report += ["Decisions and losses to check:", *[f"  {n}" for n in notes]]
    if fatal or problems:
        report += ["", f"Problems ({len(fatal) + len(problems)}):", *fatal, *problems]
        report += ["", f"Help: rules {HELP['rules']} | this report {HELP['report']}"]
    print("\n".join(report), flush=True)

    if fatal or (problems and not (skip_invalid and ok)):
        raise StepError(
            f"{len(fatal) + len(problems)} problem(s), see the report above. Nothing was sent."
            + ("" if fatal else " Fix the rules or the data, or enable 'Skip invalid series'.")
        )
    if check_only:
        print("\nCheck only: nothing was sent.", flush=True)
        return

    record = ctx.scratch / "record"
    record.mkdir(parents=True, exist_ok=True)
    (record / "report.txt").write_text("\n".join(report) + "\n")
    (record / "rules.json").write_text(
        json.dumps({"rules": [r.__dict__ for r in rules], "inner_wins": inner_wins, "hash": rhash}, indent=2)
    )
    (record / "provenance.json").write_text(
        json.dumps(
            {
                ref: {
                    "output_series": written,
                    "sources": sorted({u for s in o.sources.values() for u in s}),
                    "segments": {n: sorted(o.sources[n]) for n in o.segments},
                }
                for ref, (o, _, written) in ok.items()
            },
            indent=2,
        )
    )
    send_to_pacs(ctx, out_dir, aetitle)
    unit = re.sub(r"[^A-Za-z0-9_.-]", "_", ctx.run_id)
    ctx.store.publish(record, f"harmonize/{aetitle}", unit=unit, meta=provenance(ctx, series=len(ok)))
    print(f"\nSent {len(ok)} SEG(s) to the Kaapana dataset '{aetitle}'; record in nnunet/harmonize/{aetitle}/.")
