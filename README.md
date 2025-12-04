# rmlst-cli

`rmlst-cli` is a simple tool to use the rMLST API through the command line.

## Install

```bash
pip install rmlst-cli
# or
uv tool install rmlst-cli
# or
conda install -c bioconda rmlst-cli
# or
pixi add -c bioconda rmlst-cli
```

## Quickstart

**Single FASTA file:**

```bash
rmlst -f sample.fasta
```

**Directory of FASTA files:**

```bash
rmlst -d ./fastas/ -O ./results/
```

## Output modes

- **Full JSON** (default):

  ```bash
  rmlst -f sample.fasta
  ```

- **Species only**:

  ```bash
  rmlst -f sample.fasta --species-only
  # With header
  rmlst -f sample.fasta --species-only="Species"
  ```

- **TSV**:

  ```bash
  rmlst -f sample.fasta --tsv
  ```

## Examples

**Trim to 5000 contigs:**

```bash
rmlst -f large.fasta --trim-to-5000
```

**Graceful failure (continue on error):**

```bash
rmlst -d ./fastas/ --graceful
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | Unexpected error |
| 2    | Input/usage error (invalid FASTA, empty dir, etc.) |
| 3    | Too many contigs (>5000) without --trim-to-5000 |
| 4    | Network error after retries |
| 5    | HTTP error or invalid JSON |
| 7    | Filesystem error |
| 130  | Interrupted (Ctrl-C) |

## Python API usage

```python
from rmlst_cli import api

# Single file
try:
    result = api.identify("sample.fasta")
    print(result)
except Exception as e:
    print(f"Error: {e}")

# Directory
for basename, result in api.identify_dir("./fastas/", graceful=True):
    print(f"{basename}: {result}")

# Extract species
from rmlst_cli.formats import extract_species
species = extract_species(result)
```
