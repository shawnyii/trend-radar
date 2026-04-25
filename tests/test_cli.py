import subprocess
import sys

from app.cli import main


def test_cli_init_db(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["trend-radar", "init-db"])
    main()
    captured = capsys.readouterr()
    assert "database_initialized" in captured.out


def test_cli_module_entrypoint_init_db():
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "init-db"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "database_initialized" in result.stdout
