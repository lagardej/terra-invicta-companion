import json
import subprocess
import sys
from pathlib import Path


def test_cli_generates_file(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "json2pydantic.py"

    data = {
        "name": "Example",
        "count": 3,
        "nested": {"flag": True, "value": 1.5},
        "items": [{"id": 1, "label": "a"}],
    }
    inpath = tmp_path / "sample.json"
    inpath.write_text(json.dumps(data), encoding="utf-8")

    outdir = tmp_path / "out"
    outdir.mkdir()

    res = subprocess.run(
        [sys.executable, str(script), str(inpath), "--outdir", str(outdir)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr

    out_file = outdir / "sample.py"
    assert out_file.exists()
    txt = out_file.read_text(encoding="utf-8")
    # basic checks on generated content
    assert "class Sample(" in txt or "class Sample(BaseModel):" in txt
    assert "name: str" in txt
    assert "count: int" in txt
    assert "nested: Nested" in txt or "nested: Any" in txt
