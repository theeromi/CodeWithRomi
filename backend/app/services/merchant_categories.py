"""Classify a transaction's merchant description into a coarse category, and
expand user query terms (e.g. "food", "bills") into the set of categories that
should match.

Both halves are keyword-based today: deterministic, debuggable, no LLM calls.
Order of CATEGORY_RULES matters — first match wins, so put more specific rules
above more general ones (e.g. "AMAZON PRIME" subscription before "AMAZON" shopping).
"""
import re

# Canonical category list. Anything that doesn't match a rule lands in "other".
CATEGORIES = [
    "groceries", "dining", "delivery", "subscriptions",
    "utilities", "gas", "transport", "shopping",
    "loans", "credit_card_payments", "bnpl",
    "peer_transfers", "internal_transfers",
    "atm_cash", "fees", "income",
    "healthcare", "entertainment", "other",
]

# (regex pattern, category). Patterns are matched case-insensitively against
# the merchant description. Order matters — first match wins.
CATEGORY_RULES: list[tuple[str, str]] = [
    # ── Subscriptions (must precede "AMAZON" shopping rule) ──────────────────
    (r"\bAMAZON\s*PRIME\b",                              "subscriptions"),
    (r"\bPRIME\s+VIDEO\b",                               "subscriptions"),
    (r"\bNETFLIX\b",                                     "subscriptions"),
    (r"\bSPOTIFY\b",                                     "subscriptions"),
    (r"\bAPPLE\.COM\b|\bITUNES\b|\bAPPLE\s+SERVICES\b",  "subscriptions"),
    (r"\bICLOUD\b",                                      "subscriptions"),
    (r"\bGOOGLE\s+(YOUTUBE|STORAGE|ONE|PLAY)\b",         "subscriptions"),
    (r"\bYOUTUBE\s*PREMIUM\b|\bYOUTUBETV\b|\bYOUTUBE\s+TV\b", "subscriptions"),
    (r"\bHULU\b|\bDISNEY\s*PLUS\b|\bDISNEYPLUS\b|\bDISNEY\+\b", "subscriptions"),
    (r"\bHBO\b|\bMAX\s+(SUB|MEMBERSHIP)\b|\bWARNERMEDIA\b", "subscriptions"),
    (r"\bPARAMOUNT\b|\bPEACOCK\b|\bAPPLE\s*TV\b",        "subscriptions"),
    (r"\bCRUNCHYROLL\b",                                 "subscriptions"),
    (r"\bMICROSOFT\b|\bOFFICE\s*365\b|\bMSBILL\b",       "subscriptions"),
    (r"\bADOBE\b",                                       "subscriptions"),
    (r"\bDROPBOX\b|\bNOTION\b|\bEVERNOTE\b|\bONEDRIVE\b","subscriptions"),
    (r"\bPATREON\b|\bSUBSTACK\b|\bMEDIUM\.COM\b",        "subscriptions"),
    (r"\bROCKET\s*MONEY\b",                              "subscriptions"),
    (r"\bLA\s*FITNESS\b|\bPLANET\s*FITNESS\b|\bEQUINOX\b|\bGOLD'?S\s*GYM\b", "subscriptions"),
    (r"\bNYTIMES\b|\bNEW\s+YORK\s+TIMES\b|\bWSJ\b|\bWASHINGTON\s+POST\b", "subscriptions"),

    # ── Food delivery (very specific, before generic shopping) ───────────────
    (r"\bDOORDASH\b|\bDD\s+DOORDASH\b",                  "delivery"),
    (r"\bUBER\s*EATS\b",                                 "delivery"),
    (r"\bGRUBHUB\b|\bGRUB\s*HUB\b",                      "delivery"),
    (r"\bSEAMLESS\b",                                    "delivery"),
    (r"\bPOSTMATES\b",                                   "delivery"),
    (r"\bINSTACART\b",                                   "delivery"),
    (r"\bCAVIAR\b",                                      "delivery"),

    # ── Dining (chains; merchant strings vary widely) ───────────────────────
    (r"\bSTARBUCKS\b|\bDUNKIN\b|\bDD\s*DUNKIN\b",        "dining"),
    (r"\bMCDONALD'?S?\b|\bBURGER\s*KING\b|\bWENDY'?S\b", "dining"),
    (r"\bCHIPOTLE\b|\bSWEETGREEN\b|\bCAVA\b|\bPANERA\b", "dining"),
    (r"\bSUBWAY\b|\bCHICK[- ]?FIL[- ]?A\b|\bPOPEYES\b",  "dining"),
    (r"\bTACO\s*BELL\b|\bDOMINO'?S?\b|\bDOMINO\s+S\b|\bPIZZA\s*HUT\b|\bPAPA\s*JOHN'?S\b", "dining"),
    (r"\bKITCHEN\b|\bCAFE\b|\bCAFETERIA\b|\bCAFFE\b|\bSTEAK\s*HOUSE\b|\bSEAFOOD\b|\bSUSHI\b", "dining"),
    (r"\bSHAKE\s*SHACK\b|\bFIVE\s*GUYS\b|\bIN[- ]?N[- ]?OUT\b",          "dining"),
    (r"\bRESTAURANT\b|\bDINER\b|\bBISTRO\b|\bGRILL\b|\bPIZZERIA\b",      "dining"),

    # ── Groceries ────────────────────────────────────────────────────────────
    (r"\bSHOP\s*RITE\b|\bSHOPRITE\b",                    "groceries"),
    (r"\bWHOLE\s+FOODS\b|\bAMAZON\s*FRESH\b",            "groceries"),
    (r"\bTRADER\s*JOE'?S?\b",                            "groceries"),
    (r"\bALDI\b|\bLIDL\b",                               "groceries"),
    (r"\bSTOP\s*&\s*SHOP\b|\bWEGMANS\b|\bFAIRWAY\b",     "groceries"),
    (r"\bKEY\s*FOOD\b|\bKEYFOOD\b|\bFOODTOWN\b|\bWESTERN\s+BEEF\b", "groceries"),
    (r"\bKROGER\b|\bSAFEWAY\b|\bPUBLIX\b|\bH[- ]?E[- ]?B\b",        "groceries"),
    (r"\bCOSTCO\b|\bSAM'?S?\s*CLUB\b|\bBJ'?S?\s*WHOLESALE\b",       "groceries"),
    (r"\bWALMART\s+NEIGHBORHOOD\b|\bGIANT\s+FOOD\b|\bHARRIS\s+TEETER\b", "groceries"),
    (r"\bIGA\b|\bASSOC?\s+SUPERMARKETS\b|\bC[- ]?TOWN\b",                "groceries"),
    (r"\bFOOD\s+(CORP|MART|BAZAAR|TOWN|STORE|EMPORIUM|MARKET|LION)\b",   "groceries"),
    (r"\bGROCER(?:Y|IES|S)\b|\bSUPERMARKET\b|\bDELI\b|\bBODEGA\b",       "groceries"),

    # ── Gas stations ─────────────────────────────────────────────────────────
    (r"\bSHELL\s+OIL\b|\bSHELL\s+SERVICE\b",             "gas"),
    (r"\bEXXON\b|\bMOBIL\b|\bEXXONMOBIL\b",              "gas"),
    (r"\bBP\s+OIL\b|\bBP\s*#\d+\b",                      "gas"),
    (r"\bCHEVRON\b|\bSUNOCO\b|\bCITGO\b|\bGULF\s+OIL\b|\bVALERO\b|\bSPEEDWAY\b|\bWAWA\b|\bSHEETZ\b", "gas"),
    (r"\b76\s+GAS\b|\bMURPHY\s+USA\b|\bARCO\b",          "gas"),

    # ── Rideshare / public transit ───────────────────────────────────────────
    (r"\bUBER\s+(?!EATS)\b|\bUBER\*?TRIP\b",             "transport"),
    (r"\bLYFT\b",                                        "transport"),
    (r"\bMTA\b|\bNJT\b|\bNJ\s*TRANSIT\b|\bAMTRAK\b|\bPATH\b|\bPATCO\b", "transport"),
    (r"\bAVIS\b|\bHERTZ\b|\bENTERPRISE\s+RENT\b|\bBUDGET\s+RENT\b", "transport"),

    # ── Utilities ────────────────────────────────────────────────────────────
    (r"\bPSEG\b|\bPUBLIC\s+SERVICE\b|\bCONED\b|\bCON\s*ED\b|\bCON\s+EDISON\b", "utilities"),
    (r"\bNATIONAL\s+GRID\b|\bDUKE\s+ENERGY\b|\bDOMINION\s+ENERGY\b", "utilities"),
    (r"\bOPTIMUM\b|\bCOMCAST\b|\bXFINITY\b|\bSPECTRUM\b|\bRCN\b|\bFIOS\b", "utilities"),
    (r"\bATT\s+(PAYMENT|BILL)\b|\bAT&T\b|\bT[- ]?MOBILE\b|\bVERIZON\b|\bSPRINT\b|\bMINT\s+MOBILE\b|\bGOOGLE\s+FI\b", "utilities"),
    (r"\bWATER\s+(BILL|PMT|PAYMENT)\b|\bSEWER\s+(BILL|PMT)\b|\bGAS\s+UTILITY\b|\bELEC\s+(BILL|PMT)\b", "utilities"),

    # ── BNPL (Buy Now Pay Later) ─────────────────────────────────────────────
    (r"\bAFFIRM\b",                                      "bnpl"),
    (r"\bKLARNA\b",                                      "bnpl"),
    (r"\bAFTERPAY\b|\bZIP\s*PAY\b|\bSEZZLE\b",           "bnpl"),

    # ── Loan payments ────────────────────────────────────────────────────────
    (r"\bROCKETLOANS?\b|\bUPSTART\b",                    "loans"),
    (r"\bSOFI\b|\bPROSPER\b|\bLENDINGCLUB\b",            "loans"),
    (r"\bWELLS\s+FARGO\s+AUTO\b|\bAUTO\s+(DRAFT|PYMT|PAYMENT|LOAN)\b", "loans"),
    (r"\bSALLIE\s+MAE\b|\bNAVIENT\b|\bNELNET\b|\bGREAT\s+LAKES\b", "loans"),
    (r"\bMORTGAGE\b|\bROCKET\s+MORTGAGE\b",              "loans"),
    (r"\bBEST\s+BUY\s+(AUTO\s+PYMT|FINANCING)\b",        "loans"),

    # ── Credit card payments ─────────────────────────────────────────────────
    (r"\bAPPLECARD\b|\bAPPLE\s+CARD\b",                  "credit_card_payments"),
    (r"\bCAPITAL\s*ONE\s+(MOBILE\s+)?(PMT|PAYMENT)\b",   "credit_card_payments"),
    (r"\bCHASE\s+(CARD\s+)?(PMT|PAYMENT)\b|\bAMEX\s+(EPAYMENT|PMT)\b|\bAMERICAN\s+EXPRESS\b", "credit_card_payments"),
    (r"\bDISCOVER\s+(PMT|PAYMENT|CARD)\b|\bCITI\s+CARD\b|\bSYNCHRONY\b|\bBARCLAY\b", "credit_card_payments"),

    # ── Internal transfers (within the user's own accounts) ──────────────────
    (r"\bWithdrawal\s+to\s+(?:savings|checking|360\s+Checking)\b", "internal_transfers"),
    (r"\bDeposit\s+from\s+(?:savings|checking|360\s+Checking)\b",  "internal_transfers"),
    (r"\bWithdrawal\s+from\s+Rocket\s+Savings\b",        "internal_transfers"),
    (r"\bDeposit\s+from\s+Rocket\s+Savings\b",           "internal_transfers"),
    (r"\bTransfer\s+(to|from)\b",                        "internal_transfers"),

    # ── Peer transfers (Zelle / Venmo / Cash App / PayPal P2P) ───────────────
    (r"\bZelle\s+money\s+(sent|received)\b",             "peer_transfers"),
    (r"\bVENMO\b|\bCASH\s+APP\b|\bCASHAPP\b",            "peer_transfers"),
    (r"\bPAYPAL\b",                                      "peer_transfers"),

    # ── ATM / cash ───────────────────────────────────────────────────────────
    (r"\bATM\b|\bCASH\s+WITHDRAWAL\b",                   "atm_cash"),

    # ── Fees ─────────────────────────────────────────────────────────────────
    (r"\bOVERDRAFT\b|\bRETURN\s+ITEM\s+FEE\b|\bNSF\s+FEE\b|\bSERVICE\s+FEE\b|\bMAINT(?:ENANCE)?\s+FEE\b", "fees"),
    (r"\bFOREIGN\s+TRANS(?:ACTION)?\s+FEE\b|\bATM\s+FEE\b", "fees"),

    # ── Income ───────────────────────────────────────────────────────────────
    (r"\bPAYROLL\b|\bDIRECT\s+DEP(?:OSIT)?\b|\bPAYCHECK\b|\bWAGES\b", "income"),
    (r"\bNPS\.BD\.OF\s+ED\.\s+PAYROLL\b",                "income"),
    (r"\bTAX\s+REFUND\b|\bIRS\s+(REFUND|TREAS)\b",       "income"),
    (r"\bMonthly\s+Interest\s+Paid\b|\bINTEREST\s+EARNED\b", "income"),
    (r"\bCheck\s+Deposit\b",                             "income"),
    (r"\bFID\s+BKG\s+SVC\b|\bFIDELITY\b",                "internal_transfers"),

    # ── Healthcare ───────────────────────────────────────────────────────────
    (r"\bCVS\s+PHARMACY\b|\bWALGREENS\b|\bRITE\s+AID\b", "healthcare"),
    (r"\bDR\.?\s+\w+\b|\bMEDICAL\b|\bHOSPITAL\b|\bCLINIC\b|\bDENTAL\b", "healthcare"),
    (r"\bONE\s*MEDICAL\b|\bTELADOC\b|\bGOODRX\b",        "healthcare"),

    # ── Entertainment (events / venues / streaming-adjacent) ─────────────────
    (r"\bAMC\s+THEATRES?\b|\bREGAL\s+CINEMAS?\b|\bCINEMARK\b", "entertainment"),
    (r"\bTICKETMASTER\b|\bSTUBHUB\b|\bSEATGEEK\b|\bAXS\b|\bEVENTBRITE\b", "entertainment"),
    (r"\bSTEAM\b|\bPLAYSTATION\b|\bPSN\b|\bXBOX\b|\bNINTENDO\b", "entertainment"),

    # ── Shopping (last so subscriptions/groceries above get first crack) ─────
    (r"\bAMAZON\.COM\b|\bAMZN\b|\bAMZN\s*MKTP\b",        "shopping"),
    (r"\bTARGET\b",                                      "shopping"),
    (r"\bWALMART\b",                                     "shopping"),
    (r"\bHOME\s*DEPOT\b|\bLOWE'?S\b|\bACE\s+HARDWARE\b", "shopping"),
    (r"\bBEST\s*BUY\b",                                  "shopping"),
    (r"\bIKEA\b|\bWAYFAIR\b|\bRESTORATION\s+HARDWARE\b", "shopping"),
    (r"\bMACY'?S\b|\bNORDSTROM\b|\bKOHL'?S\b|\bSEPHORA\b|\bULTA\b", "shopping"),
    (r"\bTEMU\b|\bSHEIN\b|\bASOS\b|\bUNIQLO\b|\bH&M\b|\bZARA\b",    "shopping"),
    (r"\bTARGET\.COM\b|\bEBAY\b|\bETSY\b",               "shopping"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), c) for p, c in CATEGORY_RULES]


