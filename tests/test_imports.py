"""Import-order regression tests."""

import subprocess
import sys


def test_token_budget_imports_before_llm_router():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.utils.token_budget; import app.llm.router",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
