"""Public tests for Lab 01. Students can read, run and re-run these.

    python3 -m pytest tests/test_public.py -v

These are not the whole grade, but nothing that fails here can pass anything
else. They run entirely against the fake machines in tests/fixtures/, so they
work on a laptop, on the board, and in CI — which is the point being made: a
measurement you can only check by having the hardware in front of you is a
measurement nobody will check.

If tests/fixtures/ is missing, run:  python3 tests/make_fixtures.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enee459l import probes, report, schema  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
GOOD = FIX / "nvme_good"
SD = FIX / "sd_boot"
BARE = FIX / "bare"


@pytest.fixture(scope="session", autouse=True)
def _fixtures_exist():
    if not GOOD.exists():
        subprocess.run([sys.executable, str(Path(__file__).parent / "make_fixtures.py")], check=True)


# ---------------------------------------------------------------------------
# Probes read from the root they are given, and only from there.
# ---------------------------------------------------------------------------


def test_module_model_is_read_from_device_tree():
    r = probes.probe_module_model(GOOD)
    assert r["status"] == "ok"
    assert "Orin Nano" in r["value"]
    assert r["source"] == "/proc/device-tree/model"


def test_module_model_strips_the_trailing_nul():
    # The real /proc/device-tree/model node is NUL-terminated. A report with a
    # stray \x00 in it is not valid JSON-safe text on every consumer.
    r = probes.probe_module_model(GOOD)
    assert "\x00" not in r["value"]


def test_memory_is_parsed_as_an_integer_of_kb():
    r = probes.probe_memory_total_kb(GOOD)
    assert r["status"] == "ok"
    assert isinstance(r["value"], int)
    assert r["value"] == 7650000


def test_root_source_detects_nvme():
    r = probes.probe_root_source(GOOD)
    assert r["status"] == "ok"
    assert r["value"] == "/dev/nvme0n1p1"
    assert r["kind"] == "nvme"


def test_root_source_detects_the_sd_card_failure():
    # The whole lab. This unit boots, works, and is wrong.
    r = probes.probe_root_source(SD)
    assert r["status"] == "ok"
    assert r["value"] == "/dev/mmcblk0p1"
    assert r["kind"] != "nvme"


def test_nvme_can_be_fitted_and_still_not_booted_from():
    # Both probes must be independent, or this state is invisible.
    assert probes.probe_nvme_present(SD)["value"] is True
    assert probes.probe_root_source(SD)["kind"] != "nvme"


def test_nvme_absent_is_reported_not_crashed():
    r = probes.probe_nvme_present(BARE)
    assert r["value"] is False


def test_thermal_is_converted_from_millidegrees():
    r = probes.probe_thermal_zones(GOOD)
    assert r["status"] == "ok"
    # 43250 millidegrees is 43.25 C, not 43250 C.
    assert r["value"] == pytest.approx(43.25)
    assert all(0 < z["temp_c"] < 120 for z in r["zones"])


def test_missing_things_become_unknown_with_a_reason_not_an_exception():
    r = probes.probe_thermal_zones(BARE)
    assert r["status"] == "unknown"
    assert r["value"] is None
    assert r["detail"], "an unknown must carry the reason it is unknown"


# ---------------------------------------------------------------------------
# The PCIe link — two numbers, and the gap between them.
# ---------------------------------------------------------------------------


def test_pcie_link_reports_negotiated_and_capable_separately():
    text = (FIX / "lspci_gen4_in_gen3.txt").read_text()
    r = probes.probe_pcie_link(GOOD, lspci_output=text)
    assert r["status"] == "ok"
    assert r["negotiated"]["gen"] == 3
    assert r["negotiated"]["width"] == 4
    assert r["capability"]["gen"] == 4


def test_pcie_link_explains_the_gen4_in_gen3_case():
    text = (FIX / "lspci_gen4_in_gen3.txt").read_text()
    r = probes.probe_pcie_link(GOOD, lspci_output=text)
    assert "interpretation" in r
    assert "Gen3" in r["interpretation"]


def test_pcie_link_does_not_invent_a_shortfall_when_there_is_none():
    text = (FIX / "lspci_gen3_matched.txt").read_text()
    r = probes.probe_pcie_link(GOOD, lspci_output=text)
    assert r["negotiated"]["gen"] == r["capability"]["gen"] == 3
    assert "full capability" in r["interpretation"]


def test_pcie_link_unavailable_is_unknown():
    r = probes.probe_pcie_link(BARE, lspci_output="")
    assert r["status"] == "unknown"


# ---------------------------------------------------------------------------
# Power mode.
# ---------------------------------------------------------------------------


def test_power_mode_is_parsed():
    text = (FIX / "nvpmodel_maxn.txt").read_text()
    r = probes.probe_power_mode(GOOD, nvpmodel_output=text)
    assert r["value"] == "MAXN_SUPER"


def test_power_mode_15w_is_parsed():
    text = (FIX / "nvpmodel_15w.txt").read_text()
    r = probes.probe_power_mode(GOOD, nvpmodel_output=text)
    assert r["value"] == "15W"


# ---------------------------------------------------------------------------
# Every finding carries its source. This is the course's rule, tested.
# ---------------------------------------------------------------------------


def test_every_finding_names_where_it_came_from():
    rep = report.build(root=GOOD, device_id="jetson-test")
    for name, finding in rep["findings"].items():
        assert finding.get("source"), f"finding {name} has no source"


def test_report_validates_against_the_schema():
    rep = report.build(root=GOOD, device_id="jetson-test")
    assert schema.validate(rep) == [], schema.validate(rep)


def test_good_machine_is_ready_for_labs():
    rep = report.build(root=GOOD, device_id="jetson-test")
    assert rep["verdicts"]["boots_from_nvme"]["result"] == "pass"
    assert rep["verdicts"]["nvme_fitted"]["result"] == "pass"
    assert rep["verdicts"]["memory_visible"]["result"] == "pass"


def test_sd_machine_fails_the_right_verdict_and_only_that_one():
    rep = report.build(root=SD, device_id="jetson-test")
    assert rep["verdicts"]["boots_from_nvme"]["result"] == "fail"
    assert rep["verdicts"]["nvme_fitted"]["result"] == "pass"
    assert rep["summary"]["ready_for_labs"] is False


def test_a_failed_verdict_carries_its_evidence():
    rep = report.build(root=SD, device_id="jetson-test")
    v = rep["verdicts"]["boots_from_nvme"]
    assert v["evidence"]["value"] == "/dev/mmcblk0p1"
    assert "mmcblk" in v["detail"]


# ---------------------------------------------------------------------------
# The command-line interface, including its exit codes.
# ---------------------------------------------------------------------------


def _run_cli(tmp_path: Path, root: Path) -> tuple[int, dict | None]:
    out = tmp_path / "system_report.json"
    proc = subprocess.run(
        [sys.executable, "system_report.py", "--root", str(root),
         "--device-id", "jetson-test", "-o", str(out), "--quiet"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True, text=True,
    )
    data = json.loads(out.read_text()) if out.exists() else None
    return proc.returncode, data


def test_cli_writes_valid_json_for_a_good_machine(tmp_path):
    code, data = _run_cli(tmp_path, GOOD)
    assert data is not None, "no system_report.json was written"
    assert schema.validate(data) == []
    assert code in (0, 2)  # 2 if nvpmodel/lspci are absent off-target


def test_cli_exit_code_signals_a_failed_machine(tmp_path):
    code, data = _run_cli(tmp_path, SD)
    assert data is not None
    assert code == 1, "a machine booting from SD must exit 1, not 0"


def test_cli_output_is_json_not_a_screenshot(tmp_path):
    _, data = _run_cli(tmp_path, GOOD)
    assert isinstance(data, dict)
    assert data["device_id"] == "jetson-test"
    assert "collected_at" in data
