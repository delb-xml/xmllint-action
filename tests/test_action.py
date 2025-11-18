import pytest

from xmllint_action import Action


@pytest.mark.parametrize(
    ("filename", "line"),
    (
        ("file01", 1),
        ("file02", 2),
        ("file03", 3),
    ),
)
def test_line_and_column(files_folder, filename, line):
    action = Action()

    errors = action.validate_file(files_folder / f"{filename}.xml")
    assert len(errors) == 1

    error = errors[0]
    assert error["line"] == line
