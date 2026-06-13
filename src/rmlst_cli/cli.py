import sys
import time
import click
import os
import traceback
from dataclasses import dataclass
from typing import Any, Optional

from . import api, io, formats, __version__
from .fasta import InvalidFastaError, TooManyContigsError
from .http import RmlstNetworkError, RmlstHttpError, DEFAULT_URI

# Exit codes
EXIT_SUCCESS = 0
EXIT_UNEXPECTED = 1
EXIT_INPUT_ERROR = 2
EXIT_TOO_MANY_CONTIGS = 3
EXIT_NETWORK_ERROR = 4
EXIT_HTTP_ERROR = 5
EXIT_FS_ERROR = 7
EXIT_SIGINT = 130


@dataclass
class DirectoryResult:
    basename: str
    result: Optional[dict[str, Any]]
    error: Optional[dict[str, Any]]
    is_graceful_failure: bool = False
    progress_message: Optional[str] = None


def print_error(msg: str, exit_code: int, debug: bool = False):
    click.echo(msg, err=True)
    if debug:
        traceback.print_exc()
    sys.exit(exit_code)


def handle_exception(e: Exception, debug: bool):
    if isinstance(e, InvalidFastaError):
        print_error("invalid FASTA or no sequences", EXIT_INPUT_ERROR, debug)
    elif isinstance(e, TooManyContigsError):
        print_error(
            "more than 5000 contigs; use --trim-to-5000", EXIT_TOO_MANY_CONTIGS, debug
        )
    elif isinstance(e, RmlstNetworkError):
        print_error("network error after retries", EXIT_NETWORK_ERROR, debug)
    elif isinstance(e, RmlstHttpError):
        print_error(
            f"HTTP error {e.status_code} or invalid JSON", EXIT_HTTP_ERROR, debug
        )
    elif isinstance(e, OSError):
        print_error("filesystem error", EXIT_FS_ERROR, debug)
    else:
        print_error(f"unexpected error: {e}", EXIT_UNEXPECTED, debug)


def get_species_headers(header_str: Optional[str]) -> tuple[str, str]:
    """
    Parse header string into two headers for species and support columns.
    Accepts space or comma separated values.
    If only one value provided, uses it for species and appends 'support'.
    """
    if not header_str:
        return "species", "support"

    # Split by comma first, then by space if no comma
    parts = header_str.split(",")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    parts = header_str.split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], "support"
    else:
        return "species", "support"


def get_exit_code(e: Exception) -> int:
    if isinstance(e, InvalidFastaError):
        return EXIT_INPUT_ERROR
    if isinstance(e, TooManyContigsError):
        return EXIT_TOO_MANY_CONTIGS
    if isinstance(e, RmlstNetworkError):
        return EXIT_NETWORK_ERROR
    if isinstance(e, RmlstHttpError):
        return EXIT_HTTP_ERROR
    if isinstance(e, OSError):
        return EXIT_FS_ERROR
    return EXIT_UNEXPECTED


def get_error_message(e: Exception) -> str:
    if isinstance(e, InvalidFastaError):
        return "invalid FASTA or no sequences"
    if isinstance(e, TooManyContigsError):
        return "more than 5000 contigs; use --trim-to-5000"
    if isinstance(e, RmlstNetworkError):
        return "network error"
    if isinstance(e, RmlstHttpError):
        return f"HTTP {e.status_code}"
    return str(e)


def format_species_result(result: dict[str, Any], header: Optional[str] = None) -> str:
    names, supports = formats.extract_species_and_support(result)
    species_header, support_header = get_species_headers(header)
    return f"{species_header}\t{support_header}\n{names}\t{supports}"


def format_directory_species(
    results: list[DirectoryResult], header: Optional[str], graceful: bool
) -> str:
    species_header, support_header = get_species_headers(header)
    lines = [f"file\t{species_header}\t{support_header}"]

    for item in results:
        if item.error and not graceful:
            continue
        species, support = "", ""
        if item.result:
            species, support = formats.extract_species_and_support(item.result)
        lines.append(f"{item.basename}\t{species}\t{support}")

    return "\n".join(lines)


