# rmlst-cli Specification (v1.0)

## 1. Overview

**Name**

- PyPI / Bioconda distribution: `rmlst-cli`
- Python package/module: `rmlst_cli`
- Executables:
  - `rmlst`
  - `rmlst-cli` (alias)

**Tagline / description**

> `rmlst-cli` is a simple tool to use the rMLST API through the command line.

**Goal**

Turn the existing `ssi-dk/rmlst` script into a proper, installable, cross-platform CLI and Python API that:

- Calls PubMLST rMLST species identification endpoint(s).
- Works with single FASTA files and directories of FASTA files.
- Enforces the 5,000-contig limit with optional trimming.
- Provides clear JSON/TSV outputs, robust error handling, and well-documented behavior.
- Is distributable via **PyPI** and **Bioconda**.
- Is installable via pip/uv/conda/pixi.

**Non-goals (v1.0)**

- No gzipped FASTA support (`.fa.gz`, `.fasta.gz`).
- No caching of results.
- No streaming/low-memory mode beyond holding up to 5,000 contigs in memory.
- No TLS verification bypass flags.
- No live configuration via environment variables (CLI flags only).

---

## 2. CLI Specification

### 2.1 Command

Single command with options:

```bash
rmlst [OPTIONS]
# alias: rmlst-cli [OPTIONS]
```

### 2.2 Inputs

**Mutually exclusive input options (exactly one must be provided):**

- `-f, --fasta PATH`
  - Single FASTA file input.
  - No stdin input (no `-` support).
- `-d, --dir PATH`
  - Directory input (top-level only).

**Directory scanning rules:**

- Non-recursive: only the specified directory’s **top level**.
- Include files whose names end (case-insensitive) in:
  - `.fa`
  - `.fasta`
- Include symlinks if their filenames match the above patterns.
- Skip hidden files (names starting with `.`) unless they still match `.fa`/`.fasta` and the user explicitly passes them as `--fasta` (single-file mode).
- Process matching files in **alphabetical order** by basename (case-sensitive sort of the string).

If directory contains **no** `.fa`/`.fasta` files:

- Print a concise error on stderr: `invalid FASTA or no sequences` (reusing the generic message).
- Exit with code **2**.
- No output to stdout or `--outdir`.

### 2.3 Output modes

The tool supports three mutually exclusive output modes:

1. **Full JSON** (default)
2. **Species-only**
3. **TSV**

#### 2.3.1 Mode selection options

- `--species-only[=HEADER]`
  - If provided **without** value:
    - Interpret as “species-only” mode with default header (when applicable).
  - If provided **with** a value:
    - Interpret as “species-only” mode with custom header (applies to TSV-like behavior as described below).
- `--tsv[=HEADER]`
  - If provided without value:
    - TSV mode with default column header `species`.
  - If provided with value:
    - TSV mode with given header.
- `--species-only` and `--tsv` are **mutually exclusive**:
  - If both are provided → error, exit code **2**.

#### 2.3.2 Species extraction (used for species-only + TSV modes)

Given the raw API JSON for a file:

- The developer must implement `extract_species(api_json: dict) -> str` with these rules:
  - Species info is expected under something like `taxon_prediction`, likely `taxon_prediction.species`. Exact keypath must be discovered empirically from the API; the code must be written to that actual structure.
  - If multiple species predictions exist:
    - Collect all species names.
    - Remove duplicates.
    - Order by **descending probability** where probabilities are available; if no probabilities, fall back to alphabetical order.
    - Join with comma: `","`.
  - If no species prediction is present (e.g. no identifiers):
    - Treat this as **success**, not an error.
    - Return an **empty string**.

### 2.4 Output destinations

Two related options:

- `-o, --output PATH`
- `-O, --outdir PATH` (alias: `--outdir`, capital `-O` for short)

Both are defined but have **context-dependent semantics**.

#### 2.4.1 General rules

**Single-file mode (`--fasta`)**

1. **Input file + output file**
   - If `--output` is interpreted as a file path, write the result to that file.
2. **Input file + output directory**
   - If `--output` / `--outdir` is interpreted as a directory, create an output file inside that directory.
   - Naming rules depend on output mode (see below).

**Directory mode (`--dir`)**

3. **Input directory + output directory**
   - Valid case.
   - Writes per-file outputs (JSON) and/or a single aggregated TSV, depending on mode (see below).
