
"""
# ENGLISH
"""

ENGLISH_ARTICLES = [
    "the",
    "a",
    "an"
]

ENGLISH_PREPOSITIONS = [
    "aboard", "about", "above", "across", "after", "against", "along", "amid",
    "among", "anti", "around", "as", "at", "before", "behind", "below", "beneath",
    "beside", "besides", "between", "beyond", "but", "by", "concerning", "considering",
    "despite", "down", "during", "except", "excepting", "excluding", "following", 
    "for", "from", "in", "inside", "into", "like", "minus", "near", "of", "off",
    "on", "onto", "opposite", "outside", "over", "past", "per", "plus", "regarding",
    "round", "save", "since", "than", "through", "to", "toward", "towards", "under",
    "underneath", "unlike", "until", "up", "upon", "versus", "via", "with", "within",
    "without"
]

ENGLISH_COORDINATING_CONJUNCTIONS = [
    "for", "and", "nor", "but", "or", "yet", "so"
]


"""
# FRENCH
"""

FRENCH_ARTICLES = [
    "le", "la", "les",
    "un", "une",
]

FRENCH_PREPOSITIONS = [
    "à", "au", "aux",
    "de", "du", "des",
    #"en", "dans",
    #"sur", "sous",
    #"avec",
    #"sans",
    #"pour",
    #"par",
    #"chez",
    #"vers",
    #"pendant",
    #"contre",
    #"depuis",
    #"jusqu'à",
    #"entre",
    #"après",
    #"avant",
]

FRENCH_COORDINATING_CONJUNCTIONS = [
    "et", "ou", "mais", "donc", "or", "ni", "car"
]

"""
# GERMAN
"""

GERMAN_ARTICLES = [
    "der", "die", "das",
    "ein", "eine", "eines", "einem", "einen",
]

"""
# CONSTANTS
"""

FIXED_SMALL = [
# Fixed
    "was", "is", "are", "am", "were", "been", "our", 
    "vs.", "on", "in", "c.",
]

ALWAYS_SMALL = FIXED_SMALL + ENGLISH_ARTICLES + ENGLISH_PREPOSITIONS + ENGLISH_COORDINATING_CONJUNCTIONS + FRENCH_ARTICLES + FRENCH_PREPOSITIONS + FRENCH_COORDINATING_CONJUNCTIONS + GERMAN_ARTICLES