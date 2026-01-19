from collections import Counter
from math import log, sqrt
import re

from app.domain.intelligence.taxonomy import normalize

LEXICAL_VERSION = "pair-tfidf-1"
_STOP_WORDS = frozenset("""
a an and are as at be been by for from has have in is it of on or our that the their this to was we were will with you your
""".split())
_TOKEN = re.compile(r"\.?[\w]+(?:[./-][\w]+)*(?:\+\+|#)?", re.UNICODE)


def tokens(value: str) -> list[str]:
    return [token for token in _TOKEN.findall(normalize(value).casefold()) if token not in _STOP_WORDS]


def terms(value: str, maximum: int = 20) -> list[str]:
    words = tokens(value)
    if not words:
        return []
    phrases = Counter(words)
    phrases.update(" ".join(pair) for pair in zip(words, words[1:]) if pair[0] != pair[1])
    return sorted(phrases, key=lambda term: (-min(phrases[term], 3), " " in term, term))[:maximum]


def lexical_similarity(left: str, right: str) -> float:
    first, second = Counter(tokens(left)), Counter(tokens(right))
    if not first or not second:
        return 0.0
    # The corpus is this exact pair. Sublinear counts are capped to resist repetition.
    idf = {term: log(3 / (1 + int(term in first) + int(term in second))) + 1 for term in first.keys() | second.keys()}
    def weights(counts):
        return {term: (1 + log(min(count, 3))) * idf[term] for term, count in counts.items()}
    a, b = weights(first), weights(second)
    dot = sum(a[term] * b[term] for term in sorted(a.keys() & b.keys()))
    return min(1.0, dot / (sqrt(sum(weight ** 2 for weight in a.values())) * sqrt(sum(weight ** 2 for weight in b.values()))))
