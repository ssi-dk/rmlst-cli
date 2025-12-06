import os
import tempfile
from typing import List


def scan_directory(dir_path: str) -> List[str]:
    """
    Scans directory for .fa/.fasta files (case-insensitive).
    Returns sorted list of absolute paths.
    """
    if not os.path.isdir(dir_path):
        return []

    files = []
    for entry in os.scandir(dir_path):
        if entry.name.startswith("."):
            continue

        if entry.is_file() or entry.is_symlink():
            lower_name = entry.name.lower()
            if lower_name.endswith(".fa") or lower_name.endswith(".fasta"):
                files.append(os.path.abspath(entry.path))

    # Sort by basename
    files.sort(key=lambda p: os.path.basename(p))
    return files


def atomic_write(path: str, content: str):
    """
    Writes content to path atomically (write to temp, then rename).
    """
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # Create temp file in the same directory to ensure atomic rename works
    # mkstemp returns a low-level file handle (int) and the absolute path
    fd, temp_path = tempfile.mkstemp(dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, path)
    except Exception:
        # If something goes wrong, clean up the temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def derive_output_path(
    input_path: str, output_dir: str, suffix: str = "_rmlst.json"
) -> str:
    """
    Derives output filename: output_dir / basename_no_ext(input_path) + suffix.
    """
    base = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{base}{suffix}"
    return os.path.join(output_dir, filename)
