# rmlst-cli TODO

This is a living implementation checklist. Keep it up to date as work progresses.

## 1. Repo setup

- [x] Create/rename repo to `https://github.com/ssi-dk/rmlst_cli`.
- [x] Add `LICENSE` (MIT) with 2025 and Povilas Matusevicius.
- [x] Add `pyproject.toml` with:
  - [x] Hatchling as backend.
  - [x] hatch-vcs for versioning from tags (`vMAJOR.MINOR`).
  - [x] `requires-python = ">=3.9,<3.15"`.
  - [x] `rmlst-cli` metadata (authors, URLs, description).
  - [x] Console scripts: `rmlst` and `rmlst-cli`.
- [x] Add `.gitignore` (Python, build artifacts, etc.).

## 2. Project layout & scaffolding

- [x] Create `src/rmlst_cli/` package:
  - [x] `__init__.py` (expose `__version__`, import API functions).
  - [x] `cli.py`.
  - [x] `api.py`.
  - [x] `http.py`.
  - [x] `fasta.py`.
  - [x] `io.py`.
  - [x] `formats.py`.
  - [x] `types.py` (optional but useful for type hints).
- [x] Create `tests/` structure:
  - [x] `tests/test_cli.py`.
  - [x] `tests/test_api.py`.
  - [x] `tests/fixtures/` (add small/large FASTA files).
  - [x] `tests/helpers.py` if needed.

## 3. FASTA handling (`fasta.py`)

- [x] Implement FASTA reading using **Biopython** as baseline:
  - [x] Decode as UTF-8; treat decode failures as invalid FASTA.
  - [x] Parse sequences (headers + sequence strings).
  - [x] Ensure at least one sequence exists.
- [x] Implement normalization:
  - [x] Remove whitespace from sequences.
  - [x] Uppercase.
  - [x] Replace `U` with `T`.
- [x] Implement validation:
  - [x] Allow only IUPAC DNA characters (A/C/G/T/N + ambiguity codes).
  - [x] On any invalid character → mark entire FASTA invalid (CLI code 2).
- [x] Implement contig length computation (length of normalized sequence).
- [x] Implement sorting + trimming logic:
  - [x] Sort by length (desc), tie-break header (asc).
  - [x] Always sort.
  - [x] If `--trim-to-5000` provided:
    - [x] Keep top 5,000 sequences (sorted).
    - [x] Keep all if ≤5,000.
  - [x] If not provided and >5,000:
    - [x] Raise an error (mapped to exit code 3).
- [x] Implement function to render normalized FASTA for payload (headers + single-line sequences).

## 4. HTTP & API (`http.py`)

- [x] Implement base HTTP client using **requests**:
  - [x] Function to POST with JSON body and timeouts (10s connect, 120s read).
  - [x] Include headers (Content-Type, Accept, User-Agent).
- [x] Implement retry logic:
  - [x] On network errors, 5xx, or 429.
  - [x] Use `retries` and `retry_delay` parameters.
  - [x] Ignore `Retry-After`.
- [x] Implement kiosk vs non-kiosk fallback:
  - [x] Only when `uri` is the default kiosk URI.
  - [x] After retries fail on kiosk, attempt same sequence against non-kiosk.
- [x] Implement error classifications:
  - [x] Map HTTP/network/JSON failures to internal error types → CLI exit codes (4/5).

## 5. Species extraction & formatting (`formats.py`)

- [x] Implement `extract_species(api_json: dict) -> str`:
  - [x] Identify correct `taxon_prediction`/species path by inspecting real API response.
  - [x] Handle multiple predictions:
    - [x] Collect species names + probabilities if available.
    - [x] Deduplicate species.
    - [x] Sort by descending probability; fallback alphabetical if needed.
    - [x] Join with `","`.
  - [x] Return empty string if no predictions (no-match is success).
- [x] Implement JSON output helpers:
  - [x] Pretty-print with 2-space indent, preserve key order.
  - [x] Build arrays for:
    - [x] Unwrapped JSON array mode.
    - [x] Wrapped mode (file+result/error).
- [x] Implement TSV output helpers:
  - [x] Header line generation for `file<TAB>HEADER`.
  - [x] Per-row formatting with value normalization:
    - [x] Replace `	`/`
` in species string with `" "`.
    - [x] Strip outer whitespace.

## 6. I/O & directory logic (`io.py`)

- [x] Implement directory scanning:
  - [x] Top-level only.
  - [x] Match `.fa` / `.fasta` (case-insensitive).
  - [x] Include symlinks that match naming.
  - [x] Sort results by basename.
- [x] Implement path classification for `--output` / `--outdir`:
  - [x] Use FS existence to distinguish file vs directory when possible.
  - [x] Enforce rules:
    - [x] Single-file + output file → write file.
    - [x] Single-file + output dir → derive filename in that dir.
    - [x] Directory + output dir → per-file outputs / aggregated TSV.
    - [x] Directory + output file → error (mapped to exit code 2).
- [x] Implement “no overwrite” logic:
  - [x] Skip writing if per-file output exists → `[SKIP]` and count as skipped.
  - [x] Make `rmlst_summary.tsv` the only file that may be overwritten.
