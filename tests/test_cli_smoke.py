from tastingsets.cli import main


def test_main_without_command_returns_zero(capsys):
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()
