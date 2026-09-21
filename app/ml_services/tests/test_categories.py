from ml_service.api.schemas import BusinessCategory


def test_supported_business_categories_are_stable() -> None:
    assert len(BusinessCategory) == 11
    assert BusinessCategory.OTHER.value == "OTHER"
