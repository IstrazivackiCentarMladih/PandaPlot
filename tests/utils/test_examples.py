import json
import zipfile
from pathlib import Path

from pandaplot.utils.examples import discover_example_projects


def _write_pplot(path: Path, name: str, description: str):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("project.json", json.dumps({"name": name, "description": description}))


class TestDiscoverExampleProjects:
    def test_missing_directory_returns_empty_list(self, tmp_path):
        assert discover_example_projects(tmp_path / "does-not-exist") == []

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert discover_example_projects(tmp_path) == []

    def test_reads_name_and_description_from_each_pplot(self, tmp_path):
        _write_pplot(tmp_path / "a.pplot", "Project A", "Description A")
        _write_pplot(tmp_path / "b.pplot", "Project B", "Description B")

        examples = discover_example_projects(tmp_path)

        assert {e["name"] for e in examples} == {"Project A", "Project B"}
        by_name = {e["name"]: e for e in examples}
        assert by_name["Project A"]["description"] == "Description A"
        assert by_name["Project A"]["path"] == str(tmp_path / "a.pplot")

    def test_finds_pplot_files_in_subdirectories(self, tmp_path):
        subdir = tmp_path / "nested"
        subdir.mkdir()
        _write_pplot(subdir / "nested.pplot", "Nested Project", "Nested description")

        examples = discover_example_projects(tmp_path)

        assert len(examples) == 1
        assert examples[0]["name"] == "Nested Project"

    def test_skips_corrupt_pplot_file(self, tmp_path):
        (tmp_path / "corrupt.pplot").write_text("not a zip file")
        _write_pplot(tmp_path / "valid.pplot", "Valid Project", "Valid description")

        examples = discover_example_projects(tmp_path)

        assert len(examples) == 1
        assert examples[0]["name"] == "Valid Project"

    def test_skips_pplot_without_project_json(self, tmp_path):
        with zipfile.ZipFile(tmp_path / "no_meta.pplot", "w") as archive:
            archive.writestr("items/something.json", "{}")

        assert discover_example_projects(tmp_path) == []

    def test_missing_name_falls_back_to_filename_stem(self, tmp_path):
        with zipfile.ZipFile(tmp_path / "fallback.pplot", "w") as archive:
            archive.writestr("project.json", json.dumps({"description": "No name field"}))

        examples = discover_example_projects(tmp_path)

        assert examples[0]["name"] == "fallback"
        assert examples[0]["description"] == "No name field"
