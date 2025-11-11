import json
import re
import subprocess
from collections.abc import Iterator
from itertools import batched
from textwrap import dedent
from typing import NamedTuple

from pathlib import Path

from github_custom_actions import ActionBase, ActionInputs, ActionOutputs


match_error_message = re.compile(
    r"(?P<file>.+):(?P<position>\d+): "
    r"(?P<category>parser|validity) error : "
    r"(?P<message>.+)"
).fullmatch


class Error(NamedTuple):
    file: Path
    position: int
    category: str
    message: str
    snippet: str


class Inputs(ActionInputs):
    root_folder: Path = Path(".")
    file_pattern: str = "**/*.xml"
    huge_files: bool = False
    validate: bool = False


class Outputs(ActionOutputs):
    errors_html: str
    errors_json: bytes


class Action(ActionBase):
    inputs: Inputs
    outputs: Outputs

    def main(self):
        # newer versions of xmllint also have --pedantic and --strict-namespace
        self.xmllint_options = (
            ["--noout"]
            + ["--huge"] * self.inputs.huge_files
            + ["--validate"] * self.inputs.validate
        )

        errors: list[Error] = []

        for file in self.iterate_files():
            errors.extend(self.validate_file(file))

        self.outputs.errors_json = json.dumps([self.error_as_dict(e) for e in errors])
        self.outputs.errors_html = self.render(
            dedent(
                """\
                |Category|File path|Position|Error message|Snippet|
                |--------|---------|--------|-------------|-------|
                {% for error in errors -%}
                  |{{ error.category }}|{{ error.file }}|{{ error.position }}|{{ error.message }}|`{{ error.snippet }}`
                {%- endfor %}
                """
            ),
            errors=errors,
        )

        summary_header = "## xmllint validation report\n\n"
        if errors:
            self.summary = summary_header + self.outputs.errors_html
            raise SystemExit(1)
        else:
            self.summary = summary_header + "Validation succeeded without errors."

    def iterate_files(self) -> Iterator[Path]:
        for file in (Path.cwd() / self.inputs.root_folder).rglob(
            self.inputs.file_pattern
        ):
            assert file.is_file(follow_symlinks=True)
            yield file

    def validate_file(self, file: Path) -> list[Error]:
        process_result = subprocess.run(
            ["xmllint"] + self.xmllint_options + [file], capture_output=True, text=True
        )
        if errors := self.parse_xmllint_output(process_result.stderr):
            assert process_result.returncode != 0
        else:
            assert process_result.returncode == 0
        return errors

    def parse_xmllint_output(self, output: str) -> list[Error]:
        errors: list[Error] = []

        lines = output.splitlines()
        assert len(lines) % 3 == 0

        for message, snippet, pointer in batched(lines, n=3):
            match = match_error_message(message)
            assert match, message

            errors.append(
                Error(
                    file=match.group("file"),
                    position=int(match.group("position")),
                    category={"parser": "syntax", "validity": "validity"}[
                        match.group("category")
                    ],
                    message=match.group("message"),
                    snippet=f"{snippet}\n{pointer}",
                )
            )

        return errors

    @staticmethod
    def error_as_dict(error: Error) -> dict:
        return {
            "file": error.file,
            "positon": error.position,
            "category": error.category,
            "message": error.message,
            "snippet": error.snippet,
        }


if __name__ == "__main__":
    # TODO validate xmllint version
    Action().run()