4. **Input directory + output file**
   - **Invalid**.
   - Should error with exit code **2**.

**Both `--output` and `--outdir` provided**

- This is invalid; exit code **2**.
- Short error on stderr, no stdout.

#### 2.4.2 Path classification & extension behavior

We want simple behavior for users but also predictable logic for the code.

- **If the path exists:**
  - If it is a directory → treat as directory.
  - If it is a file → treat as file.
- **If the path does not exist:**
  - In **directory mode**, treat `--output` / `--outdir` as a **directory** (create it).
  - In **single-file mode**, treat `--output` as a **file** by default.
    - If the program itself is deciding a path (e.g. default and derived files), it should prefer file extensions matching the output format (e.g. `.json` for JSON, `.tsv` for TSV).
    - If the user explicitly passes a name with “wrong” extension (e.g. `--output sample.txt` for JSON), the program **does not alter or reject** based on extension; it writes the correct content to that path.

We do **not** enforce extension-type consistency when the user explicitly specifies a filename; we only use sensible extensions when the program derives filenames.

#### 2.4.3 No overwrites policy

- In **general**, existing destination files are **not overwritten**, except for one special case (aggregated TSV).
- If the destination file already exists:

  - **Single-file mode** (`--fasta`):
    - If `--output FILE` points to an existing file:
      - Do **not** overwrite.
      - Print `[SKIP] <FILE> (exists)` to stderr.
      - Exit code **0** (success).
    - If `--output DIR` or `--outdir DIR` and the derived per-file output already exists, same `[SKIP]` behavior for that file, exit code 0.

  - **Directory mode** (`--dir`):
    - Per-file outputs (JSON): if a derived `<basename>_rmlst.json` already exists, **skip** and `[SKIP] <basename>_rmlst.json (exists)` on stderr.
    - Aggregated TSV (`rmlst_summary.tsv`, see below) is the **only file that may be overwritten**:
      - If `rmlst_summary.tsv` exists, it **is overwritten** when running again.

- Skipped files are counted as **skipped**, not failed, and do not cause a non-zero exit code.

---

## 3. Output formats

### 3.1 JSON (default full output)

**Default format:**

- Pretty-printed JSON with **2-space** indentation.
- Keys are **not** re-sorted; preserve API’s original key order.
- A trailing newline is fine.

#### 3.1.1 Single-file, JSON

- Default: print to **stdout**, unless `--output` is given.
- If `--output` or `--outdir` is interpreted as directory:
  - Use `<basename>_rmlst.json` as derived filename.
- If `--output` is interpreted as a file:
  - Write JSON to that file.
- Graceful behavior:
  - With `--graceful`, if a failure occurs, print `{}` and exit 0.

#### 3.1.2 Directory mode, JSON to stdout (no `--outdir`)

Output is one JSON array.

There are two shape modes:

1. **Unwrapped mode** (default when everything has species identifiers):
   - Array: `[ <api_json_file1>, <api_json_file2>, ... ]`
   - Per-file failures (non-graceful):
     - Still included as objects of shape:
       ```json
       {
         "file": "<basename>",
         "error": {
           "code": <int>,
           "message": "<short message>"
         }
       }
       ```
     - Exit code is non-zero (highest error code among failures, see §5).
   - `--graceful` **off**:
     - Failures included as above.
   - `--graceful` **on**:
     - Immediately switch to the “wrapped” shape for the entire array (see below).

2. **Wrapped mode** (triggered in specific conditions):
   - We use this array shape:
     - Success:
       ```json
       {
         "file": "<basename>",
         "result": { ... raw API JSON ... }
       }
       ```
     - Graceful failure:
       ```json
       {
         "file": "<basename>",
         "result": null
       }
       ```
     - Non-graceful failure:
       ```json
       {
         "file": "<basename>",
         "error": {
           "code": <int>,
           "message": "<short message>"
         }
       }
       ```
   - **When to use wrapped mode:**
     - If any file’s API JSON lacks species identifiers (`extract_species(api_json)` returns empty because there were no predictions), the **entire array** switches to wrapped mode.
     - If `--graceful` is set, always use wrapped mode.

The final array is printed to stdout and must be valid JSON.

#### 3.1.3 Directory mode with `--outdir`, JSON

