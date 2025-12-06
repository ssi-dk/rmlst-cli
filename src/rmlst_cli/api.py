from typing import Dict, Iterator, Tuple
import os

from . import fasta, http, io
from .http import DEFAULT_URI

# Re-export exceptions and functions
from .fasta import InvalidFastaError, TooManyContigsError
from .http import RmlstNetworkError, RmlstHttpError


def identify(
    fasta_path: str,
    *,
    uri: str = DEFAULT_URI,
    trim_to_5000: bool = False,
    graceful: bool = False,
    retries: int = 3,
    retry_delay: int = 60,
    debug: bool = False,
) -> Dict:
    """
    Identify species from a single FASTA file.
    """
    try:
        # 1. Read and process FASTA
        contigs = fasta.read_and_process_fasta(fasta_path, trim_to_5000=trim_to_5000)

        # 2. Render to string
        fasta_str = fasta.to_fasta_string(contigs)

        # 3. Call API
        result = http.call_rmlst_api(
            fasta_str, uri=uri, retries=retries, retry_delay=retry_delay, debug=debug
        )
        return result

    except (
        InvalidFastaError,
        TooManyContigsError,
        RmlstNetworkError,
        RmlstHttpError,
    ) as e:
        if graceful:
            return {}
        raise e


def identify_dir(
    dir_path: str,
    *,
    uri: str = DEFAULT_URI,
    trim_to_5000: bool = False,
    graceful: bool = False,
    retries: int = 3,
    retry_delay: int = 60,
    debug: bool = False,
) -> Iterator[Tuple[str, Dict]]:
    """
    Identify species for all FASTA files in a directory.
    Yields (basename, result_dict).
    """
    files = io.scan_directory(dir_path)

    if not files:
        raise InvalidFastaError("No valid FASTA files found in directory.")

    for file_path in files:
        basename = os.path.basename(file_path)
        try:
            result = identify(
                file_path,
                uri=uri,
                trim_to_5000=trim_to_5000,
                graceful=graceful,
                retries=retries,
                retry_delay=retry_delay,
                debug=debug,
            )
            yield basename, result

        except Exception as e:
            # If identify raised, it means graceful=False (or unexpected error).
            # We should let it propagate.
            raise e
