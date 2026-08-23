"""Unit tests for the pure per-component change classifier."""

from app.domain.change_classifier import classify_change
from app.models.enums.bump_level import BumpLevel


def test_newly_added_component_is_minor() -> None:
    """A component absent from the prior manifest classifies as MINOR (G-P9b)."""
    # Act
    result = classify_change(None, (1, 0, 0, None))

    # Assert
    assert result is BumpLevel.MINOR


def test_major_change_is_major() -> None:
    """A differing major position classifies as MAJOR."""
    # Assert
    assert classify_change((1, 2, 3, None), (2, 0, 0, None)) is BumpLevel.MAJOR


def test_minor_change_is_minor() -> None:
    """A differing minor position (major equal) classifies as MINOR."""
    # Assert
    assert classify_change((1, 2, 3, None), (1, 3, 0, None)) is BumpLevel.MINOR


def test_patch_change_is_patch() -> None:
    """A differing patch position (major/minor equal) classifies as PATCH."""
    # Assert
    assert classify_change((1, 2, 3, None), (1, 2, 4, None)) is BumpLevel.PATCH


def test_prerelease_only_change_is_patch() -> None:
    """A prerelease-only difference classifies as PATCH (G-P9c)."""
    # Assert
    assert classify_change((3, 4, 1, None), (3, 4, 1, "rc.2")) is BumpLevel.PATCH


def test_identical_version_is_none() -> None:
    """No difference at all classifies as NONE."""
    # Assert
    assert classify_change((1, 2, 3, "rc.1"), (1, 2, 3, "rc.1")) is BumpLevel.NONE


def test_regression_is_classified_by_highest_differing_position() -> None:
    """A backward move classifies by position regardless of direction (G-P9g)."""
    # Assert
    assert classify_change((2, 0, 0, None), (1, 0, 0, None)) is BumpLevel.MAJOR
    assert classify_change((2, 5, 3, None), (2, 5, 1, None)) is BumpLevel.PATCH


def test_empty_prerelease_and_none_are_equivalent() -> None:
    """An empty-string prerelease is treated as no prerelease."""
    # Assert
    assert classify_change((1, 0, 0, ""), (1, 0, 0, None)) is BumpLevel.NONE