- **Full JSON mode**:
  - Each input FASTA gets a per-file JSON:
    - `<basename>_rmlst.json` inside `--outdir`.
  - No aggregated JSON summary file.
  - Stderr:
    - For each success: `[OK] <basename>`
    - For each failure: `[ERR code=<n>] <basename>: <short message>`
    - For each skip: `[SKIP] <basename>_rmlst.json (exists)`
    - Final summary line:
      - `Done: <ok> ok, <failed> failed, <skipped> skipped.`
  - Exit code:
    - Highest error code among failed files (if any).
    - 0 if all successful or skipped.
    - 130 on Ctrl-C (SIGINT).

### 3.2 Species-only mode

#### 3.2.1 Single-file

- `--species-only` with no `--output`:
  - Print just the species string (from `extract_species`) to stdout followed by newline.
- `--species-only=HEADER` (single-file):
  - Behaves like TSV one-column output:
    - Output:
      ```
      HEADER
      <species-string>
      ```
  - Can be written to file via `--output` / `--outdir`.
- `--output` path semantics as per §2.4.
- Graceful:
  - With `--graceful`:
    - On failure, print either:
      - If plain species-only: an empty line.
      - If TSV style: header + empty second line.
    - Exit 0.

#### 3.2.2 Directory mode → stdout

- TSV-like output:
  - Header row:
    - If `--species-only` (no value): `file<TAB>species`
    - If `--species-only=HEADER`: `file<TAB>HEADER`
  - One row per file:
    - `file` = basename of the FASTA (including extension).
    - `species` = extracted species string.
    - Tabs/newlines in species are normalized:
      - Replace any `	` or `
` with a single space.
      - Trim surrounding whitespace.
- Failures and graceful behavior:
  - `--graceful` **off**:
    - Failed files are **skipped** from TSV output.
    - Errors reported on stderr.
  - `--graceful` **on**:
    - All files have a TSV row.
    - Failed files have an empty species field:
      - `file<TAB>`.
    - Exit 0.

#### 3.2.3 Directory mode + `--outdir`

- Writes a **single aggregated TSV** in `--outdir`:
  - Filename: `rmlst_summary.tsv`.
  - Header as above.
  - Rows as above.
- If `rmlst_summary.tsv` already exists:
  - **Overwrite** it (this file is the exception to the “no overwrites” rule).
- `--graceful`:
  - Behaves like the stdout TSV, but for the aggregated file:
    - Without `--graceful`, skip failed rows.
    - With `--graceful`, include rows for failed files with empty species.
- Exit code:
  - Highest error code among failures (0 if none; 0 if `--graceful`).

### 3.3 TSV mode (`--tsv[=HEADER]`)

Same as species-only, except used explicitly for TSV; semantics mirror species-only TSV behavior:

- Single-file:
  - One-column TSV:
    ```
    HEADER
    <species-string>
    ```
- Directory:
  - TSV with `file<TAB>HEADER` header and matching rows.
- Header default: `species` if not provided.
- Normalization of tabs/newlines in values as in §3.2.

---

## 4. HTTP & API Behavior

### 4.1 Endpoints

Default primary endpoint (kiosk rMLST DB):

- `https://rest.pubmlst.org/db/pubmlst_rmlst_seqdef_kiosk/schemes/1/sequence`

Fallback endpoint:

- `https://rest.pubmlst.org/db/pubmlst_rmlst_seqdef/schemes/1/sequence`

CLI option:

- `-u, --uri URL`:
  - Default is the kiosk endpoint.
  - If user overrides this, **no automatic fallback** is applied (fallback only applies for the default kiosk URI).

### 4.2 HTTP method and payload

- **Method**: `POST`
- **Request body**: JSON

  ```json
  {
    "base64": true,
    "details": true,
    "sequence": "<base64-encoded normalized FASTA>"
  }
  ```

- **Headers**:
  - `Content-Type: application/json`
  - `Accept: application/json`
  - `User-Agent: rmlst-cli/<version> (+https://github.com/ssi-dk/rmlst_cli; maintainer: pmat@ssi.dk)`

### 4.3 HTTP client

- Baseline implementation: **requests + Biopython**.
- Developer will also implement a **custom FASTA parser** and optionally an alternative HTTP client (e.g. `httpx`) and benchmark locally.
  - Use single-file mode and realistic test fixtures (including a synthetic large FASTA with >5,000 contigs).
  - Run each variant ~5 times per dataset.
  - Compare **end-to-end** time.
  - If one variant is ≥5% faster median, choose that variant and remove the other.
  - If within 5%, choose the variant with **fewer dependencies**.

