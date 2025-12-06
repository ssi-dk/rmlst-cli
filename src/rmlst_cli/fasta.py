import re
from typing import List, Tuple
from Bio import SeqIO


class InvalidFastaError(Exception):
    """Raised when FASTA file is invalid or contains invalid characters."""

    pass


class TooManyContigsError(Exception):
    """Raised when FASTA has >5000 contigs and trim_to_5000 is False."""

    pass


# Pre-compile regex for validation
# Allowed: A, C, G, T, N, R, Y, S, W, K, M, B, D, H, V
VALID_CHARS_RE = re.compile(r"^[ACGTRYSWKMBDHVN]*$")


def normalize_sequence(seq: str) -> str:
    """
    Remove whitespace, uppercase, and convert U -> T.
    """
    # Remove whitespace (including newlines)
    seq = "".join(seq.split())
    # Uppercase
    seq = seq.upper()
    # U -> T
    seq = seq.replace("U", "T")
    return seq


def validate_sequence(seq: str) -> bool:
    """
    Validate that sequence contains only IUPAC DNA characters (ACGTN + ambiguity).
    """
    return bool(VALID_CHARS_RE.match(seq))


def read_and_process_fasta(
    path: str, trim_to_5000: bool = False
) -> List[Tuple[str, str]]:
    """
    Reads a FASTA file, normalizes, validates, sorts, and optionally trims it.
    Returns a list of (header, sequence) tuples.
    """
    contigs = []

    try:
        # We open explicitly to enforce utf-8 and handle file errors
        with open(path, "r", encoding="utf-8") as f:
            # Suppress BiopythonDeprecationWarning about leading whitespace/comments
            import warnings
            from Bio import BiopythonDeprecationWarning

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", BiopythonDeprecationWarning)
                records = list(SeqIO.parse(f, "fasta"))
    except UnicodeDecodeError:
        raise InvalidFastaError("File is not valid UTF-8.")
    except Exception as e:
        raise InvalidFastaError(f"Could not read FASTA file: {e}")

    if not records:
        raise InvalidFastaError("No sequences found in FASTA file.")

    for record in records:
        # record.description includes the ID and description.
        # The spec says "Each contig header (> line) preserved exactly".
        # Biopython splits id and description.
        # record.description is usually the full header line after '>'.
        header = record.description

        # record.seq is a Seq object, convert to str
        raw_seq = str(record.seq)

        norm_seq = normalize_sequence(raw_seq)

        if not validate_sequence(norm_seq):
            raise InvalidFastaError(f"Invalid characters in sequence: {header}")

        contigs.append((header, norm_seq))

    # Sort: Length desc, then Header asc
    contigs.sort(key=lambda x: (-len(x[1]), x[0]))

    if len(contigs) > 5000:
        if trim_to_5000:
            contigs = contigs[:5000]
        else:
            raise TooManyContigsError("More than 5000 contigs; use --trim-to-5000")

    return contigs


def to_fasta_string(contigs: List[Tuple[str, str]]) -> str:
    """
    Render contigs to a FASTA string.
    """
    output = []
    for header, seq in contigs:
        output.append(f">{header}")
        output.append(seq)
    return "\n".join(output)