- [x] Implement atomic writes:
  - [x] Write to temp file in target dir and rename on success.
- [x] Implement 1-second sleep between files in directory mode.

## 7. CLI (`cli.py`)

- [x] Use **Click** for CLI implementation.
- [x] Define options exactly as per spec:
  - [x] `--fasta`, `--dir`.
  - [x] `--species-only[=HEADER]`, `--tsv[=HEADER]` (mutually exclusive).
  - [x] `-o/--output`, `-O/--outdir`.
  - [x] `-u/--uri`, `--retries`, `--retry-delay`, `--trim-to-5000`, `--graceful`, `--debug`.
  - [x] `--version`.
- [x] Implement single-file flow:
  - [x] Parse + validate FASTA (error = exit 2).
  - [x] Sort/trim as necessary.
  - [x] Build request payload.
  - [x] Call HTTP layer with retries/fallback.
  - [x] Handle success vs failure vs graceful.
  - [x] Render JSON/TSV/species-only appropriately.
- [x] Implement directory flow:
  - [x] Scan directory.
  - [x] Handle empty dir → exit 2.
  - [x] Process files sequentially with 1s delay.
  - [x] Maintain counters: ok / failed / skipped.
  - [x] Apply JSON/TSV/species-only modes.
  - [x] Handle `--graceful` behavior.
  - [x] Print per-file progress lines on stderr when `--outdir` is set.
  - [x] Print final summary line.
- [x] Implement exit code handling:
  - [x] For directory mode, exit with highest error code seen (except 0/130).
- [x] Implement `--version` to print `rmlst <version>`.

## 8. Python API (`api.py`)

- [x] Implement `identify(...) -> dict`:
  - [x] Reuse FASTA + HTTP modules.
  - [x] Implement `graceful` behavior (`{}` on failure).
  - [x] Raise exceptions on failures when `graceful=False`.
- [x] Implement `identify_dir(...) -> Iterator[(str, dict)]`:
  - [x] Reuse directory scanning + FASTA + HTTP modules.
  - [x] Raise immediately if directory has no valid `.fa`/`.fasta` files.
  - [x] For each file:
    - [x] If `graceful=False` → raise on first failure.
    - [x] If `graceful=True` → yield `(basename, {})` on failure and continue.
- [x] Re-export `extract_species` from `formats.py`.

## 9. Benchmark & optimization (manual)

- [x] Create alternative implementation:
  - [x] Compared against legacy `old_rmlst` (manual parsing).
  - [x] Decided against `httpx` as `requests` is sufficient and bottleneck is network.
- [x] Benchmark on a local machine:
  - [x] Use small real FASTAs and a large synthetic FASTA.
  - [x] Compare end-to-end time (5+ runs).
  - *Result: New implementation (~16.8s) is comparable to legacy (~17.5s). Overhead is negligible.*
- [x] Choose final implementation:
  - [x] Keep variant that is ≥5% faster median (or fewer deps as tie-breaker).
  - [x] Remove the losing implementation and its dependencies from `pyproject.toml`.
  - *Decision: Kept Biopython implementation for robustness.*

## 10. Tests

- [x] Add real fixtures for:
  - [x] Valid FASTA with known species.
  - [x] FASTA with >5000 contigs (synthetic).
  - [x] FASTA with invalid characters.
- [x] CLI tests:
  - [x] Single-file JSON output.
  - [x] Single-file species-only and TSV.
  - [x] Directory JSON output (wrapped/unwrapped).
  - [x] Directory TSV output (with and without `--graceful`).
  - [x] Error conditions: invalid FASTA, too many contigs, network error, etc.
- [x] API tests:
  - [x] `identify()` success, failure, `graceful`.
  - [x] `identify_dir()` success, no valid inputs, partial failures.
- [x] Integration tests using real PubMLST API:
  - [x] Use fixtures and actually hit the API.
  - [x] Keep tests careful/not too heavy.

## 11. CI & tooling

- [x] Add `.pre-commit-config.yaml` with ruff/black/mypy.
- [x] Add GitHub Actions workflow:
  - [x] Matrix: Python 3.9–3.14 on Ubuntu, macOS, Windows.
  - [x] Install via pixi or standard pip.
  - [x] Run lint, typecheck, tests.
  - [x] Build sdist and wheel.
  - [x] On `v*` tag, publish to PyPI using `PYPI_API_TOKEN`.
- [x] Set up Pixi environment:
  - [x] Dependencies for dev (pytest, ruff, black, mypy, hatch, requests, Biopython, etc.).
  - [x] Tasks: `test`, `lint`, `fmt`, `typecheck`, `build`, `release`.

## 12. Docs (README & spec alignment)

- [x] Implement README sections:
  - [x] Install.
  - [x] Quickstart.
  - [x] Output modes.
  - [x] Examples (block from spec).
  - [x] Exit codes.
  - [x] Python API usage.
- [x] Confirm README matches behavior defined in `spec.md`.
- [x] Add link to spec in README for internal reference (optional).
