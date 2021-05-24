class TestResultWriter:
    def test_basic(self, monkeypatch):
        monkeypatch.setenv("IN_KIND", "LREDIS")
        from apihub.result import ResultWriter

        writer = ResultWriter()
        writer.parse_args()