def classify(description: str) -> str:
    if not description:
        return "other"
    for pat, cat in _COMPILED:
        if pat.search(description):
            return cat
    return "other"


# ── Query expansion ─────────────────────────────────────────────────────────
# Map common natural-language terms in user questions to the set of categories
# that should be aggregated. Looked up case-insensitively as whole-word matches.
QUERY_EXPANSIONS: dict[str, set[str]] = {
    # food family
    "food":             {"groceries", "dining", "delivery"},
    "eating":           {"dining", "delivery"},
    "eat":              {"dining", "delivery"},
    "restaurants":      {"dining"},
    "dining":           {"dining"},
    "takeout":          {"delivery"},
    "take-out":         {"delivery"},
    "delivery":         {"delivery"},
    "groceries":        {"groceries"},
    "grocery":          {"groceries"},
    "supermarket":      {"groceries"},

    # subscriptions / streaming
    "subscriptions":    {"subscriptions"},
    "subscription":     {"subscriptions"},
    "streaming":        {"subscriptions"},
    "memberships":      {"subscriptions"},

    # bills / utilities
    "bills":            {"utilities", "loans", "credit_card_payments"},
    "utilities":        {"utilities"},
    "utility":          {"utilities"},
    "phone":            {"utilities"},
    "internet":         {"utilities"},
    "cable":            {"utilities"},
    "electric":         {"utilities"},
    "electricity":      {"utilities"},
    "gas bill":         {"utilities"},
    "water bill":       {"utilities"},

    # transport
    "gas":              {"gas"},          # standalone "gas" is fuel, not utility
    "fuel":             {"gas"},
    "uber":             {"transport", "delivery"},
    "lyft":             {"transport"},
    "rideshare":        {"transport"},
    "transportation":   {"transport", "gas"},
    "transit":          {"transport"},
    "commute":          {"transport"},
    "commuting":        {"transport"},

    # shopping
    "shopping":         {"shopping"},
    "amazon":           {"shopping", "subscriptions"},  # Prime fee + retail
    "online shopping":  {"shopping"},

    # money flow
    "income":           {"income"},
    "earnings":         {"income"},
    "paychecks":        {"income"},
    "salary":           {"income"},
    "transfers":        {"peer_transfers", "internal_transfers"},
    "zelle":            {"peer_transfers"},
    "venmo":            {"peer_transfers"},

    # debt
    "loans":            {"loans"},
    "loan":             {"loans"},
    "credit card":      {"credit_card_payments"},
    "credit cards":     {"credit_card_payments"},
    "card payment":     {"credit_card_payments"},
    "card payments":    {"credit_card_payments"},
    "bnpl":             {"bnpl"},
    "affirm":           {"bnpl"},
    "klarna":           {"bnpl"},
    "afterpay":         {"bnpl"},

    # cash & fees
    "atm":              {"atm_cash"},
    "cash":             {"atm_cash"},
    "fees":             {"fees"},
    "overdraft":        {"fees"},

    # entertainment / leisure
    "entertainment":    {"entertainment", "subscriptions"},
    "movies":           {"entertainment"},
    "concerts":         {"entertainment"},
    "tickets":          {"entertainment"},
    "games":            {"entertainment"},

    # healthcare
    "healthcare":       {"healthcare"},
    "medical":          {"healthcare"},
    "pharmacy":         {"healthcare"},
}

# Pre-build a map of regex → category-set so we match longer keys first
# ("credit card" before "card", "online shopping" before "shopping").
_EXPANSION_PATTERNS: list[tuple[re.Pattern, set[str]]] = sorted(
    [(re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v) for k, v in QUERY_EXPANSIONS.items()],
    key=lambda kv: -len(kv[0].pattern),
)


def expand_query(question: str) -> set[str]:
    """Return the set of categories implied by terms in the user's question.
    Empty set means "no category-specific intent — aggregate over the whole doc"."""
    found: set[str] = set()
    for pat, cats in _EXPANSION_PATTERNS:
        if pat.search(question):
            found.update(cats)
    return found
