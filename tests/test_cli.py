from app.cli import main


def test_cli_init_db(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["trend-radar", "init-db"])
    main()
    captured = capsys.readouterr()
    assert "database_initialized" in captured.out
