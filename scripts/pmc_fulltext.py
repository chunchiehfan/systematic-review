#!/usr/bin/env python3
"""
Fetch full-text articles from PubMed Central and extract structured tables.

Uses NCBI ID Converter API to map PMIDs → PMCIDs, then efetch for full-text XML.
Extracts all <table-wrap> elements into structured JSON.

Usage:
    python pmc_fulltext.py pubmed_results.json --output-dir fulltext_data/ --api-key KEY
    python pmc_fulltext.py --pmids 12345678 87654321 --output-dir fulltext_data/
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def pmid_to_pmcid(pmids: list[str], api_key: str = None) -> dict[str, str]:
    """Convert PMIDs to PMCIDs using NCBI ID Converter. Returns {pmid: pmcid} for found entries."""
    mapping = {}
    batch_size = 200
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = {
            "ids": ",".join(batch),
            "format": "json",
            "tool": "systematic-review-skill",
            "email": "systematic-review@example.com",
        }
        if api_key:
            params["api_key"] = api_key
        url = f"{CONVERTER_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read())
            for record in data.get("records", []):
                pmcid = record.get("pmcid")
                pmid = record.get("pmid")
                if pmcid and pmid:
                    mapping[pmid] = pmcid
        except urllib.error.URLError as e:
            print(f"  Warning: ID converter batch failed: {e}", file=sys.stderr)
        time.sleep(0.35 if not api_key else 0.1)
    return mapping


def fetch_pmc_xml(pmcid: str, api_key: str = None) -> str:
    """Fetch full-text XML for a single PMC article."""
    params = {
        "db": "pmc",
        "id": pmcid,
        "rettype": "full",
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{EFETCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"  Warning: Failed to fetch {pmcid}: {e}", file=sys.stderr)
        return ""


def parse_table_element(table_wrap: ET.Element) -> dict:
    """Parse a <table-wrap> element into structured data."""
    label_el = table_wrap.find("label")
    label = label_el.text.strip() if label_el is not None and label_el.text else ""

    caption_el = table_wrap.find(".//caption/title")
    if caption_el is None:
        caption_el = table_wrap.find(".//caption")
    caption = "".join(caption_el.itertext()).strip() if caption_el is not None else ""

    table_el = table_wrap.find(".//table")
    if table_el is None:
        return {"label": label, "caption": caption, "headers": [], "rows": []}

    headers = []
    thead = table_el.find("thead")
    if thead is not None:
        for th in thead.findall(".//th"):
            headers.append("".join(th.itertext()).strip())
        if not headers:
            first_row = thead.find("tr")
            if first_row is not None:
                for td in first_row.findall("td"):
                    headers.append("".join(td.itertext()).strip())

    rows = []
    tbody = table_el.find("tbody")
    row_elements = tbody.findall("tr") if tbody is not None else table_el.findall("tr")
    for tr in row_elements:
        cells = []
        for cell in tr.findall("td"):
            cells.append("".join(cell.itertext()).strip())
        if not cells:
            for cell in tr.findall("th"):
                cells.append("".join(cell.itertext()).strip())
        if cells:
            rows.append(cells)

    return {"label": label, "caption": caption, "headers": headers, "rows": rows}


def extract_tables_from_xml(xml_text: str) -> list[dict]:
    """Extract all tables from a PMC full-text XML string."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tables = []
    for table_wrap in root.findall(".//table-wrap"):
        parsed = parse_table_element(table_wrap)
        tables.append(parsed)
    return tables


def extract_sections_text(xml_text: str) -> list[dict]:
    """Extract section titles and text from PMC XML body."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    sections = []
    for sec in root.findall(".//body//sec"):
        title_el = sec.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        paragraphs = []
        for p in sec.findall("p"):
            text = "".join(p.itertext()).strip()
            if text:
                paragraphs.append(text)
        if title or paragraphs:
            sections.append({"title": title, "text": "\n".join(paragraphs)})
    return sections


def process_articles(pmids: list[str], output_dir: Path, api_key: str = None) -> dict:
    """
    Fetch full text for a list of PMIDs and save structured data.
    Returns summary: {fetched: [...], no_fulltext: [...]}.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting {len(pmids)} PMIDs to PMCIDs...")
    pmcid_map = pmid_to_pmcid(pmids, api_key)
    print(f"  Found {len(pmcid_map)} articles in PMC out of {len(pmids)}")

    fetched = []
    no_fulltext = []
    delay = 0.1 if api_key else 0.35

    for pmid in pmids:
        pmcid = pmcid_map.get(pmid)
        if not pmcid:
            no_fulltext.append(pmid)
            continue

        print(f"  Fetching {pmcid} (PMID: {pmid})...", end="\r")
        xml_text = fetch_pmc_xml(pmcid, api_key)
        if not xml_text:
            no_fulltext.append(pmid)
            continue

        tables = extract_tables_from_xml(xml_text)
        sections = extract_sections_text(xml_text)

        article_data = {
            "pmid": pmid,
            "pmcid": pmcid,
            "tables": tables,
            "sections": sections,
        }

        out_file = output_dir / f"{pmid}.json"
        out_file.write_text(json.dumps(article_data, indent=2, ensure_ascii=False))
        fetched.append(pmid)
        time.sleep(delay)

    print(f"\nFetched full text for {len(fetched)} articles. {len(no_fulltext)} not available in PMC.")
    return {"fetched": fetched, "no_fulltext": no_fulltext}


def main():
    parser = argparse.ArgumentParser(
        description="Fetch PMC full-text articles and extract structured tables.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("input_json", nargs="?", help="pubmed_results.json or screening_results.json")
    group.add_argument("--pmids", nargs="+", help="Space-separated PMIDs")
    parser.add_argument("--output-dir", default="fulltext_data", help="Output directory (default: fulltext_data/)")
    parser.add_argument("--api-key", help="NCBI API key")
    args = parser.parse_args()

    if args.pmids:
        pmids = args.pmids
    else:
        input_path = Path(args.input_json)
        if not input_path.exists():
            print(f"Error: {input_path} not found.", file=sys.stderr)
            sys.exit(1)
        with open(input_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            pmids = [str(item.get("pmid", "")) for item in data if item.get("pmid")]
        else:
            pmids = data.get("pmids", [])

    output_dir = Path(args.output_dir)
    summary = process_articles(pmids, output_dir, args.api_key)

    no_ft_path = output_dir / "no_fulltext.json"
    no_ft_path.write_text(json.dumps(summary["no_fulltext"], indent=2))
    print(f"No-fulltext PMIDs saved to {no_ft_path}")


if __name__ == "__main__":
    main()
