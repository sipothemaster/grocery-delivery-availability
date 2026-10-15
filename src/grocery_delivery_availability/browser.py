"""Minimal Playwright lifecycle shared by browser-session retailers."""

from __future__ import annotations

import tempfile
from typing import Any


class BrowserSession:
    def __init__(
        self,
        *,
        headless: bool = True,
        channel: str | None = None,
        executable_path: str | None = None,
        cdp_url: str | None = None,
        preferred_page_url: str | None = None,
    ) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - import error depends on installation
            raise RuntimeError("Browser retailers require the playwright package") from exc

        self._closed = False
        self._attached = bool(cdp_url)
        self._profile: tempfile.TemporaryDirectory[str] | None = None
        self._playwright = sync_playwright().start()
        if cdp_url:
            self._browser = self._playwright.chromium.connect_over_cdp(cdp_url)
            if not self._browser.contexts:
                self._playwright.stop()
                raise RuntimeError("The attached browser has no usable context")
            pages = [page for context in self._browser.contexts for page in context.pages]
            self.page = next(
                (
                    page
                    for page in pages
                    if preferred_page_url and preferred_page_url in page.url
                ),
                None,
            )
            self.context = (
                self.page.context if self.page is not None else self._browser.contexts[0]
            )
            if self.page is None:
                self.page = self.context.new_page()
            self.context.set_default_timeout(15_000)
            self.context.set_default_navigation_timeout(45_000)
            return

        self._profile = tempfile.TemporaryDirectory(
            prefix="grocery-availability-", ignore_cleanup_errors=True
        )
        options: dict[str, Any] = {
            "headless": headless,
            "locale": "en-GB",
            "viewport": {"width": 1365, "height": 900},
            "args": ["--disable-dev-shm-usage"],
        }
        if channel:
            options["channel"] = channel
        if executable_path:
            options["executable_path"] = executable_path
        self.context = self._playwright.chromium.launch_persistent_context(
            self._profile.name, **options
        )
        self.context.set_default_timeout(15_000)
        self.context.set_default_navigation_timeout(45_000)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._attached:
            self._playwright.stop()
            return
        try:
            self.context.close()
        finally:
            self._playwright.stop()
            if self._profile is not None:
                self._profile.cleanup()
