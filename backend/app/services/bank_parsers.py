"""Detect-and-parse known bank statement formats into structured transaction lines.

Strategy: cheap signature match first, then format-specific regex parser.
Returning [] (empty list) means "not a recognized format" — caller treats as
a normal RAG-only document.
"""
import re
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional


# Map textual months to month numbers (Capital One uses "Oct 1" style).
_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


@dataclass
class TxnLine:
    ordinal: int
    posted_date: Optional[str]    # ISO yyyy-mm-dd, or None if unparseable
    description: str
    category: Optional[str]
    direction: str                # "debit" | "credit"
    amount: float                 # always positive; sign implied by direction
    balance_after: Optional[float]
    raw_line: str
    source_format: str            # e.g. "capital_one"

    def to_dict(self) -> dict:
        return asdict(self)


def detect_and_parse(text: str) -> list[TxnLine]:
    """Try each known format. Returns parsed lines from the first match, or []."""
    if _looks_like_capital_one(text):
        return _parse_capital_one(text)
    return []


# ── Capital One ────────────────────────────────────────────────────────────────

_CAPONE_SIG = re.compile(r"capitalone\.com.*?STATEMENT\s+PERIOD", re.IGNORECASE | re.DOTALL)


def _looks_like_capital_one(text: str) -> bool:
    return bool(_CAPONE_SIG.search(text))


# A transaction line in Capital One PDFs (after pypdf extraction) looks like:
#
#   Oct 1 Zelle money received from SACHIN SIMPSON Credit + $1,000.00 $1,331.57
#   Oct 1 Withdrawal from Rocket Savings Deposit Debit - $5.00 $1,326.57
#   Oct 9 Withdrawal from WELLS FARGO AUTO DRAFT Debit - $483.26 $...
#
# Description sometimes contains a city/state suffix and may wrap across lines
# (pypdf inserts a \n mid-merchant-name). We match the date+amount anchor and
# then trust the description span between them. The category column is the
# token immediately before "Debit"/"Credit" — but it's often empty/absent.
_CAPONE_TXN = re.compile(
    r"""
    ^\s*
    (?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\s+
    (?P<day>\d{1,2})\s+
    (?P<desc>.+?)\s+
    (?P<dir>Debit|Credit)\s+
    [-+]\s+
    \$(?P<amt>[\d,]+\.\d{2})
    (?:\s+\$(?P<bal>[\d,]+\.\d{2}))?
    \s*$
    """,
    re.VERBOSE | re.MULTILINE,
)

# Statement period pulls the year (Capital One omits the year on each line).
_CAPONE_PERIOD = re.compile(
    r"STATEMENT\s+PERIOD\s+(?:Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?)\s+\d+\s*-\s*"
    r"(?P<endmon>Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?)\s+\d+,?\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)


def _parse_capital_one(text: str) -> list[TxnLine]:
    # PDF extraction sometimes splits a description across lines; fold soft wraps
    # so the regex anchor sees the whole line. We collapse lines that DON'T end
    # in a balance/amount pattern into the next line.
    folded = _fold_capital_one_lines(text)

    year_m = _CAPONE_PERIOD.search(text)
    year = int(year_m.group("year")) if year_m else None

    out: list[TxnLine] = []
    for i, m in enumerate(_CAPONE_TXN.finditer(folded)):
        mon_num = _MONTHS[m.group("mon")[:3].title()]
        day = int(m.group("day"))
        try:
            iso = date(year, mon_num, day).isoformat() if year else None
        except ValueError:
            iso = None

        desc_raw = re.sub(r"\s+", " ", m.group("desc")).strip()
        # Strip a trailing single-word "category" token if present
        # (Capital One's "CATEGORY" column is usually blank, but when present it's
        # one token like "Other" / "Income" between the merchant and Debit/Credit).
        category = None
        # Heuristic: if last token of desc is a known category-ish single word AND
        # the rest still looks like a description, peel it off.
        # Skipping for MVP — leave category None; description retains the text.

        amt = float(m.group("amt").replace(",", ""))
        bal = float(m.group("bal").replace(",", "")) if m.group("bal") else None
        direction = m.group("dir").lower()

        out.append(TxnLine(
            ordinal=i,
            posted_date=iso,
            description=desc_raw,
            category=category,
            direction=direction,
            amount=amt,
            balance_after=bal,
            raw_line=m.group(0).strip(),
            source_format="capital_one",
        ))
    return out


_FOLD_SKIP = re.compile(
    r"\b(STATEMENT\s+PERIOD|Page\s+\d+\s+of\s+\d+|TOTAL\s+ENDING\s+BALANCE|"
    r"Account\s+Summary|Cashflow\s+Summary|DATE\s+DESCRIPTION|"
    r"capitalone\.com)\b",
    re.IGNORECASE,
)
# A "Mon N - Mon N" range like "Oct 1 - Oct 31" is the statement period header,
# never a transaction even though it starts with a month token.
_RANGE_HEADER = re.compile(
    r"^\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\s+\d+\s*-\s*"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\s+\d+",
    re.IGNORECASE,
)
_MAX_FOLD_LINES = 3


def _fold_capital_one_lines(text: str) -> str:
    """Capital One PDFs sometimes wrap a single transaction across two lines
    (typically a long merchant name). A 'real' line ends in a $amount (and
    optionally another $balance). Lines that don't end in $X.XX are treated as
    continuations and joined to the next line — bounded so we don't swallow
    unrelated header text past a page break."""
    lines = text.splitlines()
    out: list[str] = []
    buf = ""
    folded_count = 0
    end_amt = re.compile(r"\$\d[\d,]*\.\d{2}\s*$")
    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            if buf:
                out.append(buf)
                buf = ""
                folded_count = 0
            out.append("")
            continue
        starts_txn = bool(re.match(r"\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\s+\d", s))
        # Never fold past page/section headers.
        is_skip = bool(_FOLD_SKIP.search(s)) or bool(_RANGE_HEADER.match(s))
        if buf:
            if is_skip or folded_count >= _MAX_FOLD_LINES:
                # Emit buffered (won't match the txn regex, no harm) and start fresh.
                out.append(buf)
                buf = ""
                folded_count = 0
                out.append(s)
            else:
                buf = buf + " " + s.lstrip()
                folded_count += 1
                if end_amt.search(buf):
                    out.append(buf)
                    buf = ""
                    folded_count = 0
        elif starts_txn and not is_skip and not end_amt.search(s):
            buf = s
            folded_count = 0
        else:
            out.append(s)
    if buf:
        out.append(buf)
    return "\n".join(out)
