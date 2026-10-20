"""Test multi-pack resolution and merging functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from astrbot_plugin_meme_manager.backend.packs.resolver import (
    resolve_pack_context,
    resolve_pack_context_multi_pack,
    resolve_pack_id,
    resolve_pack_ids,
)


@pytest.fixture
def temp_packs_dir():
    """Create temporary pack directories for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create pack A
        pack_a = tmp_path / "pack_a"
        pack_a.mkdir()
        (pack_a / "category_mapping.json").write_text(
            json.dumps(
                {
                    "categories": {
                        "happy": {"name": "开心", "desc": "Happy emotes", "tags": []},
                        "sad": {"name": "难过", "desc": "Sad emotes", "tags": []},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Create pack B
        pack_b = tmp_path / "pack_b"
        pack_b.mkdir()
        (pack_b / "category_mapping.json").write_text(
            json.dumps(
                {
                    "categories": {
                        "happy": {"name": "快乐", "desc": "Joyful emotes", "tags": []},
                        "angry": {"name": "生气", "desc": "Angry emotes", "tags": []},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Create selection rules
        rules_file = tmp_path / "selection_rules.json"
        rules_file.write_text(
            json.dumps(
                {
                    "default_pack_id": "pack_a",
                    "session_mappings": {},
                    "persona_mappings": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        yield {
            "packs_root": tmp_path,
            "pack_a": pack_a,
            "pack_b": pack_b,
            "rules_file": rules_file,
        }


def test_resolve_single_pack_id(temp_packs_dir):
    """Test backward compatibility: resolve_pack_id returns single pack."""
    rules = temp_packs_dir["rules_file"]
    pack_id = resolve_pack_id(rules)
    assert pack_id == "pack_a"


def test_resolve_multiple_pack_ids(temp_packs_dir):
    """Test multi-pack resolution with pack_ids in rules."""
    rules_file = temp_packs_dir["rules_file"]
    rules_data = json.loads(rules_file.read_text(encoding="utf-8"))
    rules_data["default_pack_ids"] = ["pack_a", "pack_b"]
    rules_file.write_text(json.dumps(rules_data, ensure_ascii=False), encoding="utf-8")

    pack_ids = resolve_pack_ids(rules_file)
    assert pack_ids == ["pack_a", "pack_b"]


def test_resolve_pack_ids_fallback_to_single(temp_packs_dir):
    """Test pack_ids falls back to pack_id when pack_ids not present."""
    rules = temp_packs_dir["rules_file"]
    pack_ids = resolve_pack_ids(rules)
    # Should fallback to default_pack_id
    assert pack_ids == ["pack_a"]


def test_multi_pack_context_merging(temp_packs_dir):
    """Test category merging from multiple packs."""
    packs_root = temp_packs_dir["packs_root"]
    pack_ids = ["pack_a", "pack_b"]

    context = resolve_pack_context_multi_pack(pack_ids, packs_root)

    assert context["pack_ids"] == ["pack_a", "pack_b"]
    assert "category_mapping" in context

    # Check merged categories
    categories = context["category_mapping"]["categories"]
    assert "happy" in categories
    assert "sad" in categories
    assert "angry" in categories

    # pack_a's happy should be first (priority)
    assert categories["happy"]["name"] == "开心"
    assert categories["happy"]["desc"] == "Happy emotes"


def test_resolve_pack_context_compatibility(temp_packs_dir):
    """Test that resolve_pack_context maintains backward compatibility."""
    rules = temp_packs_dir["rules_file"]
    packs_root = temp_packs_dir["packs_root"]

    context = resolve_pack_context(rules, packs_root)

    # Should have both pack_id (single) and pack_ids (list)
    assert "pack_id" in context
    assert "pack_ids" in context
    assert context["pack_id"] == "pack_a"
    assert context["pack_ids"] == ["pack_a"]


def test_multi_pack_context_with_multi_ids(temp_packs_dir):
    """Test resolve_pack_context when rules contain pack_ids."""
    rules_file = temp_packs_dir["rules_file"]
    packs_root = temp_packs_dir["packs_root"]

    # Update rules to use pack_ids
    rules_data = json.loads(rules_file.read_text(encoding="utf-8"))
    rules_data["default_pack_ids"] = ["pack_a", "pack_b"]
    rules_file.write_text(json.dumps(rules_data, ensure_ascii=False), encoding="utf-8")

    context = resolve_pack_context(rules_file, packs_root)

    assert context["pack_ids"] == ["pack_a", "pack_b"]
    # pack_id should be the first pack for compatibility
    assert context["pack_id"] == "pack_a"

    # Categories should be merged
    categories = context["category_mapping"]["categories"]
    assert len(categories) == 3  # happy, sad, angry
