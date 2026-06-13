from rmlst_cli import http


class DummyResponse:
    status_code = 200
    text = ""

    def json(self):
        return {"ok": True}


class DummySession:
    def post(self, *args, **kwargs):
        return DummyResponse()


def test_debug_output_goes_to_stderr(capsys):
    result = http._make_request(
        DummySession(),
        http.DEFAULT_URI,
        {"base64": True, "details": True, "sequence": "QQ=="},
        retries=0,
        retry_delay=0,
        debug=True,
    )

    captured = capsys.readouterr()
    assert result == {"ok": True}
    assert captured.out == ""
    assert "DEBUG: Attempt 1" in captured.err
    assert "DEBUG: Response 200" in captured.err
