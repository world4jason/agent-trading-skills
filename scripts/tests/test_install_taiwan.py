import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("tw_install", Path(__file__).resolve().parents[1]/"install_taiwan.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_install_backup_and_unrelated_skill(tmp_path):
    dest=tmp_path/"skills"
    dest.mkdir()
    (dest/"unrelated").mkdir()
    (dest/"vcp-screener").symlink_to("/old/source")
    result=module.install(dest)
    assert result["installed"] == 67
    assert (dest/"vcp-screener").resolve() == module.ROOT/"skills/vcp-screener"
    assert (dest/"unrelated").is_dir()
    assert json.loads(Path(result["backup"]).read_text())["previous"]["vcp-screener"] == "/old/source"


def test_conflict_prevents_partial_install(tmp_path):
    dest=tmp_path/"skills"
    (dest/"vcp-screener").mkdir(parents=True)
    with pytest.raises(ValueError): module.install(dest)
    assert list(dest.iterdir()) == [dest/"vcp-screener"]


def test_keyboard_interrupt_restores_prior_links(tmp_path, monkeypatch):
    destination=tmp_path/"skills"
    destination.mkdir()
    (destination/"backtest-expert").symlink_to("/previous/backtest")
    original=module.os.replace
    calls=[]
    def interrupted(source,target):
        calls.append(target)
        if len(calls)==2:
            raise KeyboardInterrupt()
        return original(source,target)
    monkeypatch.setattr(module.os,"replace",interrupted)
    with pytest.raises(KeyboardInterrupt):
        module.install(destination)
    assert module.os.readlink(destination/"backtest-expert") == "/previous/backtest"
    assert len(list(destination.iterdir())) == 1
