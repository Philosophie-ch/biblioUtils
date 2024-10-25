from dataclasses import dataclass
import os


@dataclass
class EnvVars:
    ARCH: str
    DLTC_BIBLIO: str
    DOCKERHUB_TOKEN: str
    DOCKERHUB_USERNAME: str
    DLTC_WORKHOUSE_DIRECTORY: str
    REF_PIPE_DIRECTORY: str

    @classmethod
    def attribute_names(self) -> str:
        return ", ".join(self.__annotations__.keys())


@dataclass
class Profile:
    id: str
    lastname: str
    biblio_name: str
    biblio_keys: str
    biblio_dependencies_keys: str | None


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
    raw_html: File


@dataclass
class RefHTML:
    references: File
    dependencies: File | None = None


@dataclass
class ProfileWithHTML(ProfileWithRawHTML):
    html: RefHTML