### 4.4 Timeouts & retries

**Timeouts per attempt:**

- Connect timeout: 10 seconds.
- Read timeout: 120 seconds.
- No user-configurable timeout flag.

**Retry policy:**

- Options:
  - `--retries INTEGER` (default: 3)
  - `--retry-delay SEC` (default: 60; fixed delay)
- Retries happen on:
  - Network errors (DNS, connection reset, timeouts, etc.).
  - HTTP 5xx responses.
  - HTTP 429 responses.
- `Retry-After` response header is **ignored**; we always use the fixed delay.
- No extra delay jitter/backoff; just fixed `retry_delay`.

**Fallback to non-kiosk:**

- For the **default** kiosk endpoint only:
  - After **exhausting all retries** on the kiosk endpoint and still failing:
    - Automatically retry the entire sequence against the non-kiosk endpoint (`...pubmlst_rmlst_seqdef...`), with the same retry policy.
  - No extra stderr note is needed on fallback if it eventually succeeds.

### 4.5 TLS

- Standard TLS verification is **enabled**.
- No `--no-verify-ssl` type flag.
- If TLS handshake/verification fails, treat as a network error (code 4).

---

## 5. FASTA Handling

### 5.1 Encoding & normalization

- Input files must be decodable as UTF-8 (or ASCII):
  - If decoding fails → **invalid FASTA**, exit code **2**.
- Parsing:
  - Implementation for v1 baseline: **Biopython** (e.g. `SeqIO.parse`).
  - Later optimization may replace with a custom parser.

**Normalization for API payload:**

- For each contig:
  - Remove whitespace from sequences.
  - Uppercase to `A-Z`.
  - Convert `U` to `T`.
- Validation:
  - Only allow valid IUPAC DNA characters after normalization: `ACGTN` plus standard ambiguity codes.
  - If any char remains outside this set:
    - Treat the **whole file** as invalid FASTA.
    - Exit code **2**.
- For payload:
  - Each contig header (`>` line) preserved **exactly**.
  - Sequences unwrapped to **one line** per contig (after normalization).
- Compute contig length as the length of the normalized sequence string (no whitespace).

### 5.2 Sorting and trimming (5,000-contig rule)

- The rMLST API only supports up to **5,000 contigs per request**.
- Sorting:
  - Before applying trimming, sort all contigs by:
    1. **Length descending** (longest first).
    2. **Header lexicographically ascending** as tie-breaker (if same length).
- The 5,000-contig behavior:

  - **With `--trim-to-5000`:**
    - Always:
      - Sort as above.
      - If more than 5,000 contigs:
        - Keep only the top 5,000, drop the rest.
      - If 5,000 or fewer:
        - Keep all, but still sorted by length/tie-breaker.
  - **Without `--trim-to-5000`:**
    - If contigs > 5,000:
      - Do not call the API.
      - Error: exit code **3**.
      - Stderr: `more than 5000 contigs; use --trim-to-5000`.
    - If ≤ 5,000:
      - Still sort as above.
      - No trimming.

### 5.3 Valid vs invalid FASTA

**Valid FASTA file:**

- Decodable as UTF-8.
- At least one sequence record.
- Headers present (standard FASTA format).
- Normalized sequences contain only valid IUPAC DNA characters (after `U→T`).

**Invalid FASTA conditions:**

- File unreadable (permissions, missing).
- Decoding error.
- No sequences found.
- Sequence characters fail validation.
- For directory mode: no matching `.fa`/`.fasta` files is treated as invalid input (exit code 2).

Exit code for invalid FASTA or input issues: **2**.

---

## 6. Exit Codes

- **0** – Success.
- **1** – Unexpected error (uncaught exception or internal logic error).
- **2** – Input/usage error:
  - Invalid FASTA (see 5.3).
  - No `.fa`/`.fasta` files in directory input.
  - Invalid combination of CLI options (e.g., both `--tsv` and `--species-only`, or `--output`+`--outdir`, or dir + output file).
- **3** – Too many contigs (>5000) without `--trim-to-5000`.
- **4** – Network error after all retries.
- **5** – HTTP error (non-200) or invalid JSON.
- **6** – Reserved; not used in v1 (no-match is treated as success).
- **7** – Filesystem I/O error:
  - Cannot create directory or file.
  - Permission denied.
  - Disk full, etc.
