import os
from typing import Dict, Tuple
from yaml import load, Loader
from .logic_types import Author, Article, JournalIssue, author_full_name, journal_date, TMonth, TYear, MONTH_STR_INT, TGivenName, TFamilyName
from aletk.ResultMonad import try_except_wrapper
from aletk.utils import get_logger, remove_extra_whitespace


logger = get_logger(__name__)


# TODO: italics or math on titles should be converted to markdown, maybe it's better is the data arriving here is already markdown

def article_author_to_yaml_str(author: Author) -> str:
    name_s = f"  - name: {author_full_name(author)}"
    email_s = f"    email: {author.email}" if author.email else ""
    institute_s = f"    institute:\n    - {author.institute}" if author.institute else ""
    orcid_s = f"    ORCID: {author.orcid}" if author.orcid else ""
    correspondence_s = f"    correspondence: {author.correspondence}"

    l = (name_s, email_s, institute_s, orcid_s, correspondence_s)
    l_filtered = (x for x in l if x != "")
    s = "\n".join(l_filtered)

    return s

def keyword_to_yaml_str(keyword: str) -> str:
    s = f"- {keyword}"

    return s

def article_to_yaml_str(article: Article) -> str:
    title_s = f"- title: {article.title}"
    subtitle_s = f"  subtitle: {article.subtitle}" if article.subtitle else ""
    first_page_s = f"  first-page: {article.first_page}"
    last_page_s = f"  last-page: {article.last_page}"
    doi_s = f"  doi: {article.doi}"
    abstract_s = f"  abstract: |\n    {article.abstract}" if article.abstract else ""
    author_s = f"  author:\n{"\n".join((article_author_to_yaml_str(author)) for author in article.authors)}"
    galleys_s = f"  galleys:\n  - {article.galleys}"
    keywords_s = f"  keywords:\n  {"\n  ".join((keyword_to_yaml_str(keyword)) for keyword in article.keywords)}" if article.keywords else ""

    l = (title_s, subtitle_s, first_page_s, last_page_s, doi_s, abstract_s, author_s, galleys_s, keywords_s)
    l_filtered = (x for x in l if x != "")
    s = "\n".join(l_filtered)

    return s


def journal_issue_editor_to_yaml_str(editor: Author) -> str:
    s = f"- {author_full_name(editor)}"

    return s

def journal_issue_to_yaml_str(journal_issue: JournalIssue) -> str:

    volume_s = f"volume: {journal_issue.volume}"
    issue_s = f"issue: {journal_issue.issue}"
    date_s = f"date: {journal_date(journal_issue)}"
    first_page_s = f"first-page: {journal_issue.first_page}"
    doi_s = f"doi: {journal_issue.doi}"
    issnprint_s = f"issnprint: {journal_issue.issnprint}"
    issuetitle_s = f"issuetitle: {journal_issue.title}"
    issueeditor_s = f"issueeditor:\n{"\n".join((journal_issue_editor_to_yaml_str(editor)) for editor in journal_issue.editors)}"
    articles_s = f"articles:\n{"\n".join((article_to_yaml_str(article)) for article in journal_issue.articles)}"

    l = (volume_s, issue_s, date_s, first_page_s, doi_s, issnprint_s, issuetitle_s, issueeditor_s, articles_s)
    l_filtered = (x for x in l if x != "")
    s = "\n".join(l_filtered)

    return s


    
@try_except_wrapper(logger)
def write_journal_issue_to_yaml(journal_issue: JournalIssue, filename: str) -> None:

    os.makedirs(filename, exist_ok=True)

    with open(filename, 'w') as file:
        file.write(journal_issue_to_yaml_str(journal_issue))


def parse_month_year(month_year_raw: str) -> Tuple[TMonth, TYear]:
    if month_year_raw == "":
        raise ValueError(f"Could not parse '{month_year_raw}'. Please input a month-year date of the form 'January 2025'.")
    stripped = remove_extra_whitespace(month_year_raw)
    month_s, year_s = tuple(stripped.split(" "))
    month = MONTH_STR_INT[month_s]
    year = int(year_s)
    return month, year

def parse_editor_name(author_name_raw: str) -> Tuple[TGivenName, TFamilyName]:

    if author_name_raw == "":
        return "", ""

    split = author_name_raw.split(",")
    stripped = [remove_extra_whitespace(x) for x in split]

    if len(stripped) == 2:
        return stripped[1], stripped[0]
    if len(stripped) == 1:
        print(f"Warning: author name in YAML '{author_name_raw}' contains only one part")
        return stripped[0], ""
    else:
        print(f"Warning: could not parse author name '{author_name_raw}'. Skipping.")
        return "", ""

def read_journal_issue_from_yaml(filename: str, journal: str) -> JournalIssue:

    yaml: Dict[str, str | Dict[str, str | Dict[str, str]]] = load(open(filename, 'r'), Loader=Loader)

    month, year = parse_month_year(yaml.get('date', ""))

    journal_issue = JournalIssue(
        journal=journal,
        volume=yaml.get('volume', ""),
        issue=yaml.get('issue', ""),
        month=month,
        year=year,
        first_page=int(yaml.get('first-page', "")),
        doi=yaml.get('doi', ""),
        issn=yaml.get('issn', ""),
        issnprint=yaml.get('issnprint', ""),
        title=yaml.get('issuetitle', ""),

        editors=[Author(
            given_name=parse_editor_name(editor)[0],
            family_name=parse_editor_name(editor)[1],
            correspondence=False,
            email='',
            institute='',
            orcid=''
        ) for editor in yaml.get('issueeditor', "")],

        articles=[Article(
            title=article.get('title', ""),
            subtitle=article.get('subtitle', ""),
            abstract=remove_extra_whitespace(article.get('abstract', "")),
            authors=[Author(
                given_name=(author.get('name', "")),
                family_name="",
                correspondence=author.get('correspondence', ""),
                email=author.get('email', ""),
                institute=author.get('institute', [""])[0],
                orcid=author.get('ORCID', "")
            ) for author in article['author']],

            first_page=article.get('first-page', ""),
            last_page=article.get('last-page', ""),
            doi=article.get('doi', ""),
            galleys=article.get('galleys', [""])[0],
            keywords=[keyword for keyword in article.get('keywords', [])]

        ) for article in yaml['articles']]
    )

    return journal_issue
