import unittest
from datetime import date

from nifty200_pipeline.membership import (
    ChangeEvent,
    extract_constituents_from_pdf_text,
    extract_effective_date,
    extract_events_from_press_release,
)


JAN_2015_SAMPLE = """
Symbol Security Name Industry Close Price Index Mcap
(Rs. Crores)
Weightage

Constituents of CNX 200
January 30, 2015
ABB ABB India Ltd. ELECTRICAL EQUIPMENT 1283.90 0.176802
ADANIPORTS Adani Ports and Special Economic
Zone Ltd. SHIPPING 341.05 0.4517650
DHFL Dewan Housing Finance Corporation
Ltd. FINANCE - HOUSING 470.75 0.072617
JPPOWER Jaiprakash Power Ventures Ltd POWER 12.05 0.02826
M&MFIN Mahindra & Mahindra Financial
Services Ltd. FINANCE 255.25 0.186960
"""


PRESS_RELEASE_2025_SAMPLE = """
PRESS RELEASE
Mumbai, February 21, 2025
Replacements in indices
The Index Maintenance Sub-Committee (Equity) of NSE Indices Limited has decided to make
replacement of stocks in various indices as part of its periodic review as listed hereunder. These
changes shall become effective from March 28, 2025 (close of March 27, 2025).

l) Nifty 200

The following companies are being excluded:

Sr. No. Company Name Symbol
1 Balkrishna Industries Ltd. BALKRISIND
2 Delhivery Ltd. DELHIVERY

The following companies are being included:

Sr. No. Company Name Symbol
1 Bajaj Housing Finance Ltd. BAJAJHFL
2 Swiggy Ltd. SWIGGY

m) Nifty LargeMidcap 250
"""


PRESS_RELEASE_NUMERIC_BOUNDARY_SAMPLE = """
PRESS RELEASE
Replacements in indices
These changes shall become effective from March 28, 2024 (close of March 27, 2024).

12) Nifty 200

The following companies are being excluded:

Sr. No. Company Name Symbol
1 AWL Adani Wilmar Ltd. AWL

The following companies are being included:

Sr. No. Company Name Symbol
1 Jio Financial Services Ltd. JIOFIN

13) Nifty LargeMidcap 250

The following companies are being included:

Sr. No. Company Name Symbol
1 Aarti Drugs Ltd. AARTIDRUGS
"""


JIO_ONE_OFF_SAMPLE = """
PRESS RELEASE
Mumbai, September 5, 2023
Exclusion of Jio Financial Services Limited from Nifty indices
In accordance with the index methodology, the Index Maintenance Sub-Committee (Equity) of NSE
Indices Ltd. has decided to exclude JIOFIN from various indices as listed hereunder effective from
September 7, 2023 (close of September 6, 2023).

Sr. No. Index Name
1 Nifty 50
2 Nifty 100
3 Nifty 200
4 Nifty 500
"""


class MembershipParserTests(unittest.TestCase):
    def test_extract_constituents_handles_wrapped_rows(self) -> None:
        rows = extract_constituents_from_pdf_text(JAN_2015_SAMPLE)
        tickers = [row["ticker"] for row in rows]
        self.assertEqual(tickers, ["ABB", "ADANIPORTS", "DHFL", "JPPOWER", "M&MFIN"])
        self.assertEqual(rows[1]["sector_coarse_pdf"], "SHIPPING")
        self.assertEqual(rows[2]["sector_coarse_pdf"], "FINANCE - HOUSING")

    def test_extract_effective_date(self) -> None:
        value = extract_effective_date(PRESS_RELEASE_2025_SAMPLE, "Replacements in indices")
        self.assertEqual(value, date(2025, 3, 28))

    def test_extract_events_from_nifty200_section(self) -> None:
        events = extract_events_from_press_release(
            PRESS_RELEASE_2025_SAMPLE,
            "Replacements in indices",
            "https://example.test/release.pdf",
        )
        normalized = {(event.effective_date, event.symbol, event.action) for event in events}
        self.assertEqual(
            normalized,
            {
                (date(2025, 3, 28), "BALKRISIND", "exclude"),
                (date(2025, 3, 28), "DELHIVERY", "exclude"),
                (date(2025, 3, 28), "BAJAJHFL", "include"),
                (date(2025, 3, 28), "SWIGGY", "include"),
            },
        )

    def test_numeric_section_boundaries_do_not_leak_other_indices(self) -> None:
        events = extract_events_from_press_release(
            PRESS_RELEASE_NUMERIC_BOUNDARY_SAMPLE,
            "Replacements in indices",
            "https://example.test/numeric.pdf",
        )
        symbols = sorted(event.symbol for event in events)
        self.assertEqual(symbols, ["AWL", "JIOFIN"])

    def test_extract_events_from_one_off_exclusion(self) -> None:
        events = extract_events_from_press_release(
            JIO_ONE_OFF_SAMPLE,
            "Exclusion of Jio Financial Services Limited from Nifty indices",
            "https://example.test/jio.pdf",
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ChangeEvent(date(2023, 9, 7), "JIOFIN", "exclude", "Exclusion of Jio Financial Services Limited from Nifty indices", "https://example.test/jio.pdf"))


if __name__ == "__main__":
    unittest.main()
