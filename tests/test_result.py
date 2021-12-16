import pytest


class TestResultWriter:
    def test_basic(self, monkeypatch):
        monkeypatch.setenv("IN_KIND", "FILE")
        monkeypatch.setenv("IN_FILENAME", "tests/fixtures/result_input.txt")
        from apihub.result import ResultWriter

        try:
            writer = ResultWriter()
            writer.parse_args()
            writer.start()
        except Exception:
            pytest.fail("worker raised exception")

    def test_command(self, monkeypatch):
        monkeypatch.setenv("IN_KIND", "FILE")
        monkeypatch.setenv("MONITORING", "FILE")
        monkeypatch.setenv("IN_FILENAME", "tests/fixtures/result_command.json")
        from apihub.result import ResultWriter

        try:
            writer = ResultWriter(debug=False, monitoring=False)
            writer.parse_args()
            writer.start()
        except Exception:
            pytest.fail("worker raised exception")
