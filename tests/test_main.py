from pytop.__main__ import main


def test_success():
    assert main() == 0
