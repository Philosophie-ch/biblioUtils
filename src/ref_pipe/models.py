from dataclasses import dataclass
import os
from typing import Dict, FrozenSet, Iterator, Literal, NamedTuple, Tuple

from src.sdk.utils import dump_frozenset
from src.sdk.ResultMonad import Err, Ok


class EnvVars(NamedTuple):
    """
    Environment variables required for the ref_pipe project.

    Attributes:
    ----------
    `ARCH`: str
        Architecture of the system. Must be either 'amd64' or 'arm64'.
    `BIBLIOGRAPHY_BASE_FILENAME`: str
        Basename of the bibliography file, directly inside the DLTC_WORKHOUSE_DIRECTORY.
    `DOCKERHUB_TOKEN`: str
        Token for DockerHub.
    `DOCKERHUB_USERNAME`: str
        Username for DockerHub.
    `DLTC_WORKHOUSE_DIRECTORY`: str
        Path to the DLTC_WORKHOUSE_DIRECTORY.
    `REF_PIPE_DIR_RELATIVE_PATH`: str
        Relative path to the ref_pipe directory. This is used to locate the ref_pipe directory inside the DLTC_WORKHOUSE_DIRECTORY, both in the local system and in the container.
    `DOCKER_IMAGE_NAME`: str
        Name of the Docker image to use.
    `DOCKER_CONTAINER_NAME`: str
        Name of the container to run the commands in.
    `DOCKER_COMPOSE_FILE`: str
        Path to the Docker Compose file.
    `CSL_FILE`: str
        Path to the CSL file used to compile the HTML files.
    """

    ARCH: str
    BIBLIOGRAPHY_BASE_FILENAME: str
    DOCKERHUB_TOKEN: str
    DOCKERHUB_USERNAME: str
    DLTC_WORKHOUSE_DIRECTORY: str
    CONTAINER_DLTC_WORKHOUSE_DIRECTORY: str
    REF_PIPE_DIR_RELATIVE_PATH: str
    DOCKER_IMAGE_NAME: str
    DOCKER_CONTAINER_NAME: str
    DOCKER_COMPOSE_FILE: str
    CSL_FILE: str

    @classmethod
    def attribute_names(self) -> str:
        return ", ".join(self.__annotations__.keys())


SUPPORTED_ENTITY_TYPES = ("profile", "article")
type TSupportedEntity = Literal["profile", "article"]

type TBibEntityAttribute = Literal[
    "id",
    "entity_key",
    "url_endpoint",
    "main_bibkeys",
    "further_references",
    "depends_on",
]


@dataclass(frozen=True, slots=True)
class BibEntity:
    """
    Bibliographic entity. Can be a profile, or an article.

    Attributes:
    ----------
    `id`: str
        ID in the database.
    `entity_key`: str
        biblio_name for profiles, bibkey for articles.
    `url_endpoint`: str
        URL endpoint that refers to the bibliographic entity. For example, 'urlname' for pages, 'login' for profiles.
    `main_bibkeys`: set[str]
        Entries directly written by the author, or direct references made by an article.
    `biblio_keys_further_references`: set[str]
        Entries referred to by the main_bibkeys.
    `biblio_dependencies_keys`: set[str]
        Entries that are dependencies of the main_bibkeys.
    """

    id: str
    entity_key: str
    url_endpoint: str
    main_bibkeys: FrozenSet[str]
    further_references: FrozenSet[str]
    depends_on: FrozenSet[str]

    def dump(self) -> dict[str, str | list[str]]:
        return {
            "id": f"{self.id}",
            "entity_key": f"{self.entity_key}",
            "url_endpoint": f"{self.url_endpoint}",
            "main_bibkeys": dump_frozenset(self.main_bibkeys),
            "further_references": dump_frozenset(self.further_references),
            "depends_on": dump_frozenset(self.depends_on),
        }


@dataclass(frozen=False, slots=True)
class File:
    content: str
    basename: str

    def full_file_path(self, base_dir: str) -> str:
        return os.path.join(base_dir, self.basename)

    def relative_file_path(self, relative_dir: str) -> str:
        return os.path.join(relative_dir, self.basename)


class BibentityHTMLRawFile(NamedTuple):
    local_path: str


class Markdown(NamedTuple):
    """
    Markdown files for a bibliographic entity.

    Attributes:
    ----------
    `local_base_dir`: str
        Base directory for the markdown files in the host system.
    `container_base_dir`: str
        Base directory for the markdown files in the container.
    `relative_output_dir`: str
        Relative directory for the markdown files, inside the base directory (both in the host system and in the container).
    `main_file`: File
        Main markdown file with the content to convert to HTML.
    `master_file`: File
        'master.md' file needed to compile the main markdown file to HTML.
    """

    local_base_dir: str
    container_base_dir: str
    relative_output_dir: str
    main_file: File
    master_file: File


class RefHTML(NamedTuple):
    references_filename: str
    further_references_filename: str


@dataclass(frozen=True, slots=True)
class BibEntityWithHTML(BibEntity):
    html: RefHTML


class BibDiv(NamedTuple):
    div_id: str
    content: str


type THTMLReport = Iterator[tuple[BibEntity, Ok[BibEntityWithHTML] | Err]]


class Bibliography(NamedTuple):
    """
    Model representing the part of the bibliography we need for this project.

    Attributes:
    ----------
    `bibkeys`: FrozenSet[str]
        Set of bibliographic keys. Must be one per line of the bibliography bib file.
    `bibkey_index_dict`: Dict[str, int]
        Dictionary with the index of each bibkey in the content tuple.
    `content`: Tuple[str, ...]
        Tuple in which each element is a line of the bibliography bib file.
    """

    bibkeys: FrozenSet[str]
    bibkey_index_dict: Dict[str, int]
    content: Tuple[str, ...]
