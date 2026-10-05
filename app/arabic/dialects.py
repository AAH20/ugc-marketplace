"""Arabic dialect detection and definitions."""

from enum import Enum


class ArabicDialect(str, Enum):
    """Supported Arabic dialects for MENA market."""

    EGYPTIAN = "egyptian"
    GULF = "gulf"
    LEVANTINE = "levantine"
    MAGHREBI = "maghrebi"


# Dialect-specific keywords for detection (distinctive markers)
DIALECT_KEYWORDS: dict[ArabicDialect, list[str]] = {
    ArabicDialect.EGYPTIAN: [
        "أهلا بيك",
        "إزيك",
        "إزيكي",
        "عامل إيه",
        "عاملة إيه",
        "برضه",
        "كده",
        "دلوقتي",
        "عشان",
        "أوي",
    ],
    ArabicDialect.GULF: [
        "هلا فيك",
        "شلونك",
        "شلونج",
        "حبيبي",
        "حبيبتي",
        "يالله",
        "هلا والله",
        "الله يعطيك",
        "الله يحفظك",
        "ديرة",
        "هالشيء",
        "شنو",
        "وش",
        "ليش",
    ],
    ArabicDialect.LEVANTINE: [
        "أهلا وسهلا",
        "أهلا وسهلا فيك",
        "كيفك",
        "كتير",
        "كتيرة",
        "كتير منيح",
        "كتير حلو",
        "يلا",
        "هلأ",
        "عم",
        "بدي",
        "شو",
    ],
    ArabicDialect.MAGHREBI: [
        "مرحبا بيك",
        "بزاف",
        "بزافة",
        "واخا",
        "واخة",
        "كيفاش",
        "واش",
        "علاش",
        "دابا",
        "هادا",
        "هادي",
        "هادو",
    ],
}

# Dialect to region mapping
DIALECT_REGIONS: dict[ArabicDialect, str] = {
    ArabicDialect.EGYPTIAN: "Egypt",
    ArabicDialect.GULF: "Gulf",
    ArabicDialect.LEVANTINE: "Levant",
    ArabicDialect.MAGHREBI: "Maghreb",
}

# Dialect-specific greetings
DIALECT_GREETINGS: dict[ArabicDialect, str] = {
    ArabicDialect.EGYPTIAN: "أهلا بيك",
    ArabicDialect.GULF: "هلا فيك",
    ArabicDialect.LEVANTINE: "أهلا وسهلا",
    ArabicDialect.MAGHREBI: "مرحبا بيك",
}


class DialectDetector:
    """Detects Arabic dialect from text using keyword matching."""

    def detect(self, text: str) -> ArabicDialect:
        """Detect the most likely Arabic dialect from text.

        Returns the dialect with the most keyword matches.
        Defaults to Egyptian (most widely understood) if no match.
        """
        if not text or not text.strip():
            return ArabicDialect.EGYPTIAN

        text_lower = text.lower()
        scores: dict[ArabicDialect, int] = {d: 0 for d in ArabicDialect}

        for dialect, keywords in DIALECT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[dialect] += 1

        best_dialect = max(scores, key=lambda d: scores[d])
        if scores[best_dialect] == 0:
            return ArabicDialect.EGYPTIAN  # Default fallback
        return best_dialect


def get_dialect(text: str) -> ArabicDialect:
    """Convenience function to detect dialect from text."""
    return DialectDetector().detect(text)


def get_dialect_region(dialect: ArabicDialect) -> str:
    """Get the region name for a dialect."""
    return DIALECT_REGIONS.get(dialect, "Unknown")


def get_dialect_greeting(dialect: ArabicDialect) -> str:
    """Get the greeting for a dialect."""
    return DIALECT_GREETINGS.get(dialect, "مرحبا")


def is_valid_dialect(dialect_str: str) -> bool:
    """Check if a string is a valid dialect identifier."""
    return dialect_str.lower() in [d.value for d in ArabicDialect]