def format_directory_json(results: list[DirectoryResult], graceful: bool) -> str:
    use_wrapped = graceful
    if not use_wrapped:
        for item in results:
            if item.result is not None and not formats.extract_species(item.result):
                use_wrapped = True
                break

    json_out: list[dict[str, Any]] = []
    for item in results:
        if use_wrapped:
            if item.is_graceful_failure:
                json_out.append({"file": item.basename, "result": None})
            elif item.error:
                json_out.append({"file": item.basename, "error": item.error})
            else:
                json_out.append({"file": item.basename, "result": item.result})
        else:
            if item.error:
                json_out.append({"file": item.basename, "error": item.error})
            elif item.result is not None:
                json_out.append(item.result)

    return formats.format_json(json_out)


def identify_directory_file(
    file_path: str,
    *,
    uri: str,
    retries: int,
    retry_delay: int,
    trim_to_5000: bool,
    graceful: bool,
    debug: bool,
) -> tuple[DirectoryResult, bool, int]:
    basename = os.path.basename(file_path)

    try:
        result = api.identify(
            file_path,
            uri=uri,
            trim_to_5000=trim_to_5000,
            graceful=False,
            retries=retries,
            retry_delay=retry_delay,
            debug=debug,
        )
        return DirectoryResult(basename=basename, result=result, error=None), True, 0
    except Exception as e:
        code = get_exit_code(e)
        if graceful:
            return (
                DirectoryResult(
                    basename=basename,
                    result={},
                    error=None,
                    is_graceful_failure=True,
                    progress_message=get_error_message(e),
                ),
                False,
                code,
            )
        return (
            DirectoryResult(
                basename=basename,
                result=None,
                error={"code": code, "message": str(e)},
                progress_message=get_error_message(e),
            ),
            False,
            code,
        )


