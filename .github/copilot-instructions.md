# Copilot Instructions for rmlst-cli

You are helping to implement and maintain **rmlst-cli**, a CLI and Python API for calling the rMLST PubMLST API.

## 1. Always read the spec and TODO first

Before making changes, **always**:

1. Open and read `.github/spec.md`.
   - This file is the **source of truth** for behavior.
   - Do not contradict or silently deviate from it.
2. Open and read `.github/todo.md`.
   - This file states what is planned and what remains.
   - Keep it updated as tasks are completed or added.
3. You can review old implementation in old_rmlst/ if there is a need to compare.

Never invent new behavior that conflicts with `spec.md`. If something in the code diverges from the spec, assume the **spec is correct** unless there is a clear comment stating otherwise.

## 2. Overall goals

- Provide a **robust CLI** (`rmlst` and `rmlst-cli`) to call the rMLST API with:
  - Single FASTA or directory of FASTA files.
  - Enforced 5,000-contig limit, with optional trimming.
  - Clear JSON and TSV outputs.
  - Good error handling and exit codes.
- Provide an **importable Python API** (`rmlst_cli.api`) with:
  - `identify(...)` for single FASTA.
  - `identify_dir(...)` for directories.
  - `extract_species(...)` for consistent parsing of rMLST results.

## 3. Key design constraints (do not change)

When writing or modifying code, respect these constraints:

- **Python support**: `>=3.9,<3.15`.
- **Package name**: `rmlst-cli` (PyPI/Bioconda).
- **Module name**: `rmlst_cli`.
- **Executables**:
  - `rmlst`
  - `rmlst-cli`
- **HTTP**:
  - Use JSON payload `{ "sequence": "<base64>", "base64": true, "details": true }`.
  - Default endpoint: kiosk rMLST API.
  - Fallback to non-kiosk endpoint only if using default URI.
  - Retries on network/5xx/429 with fixed delay.
  - Ignore `Retry-After`.
- **FASTA**:
  - Normalize sequences (uppercase, `U→T`, strip whitespace).
  - Validate only IUPAC DNA characters (ACGTN + ambiguity codes).
  - Sort by length desc + header tie-breaker.
  - Enforce 5,000-contig rule and `--trim-to-5000` semantics.
- **Output**:
  - Pretty JSON (2-space indent, no key-sorting).
  - TSV with `file<TAB>HEADER`.
  - `--species-only[=HEADER]` and `--tsv[=HEADER]` mutually exclusive.
  - Directory → stdout JSON: unwrapped or wrapped arrays as defined.
- **Error handling**:
  - Exit codes exactly as specified.
  - `--graceful` must return empty/neutral outputs but still exit 0.
- **No caching** and **no gzip FASTA**.

## 4. Implementation guidance

### 4.1 Files and modules

Follow the layout described in `spec.md`. In particular:

- `src/rmlst_cli/cli.py`
  - Implement the Click-based CLI.
  - The CLI must match the option names and semantics in the spec.
- `src/rmlst_cli/api.py`
  - Implement `identify(...)`, `identify_dir(...)`, `extract_species(...)`.
  - Mirror CLI behavior for FASTA and HTTP logic where appropriate.
- `src/rmlst_cli/fasta.py`
  - Implement FASTA parsing, validation, normalization, sorting, trimming.
- `src/rmlst_cli/http.py`
  - Implement HTTP calls, retries, and fallback.
- `src/rmlst_cli/formats.py`
  - Implement JSON/TSV rendering and species extraction.
- `src/rmlst_cli/io.py`
  - Implement directory scanning, path classification, atomic writes, skip/summary logic.

### 4.2 CLI behavior

Make sure the CLI adheres to:

- Exactly one of `--fasta` or `--dir` must be provided.
- `--species-only[=HEADER]` and `--tsv[=HEADER]` are mutually exclusive.
- `--output` and `--outdir`:
  - If both provided → exit code 2.
  - Directory + output file → exit code 2.
  - Respect skip/overwrite rules and summary behavior.

### 4.3 Python API behavior

Ensure:

- `identify` mirrors the CLI behavior for a single file.
  - On failure:
    - Raise exceptions when `graceful=False`.
    - Return `{}` when `graceful=True`.
- `identify_dir`:
  - Yields `(basename, dict)` for each file.
  - Raises early if directory has no valid `.fa`/`.fasta` files.
  - For failures:
    - `graceful=False`: raise on first failure.
    - `graceful=True`: yield `(basename, {})` and continue.

### 4.4 Tests

When adding tests:

- Cover:
  - Single-file JSON, TSV, species-only.
  - Directory JSON and TSV, with and without `--graceful`.
  - Error cases: invalid FASTA, >5000 contigs, network/HTTP errors.
- Prefer small, fast tests but also include some integration tests using the real PubMLST API (careful with rate and runtime).
- Keep Bioconda `test:` offline (only `--version`, `--help`).

## 5. Updating todo.md

Whenever you complete meaningful work:

1. Mark relevant items in `todo.md` as done (`[x]`).
2. If you introduce new implementation steps or sub-tasks:
   - Add them to `todo.md` in the appropriate section.
3. If you discover deviations between code and spec that you **must** implement:
   - Prefer updating code to match `spec.md`.
   - If the spec is clearly wrong/outdated, add a comment in `todo.md` (and/or the PR description) explaining the discrepancy so a human can reconcile.

## 6. Style & quality

- Use type hints and keep `mypy` happy where configured.
- Use `black` and `ruff` as configured (via Pixi/pre-commit).
- Prefer small, well-named functions over large monolithic blocks.
- Keep error messages concise and match the exact wording from `spec.md`.

## 7. Do not do these things

- Do **not** add new CLI flags or change existing flag names/semantics without the spec being explicitly updated.
- Do **not** change exit code meanings.
- Do **not** silently alter output formats (JSON structure or TSV header/order).
- Do **not** introduce environment-variable-based configuration unless added to the spec.
- Do **not** add caching or gzip input support unless the spec is revised.

## 8. Environment & Testing

- Use the existing conda environment in `.conda_env/` for running tests and executing the tool.
- Do not create new virtual environments unless explicitly requested.
- Ensure dependencies are installed in this environment.

---

**In short:**  
**Read `spec.md` → check `todo.md` → implement exactly what the spec says → update `todo.md`.**
