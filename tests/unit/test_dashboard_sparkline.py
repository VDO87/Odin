from __future__ import annotations

from odin_dashboard.formatters import (
    normalize_price_series,
    render_ascii_sparkline,
    render_html_sparkline,
)


def test_sparkline_rendering() -> None:
    series: list[float | int | str] = [1.1, "1.2", 1.15, "bad", 1.3]
    normalized = normalize_price_series(series)
    assert normalized == [1.1, 1.2, 1.15, 1.3]

    ascii_chart = render_ascii_sparkline(series)
    assert ascii_chart != "n/a"
    assert len(ascii_chart) == len(normalized)

    html_chart = render_html_sparkline(series)
    assert "market-sparkline" in html_chart
    assert "sparkline" in html_chart
