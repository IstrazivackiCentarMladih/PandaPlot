"""Tests for the note search service.

Covers matching in title and content, the case/whole-word/regex options,
result ordering, the per-note match cap, snippet building, and invalid-regex
handling.
"""

from dataclasses import dataclass

import pytest

from pandaplot.services.note_search.note_search_service import (
    QueryError,
    build_snippet,
    search_notes,
)


@dataclass
class FakeNote:
    id: str
    name: str
    content: str


def _notes():
    return [
        FakeNote("1", "Physics", "Energy equals mass times c squared.\nSecond line about energy."),
        FakeNote("2", "Chemistry", "Water is H2O.\nEnergy of activation matters."),
        FakeNote("3", "Empty", ""),
    ]


def test_empty_query_returns_nothing():
    assert search_notes(_notes(), "") == []
    assert search_notes(_notes(), "   ") == []


def test_matches_across_notes_content():
    results = search_notes(_notes(), "energy")
    ids = {r.note_id for r in results}
    assert ids == {"1", "2"}


def test_case_insensitive_by_default():
    assert search_notes(_notes(), "ENERGY")
    assert search_notes(_notes(), "energy")


def test_case_sensitive_option():
    assert search_notes(_notes(), "ENERGY", case_sensitive=True) == []
    assert search_notes(_notes(), "Energy", case_sensitive=True)


def test_title_match_is_flagged_and_first():
    results = search_notes(_notes(), "Physics")
    assert len(results) == 1
    first = results[0].matches[0]
    assert first.in_title is True
    assert first.line_number == 0


def test_line_numbers_are_one_based():
    results = search_notes(_notes(), "Second line")
    match = results[0].matches[0]
    assert match.line_number == 2


def test_whole_word_option():
    notes = [FakeNote("1", "n", "cat category cats")]
    # Substring match hits all three tokens.
    assert search_notes(notes, "cat")[0].match_count == 3
    # Whole word only matches the standalone "cat".
    assert search_notes(notes, "cat", whole_word=True)[0].match_count == 1


def test_regex_option():
    notes = [FakeNote("1", "n", "value=42 and value=7")]
    results = search_notes(notes, r"value=\d+", use_regex=True)
    assert results[0].match_count == 2


def test_plain_query_treats_metacharacters_literally():
    notes = [FakeNote("1", "n", "a.b and axb")]
    # Without regex, "a.b" should match only the literal "a.b".
    assert search_notes(notes, "a.b")[0].match_count == 1


def test_invalid_regex_raises_query_error():
    with pytest.raises(QueryError):
        search_notes(_notes(), "(unclosed", use_regex=True)


def test_results_sorted_by_match_count_desc():
    notes = [
        FakeNote("few", "a", "energy"),
        FakeNote("many", "b", "energy energy energy"),
    ]
    results = search_notes(notes, "energy")
    assert [r.note_id for r in results] == ["many", "few"]


def test_zero_width_regex_is_ignored():
    notes = [FakeNote("1", "n", "abc")]
    # 'x?' matches empty string everywhere; must not produce matches or hang.
    assert search_notes(notes, "x?", use_regex=True) == []


def test_per_note_match_cap():
    notes = [FakeNote("1", "n", "a " * 500)]
    result = search_notes(notes, "a")[0]
    assert result.match_count == 200
    assert result.truncated is True


def test_build_snippet_highlights_match():
    from pandaplot.services.note_search.note_search_service import NoteMatch

    match = NoteMatch(line_number=1, line_text="the quick brown fox", match_start=4, match_end=9)
    text, start, end = build_snippet(match)
    assert text[start:end] == "quick"


def test_build_snippet_trims_long_lines():
    from pandaplot.services.note_search.note_search_service import NoteMatch

    line = "x" * 100 + "TARGET" + "y" * 100
    match = NoteMatch(line_number=1, line_text=line, match_start=100, match_end=106)
    text, start, end = build_snippet(match, context=10)
    assert text[start:end] == "TARGET"
    assert text.startswith("…") and text.endswith("…")
