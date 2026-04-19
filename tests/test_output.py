"""Tests for orca_cli.core.output — print_list / print_detail rendering modes."""

from __future__ import annotations

import json

from click.testing import CliRunner

from orca_cli.core.output import print_detail, print_list


def _capture(fn, *args, **kwargs):
    """Invoke a function that writes via click.echo/console and return the captured stdout."""
    runner = CliRunner()
    import click

    @click.command()
    def _wrap():
        fn(*args, **kwargs)

    result = runner.invoke(_wrap, [], catch_exceptions=False)
    return result.output


class TestPrintListEmpty:

    def test_empty_list_table_mode_shows_yellow_msg(self):
        out = _capture(print_list, [], [("ID", "id")], empty_msg="Nothing here.")
        assert "Nothing here." in out

    def test_empty_list_json_mode_prints_brackets(self):
        out = _capture(print_list, [], [("ID", "id")], output_format="json")
        assert out.strip() == "[]"

    def test_empty_list_value_mode_prints_empty_msg(self):
        """Non-JSON empty output falls into the same yellow-msg branch."""
        out = _capture(print_list, [], [("ID", "id")], output_format="value")
        assert "No results found." in out


class TestPrintListJson:

    def test_json_indent_by_default(self):
        items = [{"id": "1", "name": "foo"}]
        out = _capture(print_list, items, [("ID", "id"), ("Name", "name")], output_format="json")
        assert '\n  "ID"' in out or '"ID": "1"' in out
        data = json.loads(out)
        assert data == [{"ID": "1", "Name": "foo"}]

    def test_json_noindent_compact(self):
        items = [{"id": "1"}]
        out = _capture(print_list, items, [("ID", "id")], output_format="json", noindent=True)
        assert "\n" not in out.strip()
        assert json.loads(out) == [{"ID": "1"}]


class TestPrintListValue:

    def test_value_mode_space_separated(self):
        items = [{"id": "1", "name": "foo"}, {"id": "2", "name": "bar"}]
        out = _capture(
            print_list, items, [("ID", "id"), ("Name", "name")], output_format="value"
        )
        lines = out.strip().split("\n")
        assert lines == ["1 foo", "2 bar"]


class TestPrintListColumnFilter:

    def test_columns_filter_case_insensitive(self):
        items = [{"id": "1", "name": "foo", "status": "ACTIVE"}]
        out = _capture(
            print_list,
            items,
            [("ID", "id"), ("Name", "name"), ("Status", "status")],
            output_format="json",
            columns=("name", "STATUS"),
        )
        data = json.loads(out)
        assert data == [{"Name": "foo", "Status": "ACTIVE"}]


class TestPrintListTable:

    def test_fit_width_renders(self):
        items = [{"id": "1", "name": "foo"}]
        out = _capture(
            print_list, items, [("ID", "id"), ("Name", "name")], fit_width=True
        )
        assert "foo" in out

    def test_max_width_renders(self):
        items = [{"id": "1", "name": "foo"}]
        out = _capture(
            print_list, items, [("ID", "id"), ("Name", "name")], max_width=40
        )
        assert "foo" in out

    def test_max_width_zero_unlimited(self):
        items = [{"id": "1"}]
        out = _capture(print_list, items, [("ID", "id")], max_width=0)
        assert "1" in out


class TestPrintDetail:

    def test_json_mode(self):
        out = _capture(
            print_detail, [("Field1", "v1"), ("Field2", 42)], output_format="json"
        )
        assert json.loads(out) == {"Field1": "v1", "Field2": 42}

    def test_json_noindent(self):
        out = _capture(
            print_detail,
            [("F", "v")],
            output_format="json",
            noindent=True,
        )
        assert out.strip() == '{"F": "v"}'

    def test_value_mode(self):
        out = _capture(
            print_detail,
            [("ID", "1"), ("Name", "foo"), ("Empty", None)],
            output_format="value",
        )
        # None becomes "" and click.echo adds a newline, so the trailing empty
        # line is preserved inside the output (splitting on non-stripped output).
        lines = out.split("\n")
        assert lines[0] == "1"
        assert lines[1] == "foo"
        assert lines[2] == ""  # the None-valued row

    def test_columns_filter(self):
        out = _capture(
            print_detail,
            [("ID", "1"), ("Name", "foo")],
            output_format="json",
            columns=("name",),
        )
        assert json.loads(out) == {"Name": "foo"}

    def test_table_fit_width(self):
        out = _capture(print_detail, [("F", "v")], fit_width=True)
        assert "v" in out

    def test_table_max_width(self):
        out = _capture(print_detail, [("F", "v")], max_width=40)
        assert "v" in out
