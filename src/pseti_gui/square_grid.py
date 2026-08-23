from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class SquareGridContainer(QWidget):
    """A rows x cols grid of square cells that always fills as much of this
    widget's assigned area as it can without distorting cell aspect ratio.

    A plain QGridLayout stretches each cell to whatever width/height its row
    and column happen to get, which is square only when the container's
    aspect ratio already matches rows:cols. This widget instead manages
    child geometry itself: on every resize it picks the largest square cell
    size that still fits `cols` columns and `rows` rows in the available
    space, then centers the resulting grid (letterboxing any leftover
    space on whichever axis doesn't divide evenly).
    """

    def __init__(self, rows: int, cols: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows = rows
        self._cols = cols
        self._widgets: dict[tuple[int, int], QWidget] = {}

    def add_widget(self, widget: QWidget, row: int, col: int) -> None:
        """Place `widget` at (row, col), replacing and disposing of whatever was there."""
        key = (row, col)
        old = self._widgets.get(key)
        if old is not None and old is not widget:
            old.setParent(None)
            old.deleteLater()
        widget.setParent(self)
        widget.show()
        self._widgets[key] = widget
        self._relayout()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        if self._rows <= 0 or self._cols <= 0:
            return
        cell = max(1, min(self.width() // self._cols, self.height() // self._rows))
        grid_w = cell * self._cols
        grid_h = cell * self._rows
        x0 = (self.width() - grid_w) // 2
        y0 = (self.height() - grid_h) // 2
        for (row, col), widget in self._widgets.items():
            widget.setGeometry(x0 + col * cell, y0 + row * cell, cell, cell)