- **130** – Termination by SIGINT (Ctrl-C) in directory mode, where we stop **immediately** and do not print the summary line.

### 6.1 Error messages on stderr

Short, one-sentence messages:

- Code 2: `invalid FASTA or no sequences`
- Code 3: `more than 5000 contigs; use --trim-to-5000`
- Code 4: `network error after <N> retries`
- Code 5: `HTTP error <status> or invalid JSON`
- Code 7: `filesystem error`
- Code 1: `unexpected error`

`--debug` flag can augment this with a full traceback and (for HTTP errors) up to ~1 KB of response body.

---

## 7. Graceful mode

Option:

- `--graceful`

Behavior:

- CLI exits with **0** even when individual files fail.
- Output is an “empty” value:

  - **Single-file JSON**:
    - Output: `{}`.
  - **Single-file species-only (no TSV)**:
    - Output: empty line.
  - **Single-file TSV species-only / TSV**:
    - Header line + empty data line.
  - **Directory JSON**:
    - Use wrapped array format (`{"file":..., "result":{...}}`).
    - Failed files: `{"file":"<basename>", "result": null}`.
  - **Directory TSV**:
    - All files get a row.
    - Failed files: `file<TAB>` (empty species).

- With `--graceful`, exit code is **0**.

---

## 8. Directory behavior, progress & summary

### 8.1 Progress output (stderr)

Only when `--outdir` is used (directory mode or single-file mode). For directory mode:

- For each file:
  - Success: `[OK] <basename>`
  - Failure: `[ERR code=<n>] <basename>: <short message>`
  - Skip: `[SKIP] <basename>_rmlst.json (exists)` (or appropriate filename)
- Final line:
  - `Done: <ok> ok, <failed> failed, <skipped> skipped.`

In **stdout-only** mode (no `--outdir`):

- On success, **no stderr output**.
- Only errors (and debug output if `--debug`).

### 8.2 Inter-file delay

- In directory mode, there is a fixed **1 second sleep** between processing each file.
- No flag to modify or disable this.

### 8.3 Ctrl-C behavior

- On Ctrl-C (SIGINT) in directory mode:
  - Stop immediately.
  - Do **not** print the summary line.
  - Exit code **130**.

---

## 9. Python API

Module: `rmlst_cli.api`

### 9.1 Functions

#### 9.1.1 `identify`

```python
def identify(
    fasta_path: str,
    *,
    uri: str = DEFAULT_URI,
    trim_to_5000: bool = False,
    graceful: bool = False,
    retries: int = 3,
    retry_delay: int = 60,
) -> dict:
    ...
```

Behavior:

- Mirrors single-file CLI semantics:
  - FASTA parsing, normalization, validation, sorting, trimming.
  - HTTP request with retries and fallback for default URIs.
- On success:
  - Returns the raw API JSON (`dict`).
- On failure:
  - If `graceful=False`:
    - Raises Python exceptions corresponding to CLI exit categories (e.g., custom exceptions for invalid FASTA, network error, etc.).
  - If `graceful=True`:
    - Returns `{}` (empty dict) instead of raising.
- No CLI-only options (like TSV, `--tsv`, etc.) apply here.

#### 9.1.2 `identify_dir`

```python
from typing import Iterator, Tuple, Dict

def identify_dir(
    dir_path: str,
    *,
    uri: str = DEFAULT_URI,
    trim_to_5000: bool = False,
    graceful: bool = False,
    retries: int = 3,
    retry_delay: int = 60,
) -> Iterator[Tuple[str, Dict]]:
    ...
```

Behavior:

- Mirrors directory mode semantics:
  - Directory scanning rules as in §2.2.
  - For each valid FASTA file (in alphabetical order):
    - IF `graceful=False`:
      - On a per-file failure → **raise** immediately.
      - The iterator ends with exception.
    - IF `graceful=True`:
      - On per-file failure, yield `(basename, {})` and continue.
- If the directory has **no valid inputs** (`.fa`/`.fasta` files):
  - Raise immediately (corresponds to CLI exit code 2).
- Each success yields `(basename, api_json_dict)`.

#### 9.1.3 `extract_species`

```python
def extract_species(api_json: dict) -> str:
    ...
```

