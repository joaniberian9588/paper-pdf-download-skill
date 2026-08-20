import sys
from types import SimpleNamespace

from paper_pdf.browser_session import CloakPublisherSession
from paper_pdf.config import AppConfig
from paper_pdf.publishers import get_profile


class FakePage:
    def set_default_timeout(self, timeout: int) -> None:
        self.timeout = timeout


class FakeContext:
    def __init__(self) -> None:
        self.pages = [FakePage()]
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_persistent_launch_passes_only_supported_wrapper_arguments(tmp_path, monkeypatch) -> None:
    captured = {}
    context = FakeContext()

    def fake_launch(path, **kwargs):
        captured["path"] = path
        captured.update(kwargs)
        return context

    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        SimpleNamespace(launch_persistent_context=fake_launch),
    )
    config = AppConfig()
    config.browser.profile_dir = tmp_path
    with CloakPublisherSession(get_profile("plos"), config):
        pass
    assert "auto_update" not in captured
    assert captured["headless"] is True
    assert context.closed
