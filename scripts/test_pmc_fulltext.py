#!/usr/bin/env python3
"""Tests for pmc_fulltext.py — uses mocked HTTP responses."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from pmc_fulltext import (
    pmid_to_pmcid,
    fetch_pmc_xml,
    extract_tables_from_xml,
    parse_table_element,
)


SAMPLE_ID_CONVERTER_RESPONSE = json.dumps({
    "records": [
        {"pmid": "12345678", "pmcid": "PMC7654321"},
        {"pmid": "87654321", "errmsg": "not found"},
    ]
})

SAMPLE_PMC_XML = """<?xml version="1.0"?>
<pmc-articleset>
<article>
<body>
<sec><title>Results</title>
<p>The primary outcome occurred in 45 of 230 patients (19.6%) in the treatment group
and 67 of 225 (29.8%) in the control group.</p>
<table-wrap id="tab1">
<label>Table 1</label>
<caption><title>Baseline characteristics</title></caption>
<table>
<thead><tr><th>Variable</th><th>Treatment (n=230)</th><th>Control (n=225)</th></tr></thead>
<tbody>
<tr><td>Age, mean (SD)</td><td>62.3 (11.2)</td><td>63.1 (10.8)</td></tr>
<tr><td>Male, n (%)</td><td>142 (61.7)</td><td>138 (61.3)</td></tr>
</tbody>
</table>
</table-wrap>
</sec>
</body>
</article>
</pmc-articleset>"""


class TestPmidToPmcid(unittest.TestCase):
    @patch("pmc_fulltext.urllib.request.urlopen")
    def test_converts_pmids(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_ID_CONVERTER_RESPONSE.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = pmid_to_pmcid(["12345678", "87654321"])
        self.assertEqual(result["12345678"], "PMC7654321")
        self.assertNotIn("87654321", result)


class TestExtractTables(unittest.TestCase):
    def test_extract_tables_from_xml(self):
        tables = extract_tables_from_xml(SAMPLE_PMC_XML)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["label"], "Table 1")
        self.assertEqual(tables[0]["caption"], "Baseline characteristics")
        self.assertEqual(len(tables[0]["rows"]), 2)
        self.assertEqual(tables[0]["headers"], ["Variable", "Treatment (n=230)", "Control (n=225)"])


if __name__ == "__main__":
    unittest.main()
