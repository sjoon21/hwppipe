import json, shutil, pytest
from helpers import FIX
from hwppipe import cli
from hwppipe.cli import main

def test_single_file(tmp_path):
    assert main([str(FIX / "SimpleTable.hwpx"), "-o", str(tmp_path)]) == 0
    assert (tmp_path / "SimpleTable/document.md").exists()

def test_tree_mirrors_structure(tmp_path):
    src = tmp_path / "in"; (src / "2025").mkdir(parents=True)
    shutil.copy(FIX / "SimpleTable.hwpx", src / "2025/a.hwpx")
    (src / "b.hwp").write_bytes(b"\xD0\xCF\x11\xE0" + b"\0" * 100)
    (src / "c.docx").write_bytes(b"PK")
    main([str(src), "-o", str(tmp_path / "out")])
    assert (tmp_path / "out/2025/a/document.md").exists()
    s = json.loads((tmp_path / "out/report.json").read_text(encoding="utf-8"))
    assert s["documents"] == [{"input": "2025/a.hwpx", "output": "2025/a", "status": "ok"}]
    assert s["unsupported"] == ["b.hwp"]          # .docx는 무시
    assert not (tmp_path / "out/b").exists()

def test_tree_case_collision(tmp_path):
    src = tmp_path / "in"; src.mkdir()
    shutil.copy(FIX / "SimpleTable.hwpx", src / "a.hwpx")
    if (src / "A.HWPX").exists():
        pytest.skip("대소문자를 구분하지 않는 파일 시스템")
    shutil.copy(FIX / "SimpleTable.hwpx", src / "a.HWPX")
    main([str(src), "-o", str(tmp_path / "out")])
    s = json.loads((tmp_path / "out/report.json").read_text(encoding="utf-8"))
    assert [d["output"] for d in s["documents"]] == ["a", "a~2"]
    assert s["collisions"] == [{"input": "a.hwpx", "output": "a~2"}]

def test_one_failure_does_not_stop_batch(tmp_path, monkeypatch):
    src = tmp_path / "in"; src.mkdir()
    for n in ("a.hwpx", "b.hwpx"): shutil.copy(FIX / "SimpleTable.hwpx", src / n)
    real = cli.convert
    def flaky(p, out, *args):
        if p.name == "a.hwpx": raise RuntimeError("boom")
        return real(p, out, *args)
    monkeypatch.setattr(cli, "convert", flaky)
    code = main([str(src), "-o", str(tmp_path / "out")])
    s = json.loads((tmp_path / "out/report.json").read_text(encoding="utf-8"))
    assert [(d["input"], d["status"]) for d in s["documents"]] == [("a.hwpx", "error"), ("b.hwpx", "ok")]
    assert "boom" in s["documents"][0]["error"]
    assert code == 1


def test_version(capsys):
    import hwppipe
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0 and capsys.readouterr().out.strip() == f"hwppipe {hwppipe.__version__}"


def test_python_m_entry(tmp_path):
    import subprocess, sys
    r = subprocess.run([sys.executable, "-m", "hwppipe", str(FIX / "SimpleTable.hwpx"), "-o", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0 and (tmp_path / "SimpleTable/graph.json").exists()


def test_progress_survives_non_utf8_console(tmp_path, monkeypatch):
    import io, sys
    src = tmp_path / "한글.hwpx"
    shutil.copy(FIX / "SimpleTable.hwpx", src)
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    assert main([str(src), "-o", str(tmp_path / "out")]) == 0
