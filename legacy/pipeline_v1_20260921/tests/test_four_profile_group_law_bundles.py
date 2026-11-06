import pytest

from src.law_bundles import FourProfileGroupLawBundleRouter


def test_four_profile_router_uses_only_metadata_conditions() -> None:
    assert FourProfileGroupLawBundleRouter.profile_for_record(
        {"id": "n", "meta": {"적용계약법": "국가계약법"}}
    ) == "national"
    assert FourProfileGroupLawBundleRouter.profile_for_record(
        {"id": "g", "meta": {"적용계약법": "지방계약법"}}
    ) == "local_general"
    assert FourProfileGroupLawBundleRouter.profile_for_record(
        {"id": "s", "meta": {"적용계약법": "지방계약법", "계약방법": "수의계약"}}
    ) == "local_small"
    assert FourProfileGroupLawBundleRouter.profile_for_record(
        {"id": "h", "meta": {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약"}}
    ) == "local_negotiated"


def test_four_profile_router_fails_for_unbuilt_fifth_profile() -> None:
    with pytest.raises(ValueError, match="unbuilt fifth profile"):
        FourProfileGroupLawBundleRouter.profile_for_record(
            {
                "id": "both",
                "meta": {
                    "적용계약법": "지방계약법",
                    "계약방법": "수의계약",
                    "낙찰방법": "협상에의한계약",
                },
            }
        )