@click.command()
@click.option(
    "-f",
    "--fasta",
    type=click.Path(exists=True, dir_okay=False),
    help="Single FASTA file input.",
)
@click.option(
    "-d",
    "--dir",
    "directory",
    type=click.Path(exists=True, file_okay=False),
    help="Directory input.",
)
@click.option("-o", "--output", type=click.Path(), help="Output file or directory.")
@click.option("-O", "--outdir", type=click.Path(), help="Output directory.")
@click.option(
    "--species-only",
    is_flag=False,
    flag_value="SPECIES_DEFAULT",
    help="Output species only.",
)
@click.option("-u", "--uri", default=DEFAULT_URI, help="rMLST API URI.")
@click.option("--retries", default=3, help="Number of retries.")
@click.option("--retry-delay", default=60, help="Delay between retries in seconds.")
@click.option("--trim-to-5000", is_flag=True, help="Trim to 5000 contigs.")
@click.option("--graceful", is_flag=True, help="Graceful failure mode.")
@click.option("--force", is_flag=True, help="Force overwrite of existing output files.")
@click.option("--debug", is_flag=True, help="Enable debug output.")
@click.version_option(__version__, prog_name="rmlst", message="%(prog)s %(version)s")
def main(
    fasta,
    directory,
    output,
    outdir,
    species_only,
    uri,
    retries,
    retry_delay,
    trim_to_5000,
    graceful,
    force,
    debug,
):
    """rmlst-cli: rMLST API client."""

    # Input validation
    if fasta and directory:
        click.echo("Error: --fasta and --dir are mutually exclusive.", err=True)
        sys.exit(EXIT_INPUT_ERROR)
    if not fasta and not directory:
        click.echo("Error: One of --fasta or --dir must be provided.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if output and outdir:
        click.echo("Error: --output and --outdir are mutually exclusive.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    # Determine output mode
    mode = "json"
    header = None
    if species_only:
        mode = "species"
        if species_only != "SPECIES_DEFAULT":
            header = species_only

    # Unify output/outdir
    out_path = output or outdir

    try:
        if fasta:
            handle_single_file(
                fasta,
                out_path,
                mode,
                header,
                uri,
                retries,
                retry_delay,
                trim_to_5000,
                graceful,
                force,
                debug,
            )
        else:
            handle_directory(
                directory,
                out_path,
                mode,
                header,
                uri,
                retries,
                retry_delay,
                trim_to_5000,
                graceful,
                force,
                debug,
            )

    except KeyboardInterrupt:
        sys.exit(EXIT_SIGINT)
    except Exception as e:
        handle_exception(e, debug)


def handle_single_file(
    fasta_path,
    out_path,
    mode,
    header,
    uri,
    retries,
    retry_delay,
    trim_to_5000,
    graceful,
    force,
    debug,
):
    final_out_path = out_path
    if out_path and os.path.isdir(out_path):
        suffix = ".json"
        if mode == "species":
            suffix = ".txt"  # Default for species-only
        final_out_path = io.derive_output_path(fasta_path, out_path, suffix)

    # Check overwrite
    if final_out_path and os.path.exists(final_out_path) and not force:
        click.echo(f"[SKIP] {os.path.basename(final_out_path)} (exists)", err=True)
        sys.exit(EXIT_SUCCESS)

    result = api.identify(
        fasta_path,
        uri=uri,
        trim_to_5000=trim_to_5000,
        graceful=graceful,
        retries=retries,
        retry_delay=retry_delay,
        debug=debug,
    )

    # Format output
    content = ""
    if mode == "json":
        content = formats.format_json(result)
    else:
        content = format_species_result(result, header)

    # Write output
    if final_out_path:
        io.atomic_write(final_out_path, content)
    else:
        click.echo(content)


def handle_directory(
    dir_path,
    out_path,
    mode,
    header,
    uri,
    retries,
    retry_delay,
    trim_to_5000,
    graceful,
    force,
    debug,
):
    if out_path:
        if os.path.exists(out_path) and not os.path.isdir(out_path):
            click.echo(
                "Error: Output path must be a directory in directory mode.", err=True
            )
            sys.exit(EXIT_INPUT_ERROR)
        if not os.path.exists(out_path):
            os.makedirs(out_path, exist_ok=True)

    files = io.scan_directory(dir_path)
    if not files:
        click.echo("invalid FASTA or no sequences", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    ok_count = 0
    failed_count = 0
    skipped_count = 0
    highest_exit_code = 0

    results = []

    summary_path = None
    if out_path and mode == "species":
        summary_path = os.path.join(out_path, "rmlst_summary.tsv")

    for i, file_path in enumerate(files):
        if i > 0:
            time.sleep(1)

        basename = os.path.basename(file_path)

        if out_path and mode == "json":
            derived = io.derive_output_path(file_path, out_path, ".json")
            if os.path.exists(derived) and not force:
                click.echo(f"[SKIP] {os.path.basename(derived)} (exists)", err=True)
                skipped_count += 1
                continue

        result, ok, code = identify_directory_file(
            file_path,
            uri=uri,
            trim_to_5000=trim_to_5000,
            graceful=graceful,
            retries=retries,
            retry_delay=retry_delay,
            debug=debug,
        )

        if ok:
            ok_count += 1
            if out_path:
                click.echo(f"[OK] {basename}", err=True)
        else:
            failed_count += 1
            highest_exit_code = max(highest_exit_code, code)
            if out_path:
                msg = result.progress_message or ""
                click.echo(f"[ERR code={code}] {basename}: {msg}", err=True)

        results.append(result)

        # Write per-file JSON
        if out_path and mode == "json" and result.result is not None:
            derived = io.derive_output_path(file_path, out_path, ".json")
            io.atomic_write(derived, formats.format_json(result.result))

    # Final Output / Summary
    if out_path:
        click.echo(
            f"Done: {ok_count} ok, {failed_count} failed, {skipped_count} skipped.",
            err=True,
        )

        if mode != "json":
            content = format_directory_species(results, header, graceful)
            io.atomic_write(summary_path, content)

    else:
        # Stdout
        if mode == "json":
            click.echo(format_directory_json(results, graceful))

        else:
            if mode == "species":
                click.echo(format_directory_species(results, header, graceful))
            else:
                # JSON mode already handled above
                pass

    sys.exit(highest_exit_code if not graceful else 0)
