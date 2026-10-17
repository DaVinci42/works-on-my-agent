import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import list_models as catalog


def fixture() -> dict[str, object]:
    return {
        "id": "fixture",
        "model_picker_enabled": True,
        "model_picker_category": "lightweight",
        "policy": {"state": "enabled"},
        "capabilities": {
            "type": "chat",
            "supports": {"tool_calls": True, "reasoning_effort": ["low"]},
        },
    }


class DiscoveryTests(unittest.TestCase):
    def test_dynamic_metadata(self):
        models = catalog.discover({"data": [fixture()]}, {"copilot/fixture"})
        self.assertEqual(models[0]["model"], "copilot/fixture")
        self.assertEqual(models[0]["reasoning_effort"], ["low"])
        malformed = fixture() | {
            "capabilities": {
                "type": "chat",
                "supports": {
                    "tool_calls": True,
                    "reasoning_effort": ["low", 1, "", None],
                },
            }
        }
        self.assertEqual(
            catalog.discover({"data": [malformed]}, {"copilot/fixture"})[0][
                "reasoning_effort"
            ],
            ["low"],
        )
        non_list = fixture() | {
            "capabilities": {
                "type": "chat",
                "supports": {"tool_calls": True, "reasoning_effort": True},
            }
        }
        self.assertEqual(
            catalog.discover({"data": [non_list]}, {"copilot/fixture"})[0][
                "reasoning_effort"
            ],
            [],
        )
        self.assertEqual(catalog.discover({"data": [fixture()]}, set()), [])

    def test_category_order(self):
        categories = ["powerful", "unknown", "versatile", "lightweight"]
        records = [
            fixture() | {"id": category, "model_picker_category": category}
            for category in categories
        ]
        models = catalog.discover(
            {"data": records}, {"copilot/" + category for category in categories}
        )
        self.assertEqual(
            [model["category"] for model in models],
            ["lightweight", "versatile", "powerful", "unknown"],
        )

    def test_ineligible_models(self):
        overrides: list[dict[str, object]] = [
            {"model_picker_enabled": False},
            {"policy": {"state": "disabled"}},
            {"capabilities": {"type": "embedding"}},
            {"capabilities": {"type": "chat", "supports": {"tool_calls": False}}},
        ]
        for override in overrides:
            self.assertEqual(
                catalog.discover({"data": [fixture() | override]}, {"copilot/fixture"}),
                [],
            )
        with self.assertRaises(TypeError):
            _ = catalog.discover({}, set())

    def test_fetch_uses_cli_header_without_exposing_token(self):
        payload = json.dumps({"data": [fixture()]}).encode()
        with (
            patch.object(
                catalog, "command", side_effect=["fixture-secret", "copilot/fixture"]
            ),
            patch(
                "urllib.request.urlopen", return_value=io.BytesIO(payload)
            ) as opening,
        ):
            self.assertEqual(len(catalog.fetch(1)), 1)
            opening.assert_called_once()

    def test_delegation_template_syntax_and_arguments(self):
        text = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text()
        snippet = text.split("```bash\n", 1)[1].split("```", 1)[0]
        result = subprocess.run(
            ["bash", "-n"], input=snippet, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CRUSH_DELEGATE_WORKER=1 crush run", snippet)
        self.assertNotIn("--yolo", snippet)
        self.assertIn('--small-model "$WORKER_MODEL"', snippet)

    def test_cli_filter_and_safe_error(self):
        with (
            patch.object(sys, "argv", ["list_models", "--category", "lightweight"]),
            patch.object(
                catalog,
                "cached_models",
                return_value=(
                    [{"model": "copilot/fixture", "category": "lightweight"}],
                    "fresh",
                ),
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(catalog.main(), 0)
            self.assertIn("copilot/fixture", output.getvalue())
        failure = subprocess.CalledProcessError(1, ["gh"], stderr="fixture-secret")
        with (
            patch.object(sys, "argv", ["list_models"]),
            patch.object(catalog, "cached_models", side_effect=failure),
            contextlib.redirect_stderr(io.StringIO()) as error,
        ):
            self.assertEqual(catalog.main(), 1)
            self.assertIn("CalledProcessError (gh)", error.getvalue())
            self.assertNotIn("fixture-secret", error.getvalue())


class CacheTests(unittest.TestCase):
    def test_cache_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            with (
                patch.object(
                    catalog, "fetch", return_value=[{"model": "copilot/fixture"}]
                ) as fetch,
                patch("time.time", return_value=1000),
            ):
                self.assertEqual(catalog.cached_models(path, False, 1)[1], "refreshed")
                self.assertEqual(catalog.cached_models(path, False, 1)[1], "fresh")
                fetch.assert_called_once()
                self.assertEqual(catalog.cached_models(path, True, 1)[1], "refreshed")
                self.assertEqual(fetch.call_count, 2)
            with (
                patch.object(catalog, "fetch", side_effect=OSError("offline")),
                patch("time.time", return_value=1000 + catalog.TTL),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(catalog.cached_models(path, False, 1)[1], "stale")
                with self.assertRaises(OSError):
                    _ = catalog.cached_models(path, True, 1)
            with (
                patch.object(catalog, "fetch", side_effect=OSError("offline")),
                patch("time.time", return_value=1001 + catalog.MAX_STALE),
                self.assertRaises(OSError),
            ):
                _ = catalog.cached_models(path, False, 1)
            self.assertNotIn("token", path.read_text())

    def test_empty_and_corrupt_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            _ = path.write_text("broken")
            with patch.object(catalog, "fetch", return_value=[]) as fetch:
                self.assertEqual(
                    catalog.cached_models(path, False, 1), ([], "refreshed")
                )
                self.assertEqual(catalog.cached_models(path, False, 1), ([], "fresh"))
                fetch.assert_called_once()
            self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_fresh_hit_never_runs_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "crush-copilot-delegate" / "models.json"
            path.parent.mkdir()
            _ = path.write_text(
                json.dumps(
                    {
                        "fetched_at": 1000,
                        "models": [
                            {"model": "copilot/fixture", "category": "lightweight"}
                        ],
                    }
                )
            )
            with (
                patch.dict(os.environ, {"XDG_CACHE_HOME": folder}),
                patch.object(sys, "argv", ["list_models"]),
                patch("time.time", return_value=1001),
                patch.object(
                    catalog,
                    "command",
                    side_effect=AssertionError("Unexpected subprocess"),
                ),
                patch.object(
                    catalog, "fetch", side_effect=AssertionError("Unexpected network")
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(catalog.main(), 0)


if __name__ == "__main__":
    _ = unittest.main()
