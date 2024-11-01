from dataclasses import dataclass
import os
from typing import Iterator, List, Tuple, TypeAlias, TypeVar

from src.sdk.ResultMonad import Err, Ok


@dataclass
class EnvVars:
    ARCH: str
    DLTC_BIBLIO: str
    DOCKERHUB_TOKEN: str
    DOCKERHUB_USERNAME: str
    DLTC_WORKHOUSE_DIRECTORY: str
    REF_PIPE_DIRECTORY: str
    CONTAINER_NAME: str

    @classmethod
    def attribute_names(self) -> str:
        return ", ".join(self.__annotations__.keys())


@dataclass
class Profile:
    id: str
    lastname: str
    biblio_name: str
    biblio_keys: List[str]
    biblio_keys_further_references: List[str]
    biblio_dependencies_keys: List[str]

    def dump(self) -> str:
        return f"{self.__dict__}"


@dataclass
class File:
    content: str
    name: str

    def file_path(self, base_dir: str) -> str:
        return os.path.join(base_dir, self.name)


@dataclass
class Markdown:
    base_dir: str
    main_file: File
    master_file: File


@dataclass
class ProfileWithMD(Profile):
    markdown: Markdown


@dataclass
class ProfileWithRawHTML(ProfileWithMD):
    raw_html_filename: str


@dataclass
class RefHTML:
    references_filename: str
    further_references_filename: str | None = None
    dependencies_filename: str | None = None


@dataclass
class ProfileWithHTML(ProfileWithRawHTML):
    html: RefHTML


TMDReport: TypeAlias = Iterator[tuple[Profile, Ok[ProfileWithMD] | Err]]

THTMLReport: TypeAlias = Iterator[tuple[Profile, Ok[ProfileWithHTML] | Err]]
