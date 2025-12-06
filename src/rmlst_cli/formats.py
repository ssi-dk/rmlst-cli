import json
from typing import Dict, Any


def extract_species(api_json: Dict[str, Any]) -> str:
    """
    Extracts species from the API JSON response.
    Returns a comma-separated string of unique species, ordered by descending support/probability.
    """
    predictions = api_json.get("taxon_prediction", [])
    if not predictions:
        return ""

    # Collect (taxon, support) tuples
    # Support might be missing, default to 0
    species_list = []
    for pred in predictions:
        taxon = pred.get("taxon")
        if taxon:
            support = pred.get("support", 0)
            # Try to cast support to float/int just in case
            try:
                support = float(support)
            except (ValueError, TypeError):
                support = 0
            species_list.append((taxon, support))

    if not species_list:
        return ""

    # Deduplicate while keeping max support for each taxon
    unique_species: dict[str, float] = {}
    for taxon, support in species_list:
        if taxon in unique_species:
            unique_species[taxon] = max(unique_species[taxon], support)
        else:
            unique_species[taxon] = support

    # Sort by support desc, then taxon asc
    sorted_species = sorted(unique_species.items(), key=lambda x: (-x[1], x[0]))

    return ",".join([s[0] for s in sorted_species])


def format_json(data: Any) -> str:
    """
    Format data as pretty JSON with 2-space indent.
    """
    return json.dumps(data, indent=2)


def format_tsv_row(file_name: str, value: str) -> str:
    """
    Format a TSV row: file<TAB>value.
    Normalizes value (tabs/newlines -> space).
    """
    # Normalize value
    # Replace tab and newline with space
    norm_value = value.replace("\t", " ").replace("\n", " ")
    # Strip outer whitespace
    norm_value = norm_value.strip()

    return f"{file_name}\t{norm_value}"
