import os
from pathlib import Path

import pytest

SAMPLES = Path(os.environ["HWPPIPE_SAMPLES"]) if os.environ.get("HWPPIPE_SAMPLES") else None


def pytest_collection_modifyitems(config, items):
    if SAMPLES is None:
        skip = pytest.mark.skip(reason="HWPPIPE_SAMPLES가 설정되지 않음")
        for item in items:
            if item.fspath.basename == "test_real_docs.py":
                item.add_marker(skip)
