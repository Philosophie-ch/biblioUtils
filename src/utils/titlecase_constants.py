from typing import List

"""
# ENGLISH
"""

ENGLISH_ARTICLES: List[str] = ["the", "a", "an"]

ENGLISH_PREPOSITIONS: List[str] = [
    "aboard",
    "about",
    "above",
    "across",
    "after",
    "against",
    "along",
    "amid",
    "among",
    "anti",
    "around",
    "as",
    "at",
    "before",
    "behind",
    "below",
    "beneath",
    "beside",
    "besides",
    "between",
    "beyond",
    "but",
    "by",
    "concerning",
    "considering",
    "despite",
    "down",
    "during",
    "except",
    "excepting",
    "excluding",
    "following",
    "for",
    "from",
    "in",
    "inside",
    "into",
    "like",
    "minus",
    "near",
    "of",
    "off",
    "on",
    "onto",
    "opposite",
    "outside",
    "over",
    "past",
    "per",
    "plus",
    "regarding",
    "round",
    "save",
    "since",
    "than",
    "through",
    "to",
    "toward",
    "towards",
    "under",
    "underneath",
    "unlike",
    "until",
    "up",
    "upon",
    "versus",
    "via",
    "with",
    "within",
    "without",
]

ENGLISH_COORDINATING_CONJUNCTIONS: List[str] = ["for", "and", "nor", "but", "or", "yet", "so"]


"""
# FRENCH
"""

FRENCH_ARTICLES: List[str] = [
    "le",
    "la",
    "les",
    "un",
    "une",
]

FRENCH_PREPOSITIONS: List[str] = [
    "à",
    "au",
    "aux",
    "de",
    "du",
    "des",
    # "en", "dans",
    # "sur", "sous",
    # "avec",
    # "sans",
    # "pour",
    # "par",
    # "chez",
    # "vers",
    # "pendant",
    # "contre",
    # "depuis",
    # "jusqu'à",
    # "entre",
    # "après",
    # "avant",
]

FRENCH_COORDINATING_CONJUNCTIONS: List[str] = ["et", "ou", "mais", "donc", "or", "ni", "car"]

"""
# GERMAN
"""

GERMAN_ARTICLES: List[str] = [
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "eines",
    "einem",
    "einen",
]

"""
# CONSTANTS
"""

FIXED_SMALL: List[str] = [
    # Fixed
    "was",
    "is",
    "are",
    "am",
    "were",
    "been",
    "our",
    "vs.",
    "on",
    "in",
    "c.",
]

ALWAYS_SMALL: List[str] = (
    FIXED_SMALL
    + ENGLISH_ARTICLES
    + ENGLISH_PREPOSITIONS
    + ENGLISH_COORDINATING_CONJUNCTIONS
    + FRENCH_ARTICLES
    + FRENCH_PREPOSITIONS
    + FRENCH_COORDINATING_CONJUNCTIONS
    + GERMAN_ARTICLES
)
