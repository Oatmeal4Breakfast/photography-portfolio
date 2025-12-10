from dataclasses import dataclass
from dotenv import load_dotenv
import os


load_dotenv()


@dataclass
class DBConfig:
    file_name: str

    @classmethod
    def from_env(cls) -> DBConfig:
        file_name = os.getenv("DB_FILE_NAME")
        if not file_name:
            raise EnvironmentError("Unable to read 'DB_FILE_NAME' from .env")

        assert file_name is not None

        return DBConfig(file_name=file_name)
