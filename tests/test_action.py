import pytest

from xmllint_action import Action


@pytest.mark.parametrize(
    ("filename", "line"),
    (
        ("file01", 0),
        ("file02", 1),
        ("file03", 2),
    ),
)
def test_line_and_column(files_folder, filename, line):
    action = Action()

    errors = action.validate_file(files_folder / f"{filename}.xml")
    assert len(errors) == 1

    error = errors[0]
    assert error["line"] == line
