import os
import subprocess
import sys
from pathlib import Path


def test_operations_signatures_dir_uses_runtime_env(tmp_path: Path):
    signature_dir = tmp_path / "uploads" / "signatures"
    env = os.environ.copy()
    env.update(
        {
            "DATA_DIR": str(tmp_path / "data"),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
            "SIGNATURE_DIR": str(signature_dir),
            "DATABASE_URL": f"sqlite:///{(tmp_path / 'data' / 'fnlifting.db').as_posix()}",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os; "
                "from pathlib import Path; "
                "from app.api.routes.operations import SIGNATURE_DIR; "
                "from app.core.config import BACKEND_DIR; "
                "print(SIGNATURE_DIR); "
                "assert Path(SIGNATURE_DIR).resolve() == Path(os.environ['SIGNATURE_DIR']).resolve(); "
                "assert str(BACKEND_DIR) not in str(SIGNATURE_DIR)"
            )
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert signature_dir.exists()
