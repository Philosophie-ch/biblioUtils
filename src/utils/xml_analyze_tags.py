"""
Goes through all XML files in the given directory and its subdirectories and analyzes the tags.
It counts the occurrences of each tag and prints a summary.
"""

import os
import xml.etree.ElementTree as ET
from aletk.ResultMonad import main_try_except_wrapper, Ok, Err
from aletk.utils import get_logger

from typing import Dict, List

lgr = get_logger(__file__)


type TagCount = Dict[str, int]


def get_xml_files(directory: str) -> List[str]:
    """Recursively get all XML files in the given directory."""

    xml_files: List[str] = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))

    return xml_files


def analyze_tags(xml_files: List[str]) -> TagCount:
    """Analyze the tags in the given XML files and return a summary of tag counts."""
    tag_counts: TagCount = {}

    for xml_file in xml_files:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        for elem in root.iter():
            tag = elem.tag
            if tag in tag_counts:
                tag_counts[tag] += 1
            else:
                tag_counts[tag] = 1

    return tag_counts


@main_try_except_wrapper(lgr)
def main(directory: str) -> TagCount | None:
    """Main function to analyze XML files in the given directory."""

    if not os.path.isdir(directory):
        raise ValueError(f"Provided path is not a directory: '{directory}'")

    lgr.info(f"Getting XML files from directory '{directory}'...")

    xml_files = get_xml_files(directory)

    if not xml_files:
        lgr.warning(f"No XML files found in directory '{directory}'")
        return None

    lgr.info(f"Found '{len(xml_files)}' XML files to analyze...")

    tag_counts = analyze_tags(xml_files)

    lgr.info(f"Tag analysis complete. Found {len(tag_counts)} unique tags.")

    return tag_counts


def cli(result: TagCount | None) -> None:
    """Command line interface to print the tag counts."""
    if result is None:
        print("No tags found.")
        return

    for tag, count in result.items():
        print(f"{tag}: {count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze XML files in a directory and count tag occurrences.")

    parser.add_argument("-d", "--directory", type=str, required=True, help="Directory to search for XML files.")

    args = parser.parse_args()

    result = main(args.directory)

    if isinstance(result, Ok):
        cli(result.out)

    elif isinstance(result, Err):
        lgr.error(f"Error occurred: {result.message}. Context: {result.__str__}")
