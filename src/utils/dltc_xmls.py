

import os
import xml.etree.ElementTree as ET
from aletk.ResultMonad import main_try_except_wrapper, Ok, Err, TResult
from aletk.utils import get_logger, remove_extra_whitespace

from typing import Any, Callable, Dict, Generator, List, TypedDict

basename = os.path.basename(__file__)

lgr = get_logger(basename)



class ArticleMetadata(TypedDict):
    journal_name: str
    journal_jstor_id: str
    journal_title: str
    publisher_name: str
    article_id: str
    doi: str
    article_title: str
    day: str
    month: str
    year: str
    volume: str
    issue: str
    issue_id: str
    stable_url: str
    language: str
    authors: str
    fpage: str
    lpage: str
    abstract: str
    has_references: bool
    is_review: bool
    reviewed_product_title: str


type ArticleMetadataGen = Generator[ArticleMetadata, None, None]

def get_xml_files(directory: str) -> List[str]:
    """Recursively get all XML files in the given directory."""

    xml_files: List[str] = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))

    return xml_files


def extract_text(elem: ET.Element, path: str) -> str:
    found = elem.find(path)
    extracted = found.text.strip() if found is not None and found.text else ""

    if extracted is None:
        lgr.warning(f"Element '{path}' not found in XML element '{elem.tag}'")

    return extracted

def full_name(raw_given: str, raw_surname: str) -> str:
    """Construct full name from given and surname."""
    given = remove_extra_whitespace(raw_given)
    surname = remove_extra_whitespace(raw_surname)

    match (given, surname):
        case ("", ""):
            return ""
        case ("", _):
            return surname
        case (_, ""):
            return given
        case _:
            return f"{surname}, {given}"

def extract_article_data(xml_path: str) -> ArticleMetadata:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    front = root.find('./front')
    if front is None:
        raise ValueError(f"XML file '{xml_path}' does not contain a valid <front> element")

    journal_meta = front.find('./journal-meta')
    article_meta = front.find('./article-meta')

    data: ArticleMetadata = {
        "journal_name": "",
        "journal_jstor_id": "",
        "journal_title": "",
        "publisher_name": "",
        "article_id": "",
        "doi": "",
        "article_title": "",
        "day": "",
        "month": "",
        "year": "",
        "volume": "",
        "issue": "",
        "issue_id": "",
        "stable_url": "",
        "language": "",
        "authors": "",
        "fpage": "",
        "lpage": "",
        "abstract": "",
        "has_references": False,
        "is_review": False,
        "reviewed_product_title": ""
    }

    ## Journal Meta
    if journal_meta is not None:
        data['journal_name'] = extract_text(journal_meta, 'journal-title-group/journal-title')
        data['journal_jstor_id'] = extract_text(journal_meta, 'journal-id[@journal-id-type="jstor"]')
        data['journal_title'] = extract_text(journal_meta, 'journal-title-group/journal-title')
        data['publisher_name'] = extract_text(journal_meta, 'publisher/publisher-name')
    
    ## Article Meta
    if article_meta is not None:
        data['doi'] = extract_text(article_meta, 'article-id[@pub-id-type="doi"]')
        data['article_id'] = extract_text(article_meta, 'article-id')
        data['article_title'] = extract_text(article_meta, 'title-group/article-title')

        pub_date = article_meta.find('pub-date')
        if pub_date is not None:
            data['day'] = extract_text(pub_date, 'day')
            data['month'] = extract_text(pub_date, 'month')
            data['year'] = extract_text(pub_date, 'year')

        data['volume'] = extract_text(article_meta, 'volume')
        data['issue'] = extract_text(article_meta, 'issue')
        data['issue_id'] = extract_text(article_meta, 'issue-id')

        self_uri = article_meta.find('self-uri')
        if self_uri is not None:
            data['stable_url'] = self_uri.attrib.get('{http://www.w3.org/1999/xlink}href', '')
    
        custom_meta_group = article_meta.find('custom-meta-group')
        if custom_meta_group is not None:
            lang = None
            for meta in custom_meta_group.findall('custom-meta'):
                name = extract_text(meta, 'meta-name')
                if name == 'lang':
                    lang = extract_text(meta, 'meta-value')
                    break
            data['language'] = lang if lang else ""

        ## Pages
        data['fpage'] = extract_text(article_meta, 'fpage')
        data['lpage'] = extract_text(article_meta, 'lpage')
    

    ## Authors
    authors = []
    contribs = article_meta.findall('contrib-group/contrib') if article_meta is not None else []
    for contrib in contribs:
        given = extract_text(contrib, 'string-name/given-names')
        surname = extract_text(contrib, 'string-name/surname')
        if given or surname:
            authors.append(f"{given or ''} {surname or ''}".strip())

    data['authors'] = " and ".join(authors)

    ## Abstract
    abstract = article_meta.find('abstract') if article_meta is not None else None
    if isinstance(abstract, ET.Element):
        data['abstract'] = remove_extra_whitespace(ET.tostring(abstract, encoding='unicode', method='html'))
    else:
        data['abstract'] = ""

    ## Reviews
    article_type = root.attrib.get('article-type', '').lower()
    data['is_review'] = article_type in {'book-review', 'review-article', 'review'}

    product = article_meta.find('product') if article_meta is not None else None
    data['reviewed_product_title'] = extract_text(product, 'source') if product is not None else ""

    ## References
    back = root.find('back')
    ref_list = back.find('ref-list') if back is not None else None
    data['has_references'] = ref_list is not None and len(ref_list.findall('ref')) > 0

    return data


process: Callable[[str], ArticleMetadataGen] = lambda directory: (
    extract_article_data(xml_file) for xml_file in get_xml_files(directory)
) 


def write_article_metadata_to_csv(
    metadata: ArticleMetadataGen,
    output_file: str
) -> None:
    """Write the extracted article metadata to a CSV file."""
    import csv

    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ArticleMetadata.__required_keys__
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for i, data in enumerate(metadata):
            if i % 49 == 0:
                lgr.info(f"Writing record {i+1}...")
            writer.writerow(data)


@main_try_except_wrapper(lgr)
def main(directory: str, output_file: str) -> None:
    """Main function to extract article metadata from XML files in the given directory."""
    
    if not os.path.isdir(directory):
        raise ValueError(f"Provided path is not a directory: '{directory}'")

    lgr.info(f"Getting XML files from directory '{directory}'...")

    xml_files = get_xml_files(directory)
    
    if not xml_files:
        lgr.warning(f"No XML files found in directory '{directory}'")
        return

    lgr.info(f"Found '{len(xml_files)}' XML files to process...")

    metadata = process(directory)

    lgr.info("Writing article metadata to CSV file...")
    write_article_metadata_to_csv(metadata, output_file)

    lgr.info("Metadata extraction complete.")

    return None


def cli(result: TResult[None]) -> None:
    """Command-line interface for the script."""

    match result:

        case Ok(_):
            print("Metadata extraction completed successfully.")

        case Err(e):
            print(f"An error occurred: {e}. Context: {result}")

        case _:
            raise ValueError(f"Unexpected result type: {type(result)}")



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract article metadata from XML files.")
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        required=True,
        help="Directory containing XML files to process."
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        required=True,
        help="Output CSV file to write the article metadata."
    )

    args = parser.parse_args()

    result = main(args.directory, args.output_file)

    cli(result)
