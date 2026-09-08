"""Chat transcript scrolling."""

from textual.containers import VerticalScroll


class ChatLog(VerticalScroll):
    """Transcript that follows new content until the user scrolls away."""

    _following_tail = True

    @property
    def following_tail(self) -> bool:
        return self._following_tail

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        self._following_tail = self.is_vertical_scroll_end

    def follow_new_content(self, *, force: bool = False) -> None:
        if force:
            self._following_tail = True
        if self._following_tail:
            self.call_after_refresh(self._follow_tail_after_refresh)

    def _follow_tail_after_refresh(self) -> None:
        if self._following_tail:
            self.scroll_end(animate=False)
