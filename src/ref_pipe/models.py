from dataclasses import dataclass
import os
from typing import Iterator, List, TypeAlias

from src.sdk.ResultMonad import Err, Ok


@dataclass(frozen=True, slots=True)
class EnvVars:
    """
    Environment variables required for the ref_pipe project.

    Attributes:
    ----------
    `ARCH`: str
        Architecture of the system. Must be either 'amd64' or 'arm64'.
    `DLTC_BIBLIO`: str
        Basename of the bibliography file, directly inside the DLTC_WORKHOUSE_DIRECTORY.
    `DOCKERHUB_TOKEN`: str
        Token for DockerHub.
    `DOCKERHUB_USERNAME`: str
        Username for DockerHub.
    `DLTC_WORKHOUSE_DIRECTORY`: str
        Path to the DLTC_WORKHOUSE_DIRECTORY.
    `REF_PIPE_DIR_RELATIVE_PATH`: str
        Relative path to the ref_pipe directory. This is used to locate the ref_pipe directory inside the DLTC_WORKHOUSE_DIRECTORY, both in the local system and in the container.
    `CONTAINER_NAME`: str
        Name of the container to run the commands in.
    `DOCKER_COMPOSE_FILE`: str
        Path to the Docker Compose file.
    """

    ARCH: str
    DLTC_BIBLIO: str
    DOCKERHUB_TOKEN: str
    DOCKERHUB_USERNAME: str
    DLTC_WORKHOUSE_DIRECTORY: str
    CONTAINER_DLTC_WORKHOUSE_DIRECTORY: str
    REF_PIPE_DIR_RELATIVE_PATH: str
    CONTAINER_NAME: str
    DOCKER_COMPOSE_FILE: str

    @classmethod
    def attribute_names(self) -> str:
        return ", ".join(self.__annotations__.keys())


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    lastname: str
    biblio_name: str
    biblio_keys: List[str]
    biblio_keys_further_references: List[str]
    biblio_dependencies_keys: List[str]

    def dump(self) -> str:
        return f"{self.__dict__}"


@dataclass(frozen=False, slots=True)
class File:
    content: str
    basename: str

    def full_file_path(self, base_dir: str) -> str:
        return os.path.join(base_dir, self.basename)

    def relative_file_path(self, relative_dir: str) -> str:
        return os.path.join(relative_dir, self.basename)


@dataclass(frozen=True, slots=True)
class Markdown:
    """
    Markdown files for a profile.

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


@dataclass(frozen=True, slots=True)
class ProfileWithMD(Profile):
    markdown: Markdown


@dataclass(frozen=True, slots=True)
class ProfileWithRawHTML(ProfileWithMD):
    raw_html_filename: str


@dataclass(frozen=True, slots=True)
class RefHTML:
    references_filename: str
    further_references_filename: str | None = None
    dependencies_filename: str | None = None


@dataclass(frozen=True, slots=True)
class ProfileWithHTML(ProfileWithRawHTML):
    html: RefHTML


type TMDReport = Iterator[tuple[Profile, Ok[ProfileWithMD] | Err]]

type THTMLReport = Iterator[tuple[Profile, Ok[ProfileWithHTML] | Err]]
