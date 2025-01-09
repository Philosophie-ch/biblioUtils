from dataclasses import dataclass
from typing import List


type TGivenName = str
type TFamilyName = str

@dataclass(frozen=True, slots=True)
class Author:
    given_name: TGivenName
    family_name: TFamilyName
    correspondence: bool
    email: str
    institute: str
    orcid: str

def author_full_name(author: Author) -> str:
    return f"{author.family_name}, {author.given_name}"


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    subtitle: str
    abstract: str
    authors: List[Author]
    first_page: int
    last_page: int
    doi: str
    galleys: str
    keywords: List[str]



type TMonth = int
type TYear = int

@dataclass(frozen=True, slots=True)
class JournalIssue:
    journal: str
    volume: int
    issue: int
    month: TMonth
    year: TYear
    first_page: int
    doi: str
    issn: str
    issnprint: str
    title: str
    editors: List[Author]
    articles: List[Article]

MONTH_STR_INT = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

MONTH_INT_STR = {v: k for k, v in MONTH_STR_INT.items()}

def journal_date(journal_issue: JournalIssue) -> str:
    month = MONTH_INT_STR[journal_issue.month]
    return f"{month} {journal_issue.year}"

