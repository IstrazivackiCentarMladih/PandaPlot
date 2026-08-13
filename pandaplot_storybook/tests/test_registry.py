import pytest

from pandaplot_storybook.registry import BoolControl, StoryDef, all_story_names, get_story, story


def test_story_registers_and_is_retrievable():
    @story("__TestWidget__")
    def _build() -> StoryDef:
        return StoryDef(controls=[BoolControl("flag", True)], make_widget=lambda values, tokens: None)

    assert "__TestWidget__" in all_story_names()
    story_def = get_story("__TestWidget__")
    assert story_def.controls[0].name == "flag"
    assert story_def.controls[0].default is True


def test_registering_the_same_name_twice_raises():
    @story("__TestWidgetTwo__")
    def _build() -> StoryDef:
        return StoryDef(controls=[], make_widget=lambda values, tokens: None)

    with pytest.raises(ValueError):
        @story("__TestWidgetTwo__")
        def _build_again() -> StoryDef:
            return StoryDef(controls=[], make_widget=lambda values, tokens: None)
