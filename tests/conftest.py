import uuid
from pathlib import Path

import pytest


FILES_FOLDER = Path(__file__).parent / "files"


@pytest.fixture
def files_folder():
    yield FILES_FOLDER


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch, tmp_path):
    github_output_path = tmp_path / uuid.uuid4().hex
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_path))
