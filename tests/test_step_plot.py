"""A smoke test of tools/step_plot.py: it must build the code, run the scenarios and write a picture (whatever the controller does)."""
import step_plot


def test_the_plot_tool_writes_a_picture(tmp_path):
    out = tmp_path / "figure.png"
    assert step_plot.main(["--out", str(out), "--gains", "0.25", "0.025", "0"]) == 0
    assert out.stat().st_size > 20000
