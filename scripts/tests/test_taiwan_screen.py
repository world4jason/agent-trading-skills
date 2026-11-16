import json
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import taiwan_screen as engine
import taiwan_technical

LISTINGS = [{"stock_id": "2330", "symbol": "2330.TW", "kind": "stock", "exchange": "twse"},
            {"stock_id": "6488", "symbol": "6488.TWO", "kind": "stock", "exchange": "tpex"},
            {"stock_id": "0050", "symbol": "0050.TW", "kind": "etf", "exchange": "twse"}]


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(engine.data, "universe", lambda: {"status":"ok","data":LISTINGS,"warnings":[]})
    monkeypatch.setattr(engine.data, "dataset", lambda *a, **k: {"status":"ok","data":[{"date":"2024-01-05"}]})
    def prices(symbol, *a, **k):
        return {"status":"ok","data":[{"date":"2024-01-05"}],"source":"finmind","as_of":"2024-01-05","warnings":[]}
    monkeypatch.setattr(engine.data, "prices", prices)
    monkeypatch.setattr(taiwan_technical, "evaluate", lambda *a, **k: {"status":"evaluated","passed":False,"metrics":{},"warnings":[]})


def run(**kwargs):
    return engine.screen(strategies=["momentum-burst"], start="2023-01-01", end="2024-01-07", **kwargs)


def test_twse_tpex_etf_and_explicit_subset(providers):
    report = run()
    assert report["scope"]["processed_symbols"] == 3
    assert {r["symbol"] for r in report["results"]} == {"2330.TW","6488.TWO","0050.TW"}
    assert report["expected_session"] == "2024-01-05"
    assert run(limit=1)["scope"]["not_processed_symbols"] == 2
    assert run(exchange="tpex")["results"][0]["symbol"] == "6488.TWO"
    assert run(kind="etf")["results"][0]["symbol"] == "0050.TW"


def test_stale_data_never_counts_as_negative_or_pass(providers, monkeypatch):
    monkeypatch.setattr(engine.data,"prices",lambda *a,**k: {"status":"ok","data":[{"date":"2023-12-31"}],"source":"finmind","as_of":"2023-12-31","warnings":[]})
    report=run()
    assert report["status"] == "insufficient_data"
    assert all(r["passed"] is None for r in report["results"])


def test_wrong_suffix_and_invalid_scope_fail(providers):
    with pytest.raises(engine.data.DataError): run(symbols=["6488.TW"])
    with pytest.raises(engine.data.DataError): run(limit=0)


def test_cli_writes_failure_json(tmp_path):
    dest = tmp_path / "new" / "result.json"
    code = engine.main(["--strategy","vcp","--symbols","2330","--start","2024-02-01",
                        "--end","2024-01-01","--output",str(dest)])
    assert code == 1
    assert json.loads(dest.read_text())["status"] == "error"


def test_all_old_entrypoints_use_taiwan_cli():
    root=Path(__file__).resolve().parents[2]
    for relative in json.loads((root/"TAIWAN_ENGINE_MAP.json").read_text()):
        process=subprocess.run([sys.executable,str(root/"skills"/relative),"--help"],capture_output=True,text=True)
        assert process.returncode == 0, process.stderr
        assert "--exchange" in process.stdout
        assert "--api-key" not in process.stdout
