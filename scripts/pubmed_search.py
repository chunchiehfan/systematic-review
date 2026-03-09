#!/usr/bin/env python3
"""
PubMed literature search using NCBI E-utilities.
Fetches article metadata (title, abstract, authors, year, journal) for a given query.

Usage:
    python pubmed_search.py "search query" --max-results 500 --api-key KEY --output results.json
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

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def esearch(query: str, max_results: int = 500, api_key: str = None) -> list[str]:
    """Search PubMed and return a list of PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key

    url = f"{BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Error connecting to PubMed: {e}", file=sys.stderr)
        sys.exit(1)

    result = data.get("esearchresult", {})
    pmids = result.get("idlist", [])
    total = result.get("count", "unknown")
    print(f"Total records matching query: {total}")
    print(f"Retrieving up to {max_results} records ({len(pmids)} returned)")
    return pmids


def efetch_batch(pmids: list[str], api_key: str = None) -> str:
    """Fetch PubMed XML for a batch of PMIDs."""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key

    url = f"{BASE_URL}/efetch.fcgi?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"Error fetching batch: {e}", file=sys.stderr)
        return ""


def parse_article(article_el: ET.Element) -> dict:
    """Parse a single PubmedArticle element into a dict."""
    medline = article_el.find("MedlineCitation")
    if medline is None:
        return {}

    article = medline.find("Article")
    if article is None:
        return {}

    # PMID
    pmid_el = medline.find("PMID")
    pmid = pmid_el.text if pmid_el is not None else ""

    # Title (strip tags like <i>)
    title_el = article.find("ArticleTitle")
    title = "".join(title_el.itertext()) if title_el is not None else ""

    # Abstract (handle structured abstracts with label attributes)
    abstract_parts = article.findall(".//AbstractText")
    abstract_segments = []
    for el in abstract_parts:
        label = el.get("Label", "")
        text = "".join(el.itertext()).strip()
        if label:
            abstract_segments.append(f"{label}: {text}")
        elif text:
            abstract_segments.append(text)
    abstract = " ".join(abstract_segments)

    # Authors
    authors = []
    author_list = article.find("AuthorList")
    if author_list is not None:
        for author in author_list.findall("Author"):
            last = author.findtext("LastName", "")
            fore = author.findtext("ForeName", "")
            collective = author.findtext("CollectiveName", "")
            if last:
                authors.append(f"{last} {fore}".strip())
            elif collective:
                authors.append(collective)

    # Year
    pub_date = article.find(".//PubDate")
    year = ""
    if pub_date is not None:
        year = pub_date.findtext("Year", "")
        if not year:
            medline_date = pub_date.findtext("MedlineDate", "")
            year = medline_date[:4] if medline_date else ""

    # Journal
    journal = article.findtext(".//Journal/Title", "")

    # DOI
    doi = ""
    for id_el in article_el.findall(".//ArticleId"):
        if id_el.get("IdType") == "doi":
            doi = id_el.text or ""
            break

    # Publication types
    pub_types = [pt.text for pt in article.findall(".//PublicationType") if pt.text]

    # MeSH terms
    mesh_terms = [
        desc.text
        for desc in medline.findall(".//MeshHeading/DescriptorName")
        if desc.text
    ]

    return {
        "pmid": pmid,
        "title": title.strip(),
        "abstract": abstract.strip(),
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "publication_types": pub_types,
        "mesh_terms": mesh_terms[:10],  # First 10 MeSH terms
    }


def efetch_all(pmids: list[str], api_key: str = None, batch_size: int = 100) -> list[dict]:
    """Fetch all articles in batches."""
    articles = []
    total = len(pmids)
    # Rate limiting: 10 req/s with key, 3 req/s without
    delay = 0.1 if api_key else 0.35

    for i in range(0, total, batch_size):
        batch = pmids[i : i + batch_size]
        end = min(i + batch_size, total)
        print(f"  Fetching records {i+1}–{end} of {total}...", end="\r")

        xml_data = efetch_batch(batch, api_key)
        if not xml_data:
            continue

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            print(f"\nXML parse error for batch {i//batch_size + 1}: {e}", file=sys.stderr)
            continue

        for article_el in root.findall("PubmedArticle"):
            parsed = parse_article(article_el)
            if parsed.get("pmid"):
                articles.append(parsed)

        time.sleep(delay)

    print(f"\nFetched {len(articles)} article records.")
    return articles


def main():
    parser = argparse.ArgumentParser(
        description="Search PubMed and export results as JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pubmed_search.py "SGLT2 inhibitors AND heart failure" --max-results 300
  python pubmed_search.py "metformin AND type 2 diabetes AND HbA1c" --api-key MYKEY --output results.json
        """,
    )
    parser.add_argument("query", help="PubMed search query (use PubMed syntax)")
    parser.add_argument(
        "--max-results", type=int, default=500, help="Maximum records to retrieve (default: 500)"
    )
    parser.add_argument("--api-key", help="NCBI API key (increases rate limit to 10 req/s)")
    parser.add_argument(
        "--output", default="pubmed_results.json", help="Output JSON file (default: pubmed_results.json)"
    )
    args = parser.parse_args()

    print(f"Searching PubMed: {args.query}")
    pmids = esearch(args.query, args.max_results, args.api_key)

    if not pmids:
        print("No results found. Check your search query.")
        sys.exit(0)

    print("Fetching article details...")
    articles = efetch_all(pmids, args.api_key)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(articles, indent=2, ensure_ascii=False))
    print(f"Saved {len(articles)} articles to {output_path}")


if __name__ == "__main__":
    main()
