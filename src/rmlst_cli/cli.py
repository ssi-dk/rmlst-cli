import sys
import time
import click
import os
import traceback

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
@click.option(
    "--tsv", is_flag=False, flag_value="SPECIES_DEFAULT", help="Output TSV format."
)
@click.option("-u", "--uri", default=DEFAULT_URI, help="rMLST API URI.")
@click.option("--retries", default=3, help="Number of retries.")
@click.option("--retry-delay", default=60, help="Delay between retries in seconds.")
@click.option("--trim-to-5000", is_flag=True, help="Trim to 5000 contigs.")
@click.option("--graceful", is_flag=True, help="Graceful failure mode.")
@click.option("--debug", is_flag=True, help="Enable debug output.")
@click.version_option(__version__, prog_name="rmlst", message="%(prog)s %(version)s")
def main(
    fasta,
    directory,
    output,
    outdir,
    species_only,
    tsv,
    uri,
    retries,
    retry_delay,
    trim_to_5000,
    graceful,
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

    if species_only and tsv:
        click.echo("Error: --species-only and --tsv are mutually exclusive.", err=True)
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
    elif tsv:
        mode = "tsv"
        header = tsv if tsv != "SPECIES_DEFAULT" else "species"

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
    debug,
):
    final_out_path = out_path
    if out_path and os.path.isdir(out_path):
        suffix = ".json"
        if mode == "tsv":
            suffix = ".tsv"
        if mode == "species":
            suffix = ".txt"  # Default for species-only
        final_out_path = io.derive_output_path(fasta_path, out_path, suffix)

    # Check overwrite
    if final_out_path and os.path.exists(final_out_path):
        click.echo(f"[SKIP] {os.path.basename(final_out_path)} (exists)", err=True)
        sys.exit(EXIT_SUCCESS)

    try:
        result = api.identify(
            fasta_path,
            uri=uri,
            trim_to_5000=trim_to_5000,
            graceful=graceful,
            retries=retries,
            retry_delay=retry_delay,
            debug=debug,
        )
    except Exception as e:
        # If graceful=True, api.identify returns {}, so we won't be here.
        # If we are here, graceful=False.
        raise e

    # Format output
    content = ""
    if mode == "json":
        content = formats.format_json(result)
    else:
        species = formats.extract_species(result)
        if mode == "species":
            if header:
                content = f"{header}\n{species}"
            else:
                content = species
        elif mode == "tsv":
            h = header if header else "species"
            content = f"{h}\n{species}"

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
    if out_path and (mode == "tsv" or mode == "species"):
        summary_path = os.path.join(out_path, "rmlst_summary.tsv")

    for i, file_path in enumerate(files):
        if i > 0:
            time.sleep(1)

        basename = os.path.basename(file_path)

        if out_path and mode == "json":
            derived = io.derive_output_path(file_path, out_path, ".json")
            if os.path.exists(derived):
                click.echo(f"[SKIP] {os.path.basename(derived)} (exists)", err=True)
                skipped_count += 1
                continue

        file_result = None
        file_error = None
        is_graceful_failure = False

        try:
            res = api.identify(
                file_path,
                uri=uri,
                trim_to_5000=trim_to_5000,
                graceful=False,
                retries=retries,
                retry_delay=retry_delay,
                debug=debug,
            )
            file_result = res
            ok_count += 1
            if out_path:
                click.echo(f"[OK] {basename}", err=True)

        except Exception as e:
            failed_count += 1
            code = get_exit_code(e)
            highest_exit_code = max(highest_exit_code, code)

            if out_path:
                msg = str(e)
                if isinstance(e, InvalidFastaError):
                    msg = "invalid FASTA or no sequences"
                elif isinstance(e, TooManyContigsError):
                    msg = "more than 5000 contigs; use --trim-to-5000"
                elif isinstance(e, RmlstNetworkError):
                    msg = "network error"
                elif isinstance(e, RmlstHttpError):
                    msg = f"HTTP {e.status_code}"

                click.echo(f"[ERR code={code}] {basename}: {msg}", err=True)

            if graceful:
                is_graceful_failure = True
                file_result = {}
            else:
                file_error = {"code": code, "message": str(e)}

        # Collect results
        results.append(
            {
                "basename": basename,
                "result": file_result,
                "error": file_error,
                "is_graceful_failure": is_graceful_failure,
            }
        )

        # Write per-file JSON
        if out_path and mode == "json" and file_result is not None:
            derived = io.derive_output_path(file_path, out_path, ".json")
            io.atomic_write(derived, formats.format_json(file_result))

    # Final Output / Summary
    if out_path:
        click.echo(
            f"Done: {ok_count} ok, {failed_count} failed, {skipped_count} skipped.",
            err=True,
        )

        if mode != "json":
            h = header if header else "species"
            lines = [f"file\t{h}"]
            for item in results:
                if item["error"] and not graceful:
                    continue
                species = ""
                if item["result"]:
                    species = formats.extract_species(item["result"])
                lines.append(formats.format_tsv_row(item["basename"], species))

            content = "\n".join(lines)
            io.atomic_write(summary_path, content)

    else:
        # Stdout
        if mode == "json":
            use_wrapped = graceful
            if not use_wrapped:
                for item in results:
                    if item["result"] is not None:
                        if not formats.extract_species(item["result"]):
                            use_wrapped = True
                            break

            json_out = []
            for item in results:
                if use_wrapped:
                    if item["is_graceful_failure"]:
                        json_out.append({"file": item["basename"], "result": None})
                    elif item["error"]:
                        json_out.append(
                            {"file": item["basename"], "error": item["error"]}
                        )
                    else:
                        json_out.append(
                            {"file": item["basename"], "result": item["result"]}
                        )
                else:
                    if item["error"]:
                        json_out.append(
                            {"file": item["basename"], "error": item["error"]}
                        )
                    elif item["result"] is not None:
                        json_out.append(item["result"])

            click.echo(formats.format_json(json_out))

        else:
            h = header if header else "species"
            click.echo(f"file\t{h}")
            for item in results:
                if item["error"] and not graceful:
                    continue

                species = ""
                if item["result"]:
                    species = formats.extract_species(item["result"])

                click.echo(formats.format_tsv_row(item["basename"], species))

    sys.exit(highest_exit_code if not graceful else 0)