- Implements the species extraction rules in §2.3.2.
- Returns a comma-separated string of unique species, ordered by descending probability.
- Returns `""` if no predictions.

### 9.2 Error mapping

- API raises Python exceptions instead of returning error objects or exit codes (except with `graceful=True`, where `{}` is returned).
- Mapping of exceptions to CLI exit codes is internal but should be documented in the code and tests.

---

## 10. Project Layout

Proposed layout:

```text
rmlst_cli/
├─ src/
│  └─ rmlst_cli/
│     ├─ __init__.py          # __version__ from hatch-vcs, API re-exports
│     ├─ cli.py               # Click CLI implementation
│     ├─ api.py               # identify, identify_dir, extract_species
│     ├─ http.py              # HTTP client and retry/fallback logic
│     ├─ fasta.py             # FASTA parsing, validation, sort/trim
│     ├─ io.py                # Directory scanning, file/directory resolution
│     ├─ formats.py           # JSON/TSV rendering, normalization
│     └─ types.py             # Optional typed models
├─ tests/
│  ├─ test_cli.py
│  ├─ test_api.py
│  ├─ fixtures/
│  │  ├─ small_*.fasta        # Provided by maintainer
│  │  └─ large_synthetic.fasta
│  └─ helpers.py
├─ README.md
├─ LICENSE
├─ pyproject.toml
├─ pixi.toml
├─ .pre-commit-config.yaml
└─ .github/workflows/ci.yml
```

---

## 11. Packaging & Tooling

### 11.1 Packaging

- Build backend: **Hatchling**.
- Versioning: **hatch-vcs** derived from Git tags.
  - Tags: `vMAJOR.MINOR` (e.g. `v1.0`).
- `requires-python = ">=3.9,<3.15"`.

**Entry points (console_scripts):**

- `rmlst = rmlst_cli.cli:main`
- `rmlst-cli = rmlst_cli.cli:main`

### 11.2 Distribution

- **PyPI**: `rmlst-cli`
  - GitHub Actions workflow:
    - Test on Python 3.9–3.14 (Linux, macOS, Windows).
    - Build sdist + wheel.
    - On tag `v*`, publish to PyPI using `PYPI_API_TOKEN` secret.
- **Bioconda**:
  - Manual PR to `bioconda-recipes`, generated from tagged releases.
  - Platforms: `linux-64`, `osx-64`, `osx-arm64`.
  - `test:` section (offline) runs:
    - `rmlst --version`
    - `rmlst --help`.

### 11.3 Dev tooling

- **Pixi** (primary dev environment):
  - `pixi.toml` with tasks:
    - `pixi run test` → `pytest -q`
    - `pixi run lint` → `ruff check .`
    - `pixi run fmt` → `black .`
    - `pixi run typecheck` → `mypy src/rmlst_cli`
    - `pixi run build` → `hatch build`
    - `pixi run release` → local steps; actual publish via CI on tag.
- **Pre-commit**:
  - `.pre-commit-config.yaml` with:
    - `ruff`
    - `black`
    - `mypy` (or run via Pixi task).

---

## 12. README Structure

Keep README concise and to the point, with the following sections:

1. **Install**
   - `pip install rmlst-cli`
   - `uv tool install rmlst-cli`
   - `conda install -c bioconda rmlst-cli`
   - `pixi add -c bioconda rmlst-cli`
2. **Quickstart**
   - Single FASTA example.
   - Directory example.
3. **Output modes**
   - Full JSON, `--species-only[=HEADER]`, `--tsv[=HEADER]`.
4. **Examples** (includes 5,000-contig trimming example)
5. **Exit codes**
   - Table mapping codes to meaning.
6. **Python API usage**
   - `identify`, `identify_dir`, `extract_species`.

Use the example block already agreed on in the conversation.

---

## 13. License & Metadata

- License: **MIT**
  - Year: **2025**
  - Copyright:
    - `Copyright (c) 2025 Povilas Matusevicius`
- `pyproject.toml` metadata:
  - `authors`:
    - `Povilas Matusevicius <pmat@ssi.dk>`
  - `maintainers` similar.
  - `project.urls`:
    - `Homepage`: `https://github.com/ssi-dk/rmlst_cli`
    - `Source`: `https://github.com/ssi-dk/rmlst_cli`
    - `Issues`: `https://github.com/ssi-dk/rmlst_cli/issues`
