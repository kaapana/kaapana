"""
Build-time patch applied to a freshly-cloned, unmodified copy of the official
TRIDENT repo (https://github.com/mahmoodlab/trident) to register the new
DicomWSI reader backend (see DicomWSI.py, copied into trident/wsi_objects/
by the Dockerfile before this script runs).

Uses regex substitution against the *shape* of WSIFactory.py's reader-type
lists/dispatch (not an exact snapshot) - TRIDENT is actively adding new reader
backends upstream (e.g. 'omezarr', 'czi' were added after this was first
written), so matching "insert 'dicom' into whatever Literal[...]/assert [...]
list currently exists" is far more robust across TRIDENT_GIT_REF bumps than
matching one exact historical string.

Usage: python3 apply_patch.py <path-to-WSIFactory.py>
"""
import re
import sys
from pathlib import Path

IMPORT_MARKER = "from trident.wsi_objects.SDPCWSI import SDPCWSI"
IMPORT_ADDITION = "from trident.wsi_objects.DicomWSI import DicomWSI"

LITERAL_PATTERN = re.compile(r"(WSIReaderType\s*=\s*Literal\[)([^\]]*)(\])")
ASSERT_PATTERN = re.compile(r"(assert reader_type in \[)([^\]]*)(\])")

DISPATCH_MARKER = "    elif reader_type is None:"
DISPATCH_ADDITION = (
    "    elif reader_type == 'dicom':\n"
    "        return DicomWSI(slide_path=slide_path, lazy_init=lazy_init, **kwargs)\n\n"
)


def fail(reason: str) -> None:
    sys.stderr.write(
        f"[apply_patch.py] FAILED to patch WSIFactory.py: {reason}\n"
        "The pinned TRIDENT_GIT_REF's WSIFactory.py no longer matches the shape "
        "this patch was written against - update dicom_wsi_patch/apply_patch.py.\n"
    )
    sys.exit(1)


def _add_dicom_to_list(match: re.Match) -> str:
    items = match.group(2)
    if "'dicom'" in items:
        return match.group(0)
    return f"{match.group(1)}{items}, 'dicom'{match.group(3)}"


def main() -> None:
    if len(sys.argv) != 2:
        fail("expected exactly one argument: path to WSIFactory.py")

    path = Path(sys.argv[1])
    text = path.read_text()

    if IMPORT_ADDITION in text:
        print("[apply_patch.py] WSIFactory.py already patched, nothing to do.")
        return

    if IMPORT_MARKER not in text:
        fail(f"import marker not found: {IMPORT_MARKER!r}")
    if DISPATCH_MARKER not in text:
        fail(f"dispatch marker not found: {DISPATCH_MARKER!r}")

    text, n_literal = LITERAL_PATTERN.subn(_add_dicom_to_list, text, count=1)
    if n_literal == 0:
        fail("no 'WSIReaderType = Literal[...]' assignment found")

    text, n_assert = ASSERT_PATTERN.subn(_add_dicom_to_list, text, count=1)
    if n_assert == 0:
        fail("no 'assert reader_type in [...]' statement found")

    text = text.replace(IMPORT_MARKER, f"{IMPORT_MARKER}\n{IMPORT_ADDITION}", 1)
    text = text.replace(DISPATCH_MARKER, DISPATCH_ADDITION + DISPATCH_MARKER, 1)

    path.write_text(text)
    print("[apply_patch.py] WSIFactory.py patched: 'dicom' reader_type registered.")


if __name__ == "__main__":
    main()
