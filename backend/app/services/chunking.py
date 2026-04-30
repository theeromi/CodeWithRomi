import re
import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")

_SPLIT_PATTERNS = [
    re.compile(r"\n\n+"),   # paragraph breaks
    re.compile(r"(?<=[.!?])\s+"),  # sentence boundary
    re.compile(r"\s+"),     # whitespace fallback
]


def count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


def chunk_text(text: str, target_tokens: int = 800, overlap_tokens: int = 100) -> list[tuple[str, int]]:
    """Recursive splitter. Returns list of (chunk_text, token_count).
    Splits on paragraphs, then sentences, then whitespace, packing pieces up to target_tokens.
    Adds overlap of approx `overlap_tokens` between adjacent chunks.
    """
    text = text.strip()
    if not text:
        return []

    pieces = _split_recursive(text, target_tokens)

    chunks: list[tuple[str, int]] = []
    buf: list[str] = []
    buf_tokens = 0
    for piece in pieces:
        ptok = count_tokens(piece)
        if buf and buf_tokens + ptok > target_tokens:
            joined = " ".join(buf).strip()
            chunks.append((joined, count_tokens(joined)))
            buf = _tail_overlap(buf, overlap_tokens)
            buf_tokens = sum(count_tokens(b) for b in buf)
        buf.append(piece)
        buf_tokens += ptok
    if buf:
        joined = " ".join(buf).strip()
        if joined:
            chunks.append((joined, count_tokens(joined)))
    return chunks


def _split_recursive(text: str, target: int, depth: int = 0) -> list[str]:
    if count_tokens(text) <= target or depth >= len(_SPLIT_PATTERNS):
        return [text]
    parts = _SPLIT_PATTERNS[depth].split(text)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if count_tokens(p) <= target:
            out.append(p)
        else:
            out.extend(_split_recursive(p, target, depth + 1))
    return out


def _tail_overlap(buf: list[str], overlap_tokens: int) -> list[str]:
    out: list[str] = []
    total = 0
    for piece in reversed(buf):
        out.insert(0, piece)
        total += count_tokens(piece)
        if total >= overlap_tokens:
            break
    return out
