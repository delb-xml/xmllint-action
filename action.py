import json
import re
import subprocess
from collections.abc import Iterator
from itertools import batched
from typing import Final, TypedDict

from pathlib import Path

from github_custom_actions import ActionBase, ActionInputs, ActionOutputs


match_error_message: Final = re.compile(
    r"(?P<file>.+):(?P<position>\d+): "
    r"(?P<category>parser|validity) error : "
    r"(?P<message>.+)"
).fullmatch


def crunch_whitespace(s: str) -> str:
    s = s.replace("\n", " ")
    while "   " in s:
        s = s.replace("   ", "")
    while "  " in s:
        s = s.replace("  ", "")
    return s


SUMMARY_ERRORS_TABLE_TEMPLATE: Final = crunch_whitespace(
    """\
<table>
  <thead>
    <tr>
    <th>Category</th>
    <th>Error message</th>
    <th>File path</th>
    <th>Position</th>
    </tr>
  </thead>
  <tbody>
    {% for error in errors -%}
    <tr>
    <td>{{ error.category }}</td>
    <td>{{ error.message }}</td>
    <td><code>{{ error.file|e }}</code></td>
    <td>{{ error.position }}</td>
    </tr>
    <td colspan="4"><pre>{{ error.snippet.splitlines()[0]|e }}<br>{{ error.snippet.splitlines()[1][1:]|e }}</pre></td>
    </tr>
    {%- endfor %}
  </tbody>
</table>
"""
)
WORKSPACE_DIRECTORY: Final = Path.cwd()


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Path):
            return str(o)
        else:
            return super().default(o)


class Error(TypedDict):
    file: Path
    line: int
    column: int
    category: str
    message: str
    snippet: str


class Inputs(ActionInputs):
    root_folder: Path = Path(".")
    file_pattern: str = "**/*.xml"
    huge_files: str = "off"
    validate: str = "off"


class Outputs(ActionOutputs):
    errors_html: str
    errors_json: str


class Action(ActionBase):
    inputs: Inputs
    outputs: Outputs

    def main(self):
        if self.inputs.root_folder.is_absolute():
            raise ValueError(
                "The root path must be a relative one to the current working directory."
            )

        errors: list[Error] = []
        # newer versions of xmllint also have --pedantic and --strict-namespace
        self.xmllint_options = (
            ["--noout"]
            + ["--huge"] * (self.inputs.huge_files == "on")
            + ["--validate"] * (self.inputs.validate == "on")
        )

        for file in self.iterate_files():
            errors.extend(self.validate_file(file))

        self.emit_error_messages(errors)
        self.outputs.errors_json = json.dumps(errors, cls=JSONEncoder)
        errors_html = self.render(SUMMARY_ERRORS_TABLE_TEMPLATE, errors=errors)
        assert "\n" not in errors_html, errors_html
        self.outputs.errors_html = errors_html

        summary_header = "## xmllint Validation Report\n\n"
        if errors:
            self.summary = summary_header + errors_html
            raise SystemExit(1)
        else:
            self.summary = summary_header + "Validation succeeded without errors."

    def iterate_files(self) -> Iterator[Path]:
        for file in (WORKSPACE_DIRECTORY / self.inputs.root_folder).rglob(
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

            line, column = self.get_line_and_column(
                Path(match.group("file")), int(match.group("position"))
            )
            errors.append(
                {
                    "file": Path(match.group("file")).relative_to(WORKSPACE_DIRECTORY),
                    "line": line,
                    "column": column,
                    "category": {"parser": "syntax", "validity": "validity"}[
                        match.group("category")
                    ],
                    "message": match.group("message"),
                    "snippet": f"{snippet}\n{pointer}",
                }
            )

        return errors

    def get_line_and_column(self, file: Path, position: int) -> tuple[int, int]:
        data = b""
        with file.open("rb") as f:
            while (remaining_bytes := position - len(data)) > 0:
                data += f.read(remaining_bytes)
        data = data[:position]

        last_newline_position = data.rfind(b"\n")

        column = (
            position
            - last_newline_position
            # offsetting the fact that position starts counting w/ 1
            - 1
        )
        assert column >= 0

        previous_lines_data = data[:last_newline_position]
        if previous_lines_data:
            assert previous_lines_data.endswith(b"\n")
        line = previous_lines_data.count(b"\n")
        assert line >= 0

        return line, column

    def emit_error_messages(self, errors: list[Error]):
        for error in errors:
            self.error_message(
                error["message"],
                title=f"xmllint {error['category']} error",
                file=error["file"],
                line=error["line"],
                column=error["column"],
            )


if __name__ == "__main__":
    # TODO validate xmllint version
    Action().run()
