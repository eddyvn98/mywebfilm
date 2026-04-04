import os

import pytest

from llm_service import normalize_metadata_with_llm
from search_service import search_jav_context


def _integration_enabled():
    # This test hits external dependencies (search + local LLM).
    # Enable explicitly when needed:
    #   $env:RUN_LLM_INTEGRATION_TESTS='1'
    return os.getenv("RUN_LLM_INTEGRATION_TESTS") == "1"


@pytest.mark.parametrize(
    "filename",
    [
        "ADN-413.mp4",
        "MEYD-855-Uncensored.ts",
        "IMG_20220430_134834.jpg",
    ],
)
def test_llm_pipeline(filename):
    if not _integration_enabled():
        pytest.skip("Set RUN_LLM_INTEGRATION_TESTS=1 to run LLM integration tests")

    context = search_jav_context(filename)
    assert isinstance(context, str)

    result = normalize_metadata_with_llm(filename, context)
    # Allow None when model/search does not yield a reliable output.
    assert result is None or isinstance(result, dict)
