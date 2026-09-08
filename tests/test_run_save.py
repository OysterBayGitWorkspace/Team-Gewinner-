import json

import run
from pulse.workers import WorkerResult


def test_failed_result_never_overwrites_saved_good_one(tmp_path):
    good = WorkerResult("w", True, {"n": 1}, None, None, 1.0, 0.1, 1)
    bad = WorkerResult("w", False, None, "spend limit", "quota", 0.1, 0.0, 1)
    run.save_result(tmp_path, good)
    run.save_result(tmp_path, bad)
    assert json.loads((tmp_path / "w.json").read_text())["ok"] is True
    # a failed result is saved when nothing good exists, and a good one always replaces a bad one
    run.save_result(tmp_path, WorkerResult("x", False, None, "t", "timeout", 1, 0, 0))
    assert json.loads((tmp_path / "x.json").read_text())["ok"] is False
    run.save_result(tmp_path, WorkerResult("x", True, {"n": 2}, None, None, 1, 0, 1))
    assert json.loads((tmp_path / "x.json").read_text())["data"] == {"n": 2}
