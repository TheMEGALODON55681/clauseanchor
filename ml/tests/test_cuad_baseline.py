"""Offline tests for baseline asset integrity, publication and prediction identity."""

from copy import deepcopy
import hashlib
import io
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZipFile, ZipInfo

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import read_json
from prepare_cuad_baseline import (
    CONFIG, acquire, check_archive, copy_checked, publish, validate_config,
    validate_reference_predictions, verify_file, verify_ignored_assets,
)


def spec(payload):
    return {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def predictions_fixture():
    test = {"data": [{"paragraphs": [{"qas": [{"id": "positive"}, {"id": "no-answer"}]}]}]}
    nbest = {qid: [{"text": "Contract 😀", "probability": .75, "start_logit": 3.0, "end_logit": 2.0},
                    {"text": "", "probability": .25, "start_logit": 1.0, "end_logit": .5}]
             for qid in ("positive", "no-answer")}
    top = {"positive": "Contract 😀", "no-answer": ""}
    odds = {"positive": -3.5, "no-answer": 1.25}
    return test, nbest, top, odds


class CuadBaselineTests(unittest.TestCase):
    def test_git_ignore_check_survives_windows_newlines_and_quoted_paths(self):
        real_run = subprocess.run

        def windows_text_pipe(command, **kwargs):
            # Simulate Windows text-mode stdin translation while using real Git.
            if kwargs.get("text"):
                kwargs["input"] = kwargs["input"].replace("\n", "\r\n").encode("utf-8")
                kwargs.pop("text")
            return real_run(command, **kwargs)

        with TemporaryDirectory() as folder:
            repo = Path(folder) / "repository with spaces"
            repo.mkdir()
            real_run(["git", "init", "--quiet"], cwd=repo, capture_output=True, check=True)
            (repo / ".gitignore").write_bytes(b"models/\r\ndata/\r\n")
            paths = ["models/cuad_baseline/weights.bin", "data/reference/reference file.json",
                     "data/processed/caf\u00e9.json"]
            with patch("prepare_cuad_baseline.subprocess.run", side_effect=windows_text_pipe):
                verify_ignored_assets(repo, paths)

    def test_git_ignore_check_still_rejects_unignored_and_tracked_assets(self):
        with TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(["git", "init", "--quiet"], cwd=repo, capture_output=True, check=True)
            (repo / ".gitignore").write_bytes(b"models/\n")
            for paths in (["unignored.json"], ["models/ignored.bin", "unignored.json"]):
                with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, "unignored.json"):
                    verify_ignored_assets(repo, paths)
            (repo / "models").mkdir()
            (repo / "models/tracked.bin").write_bytes(b"fixture")
            subprocess.run(["git", "add", "-f", "--", "models/tracked.bin"],
                           cwd=repo, capture_output=True, check=True)
            with self.assertRaisesRegex(ValueError, "models/tracked.bin"):
                verify_ignored_assets(repo, ["models/ignored.bin", "models/tracked.bin"])

    def test_git_failure_reports_the_actual_error(self):
        result = subprocess.CompletedProcess([], 128, b"", b"fatal: not a git repository\n")
        with patch("prepare_cuad_baseline.subprocess.run", return_value=result):
            with self.assertRaisesRegex(ValueError, "exit 128.*not a git repository"):
                verify_ignored_assets(Path("."), ["models/weights.bin"])

    def test_reference_config_keeps_original_stride_and_source(self):
        config = read_json(Path(__file__).resolve().parents[2] / CONFIG)
        validate_config(config)
        for section, key, value in (("reference_inference_settings", "doc_stride", 128),
                                     ("reference_source", "revision", "0" * 40),
                                     ("archive", "size_bytes", True)):
            with self.subTest(section=section, key=key):
                changed = deepcopy(config)
                changed[section][key] = value
                with self.assertRaises(ValueError):
                    validate_config(changed)

    def test_streamed_download_requires_exact_bytes(self):
        payload = b"downloaded checkpoint bytes"
        with TemporaryDirectory() as folder:
            target = Path(folder) / "asset.bin"
            with patch("prepare_cuad_baseline.urlopen", return_value=io.BytesIO(payload)) as opening:
                acquire("https://example.invalid/asset", target, spec(payload))
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(opening.call_args.args[0].full_url, "https://example.invalid/asset")
        for data in (payload[:-1], payload + b"extra", b"x" * len(payload)):
            with self.subTest(data=data), TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    copy_checked(io.BytesIO(data), Path(folder) / "staged.bin", spec(payload))

    def test_archive_rejects_unexpected_duplicate_link_and_wrong_size_members(self):
        def make_archive(change=None):
            buffer = io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(buffer, "w") as archive:
                    archive.writestr("roberta-base/", b"")
                    if change == "link":
                        info = ZipInfo("roberta-base/config.json")
                        info.external_attr = 0o120777 << 16
                        archive.writestr(info, b"{}")
                    else:
                        archive.writestr("roberta-base/config.json", b"{}" if change != "size" else b"{ } ")
                    if change == "duplicate":
                        archive.writestr("roberta-base/config.json", b"{}")
                    if change == "path":
                        archive.writestr("../outside.txt", b"outside")
            buffer.seek(0)
            return buffer
        with ZipFile(make_archive()) as archive:
            check_archive(archive, {"config.json": spec(b"{}")})
        for change in ("link", "size", "duplicate", "path"):
            with self.subTest(change=change), ZipFile(make_archive(change)) as archive:
                with self.assertRaises(ValueError):
                    check_archive(archive, {"config.json": spec(b"{}")})

    def test_reference_predictions_preserve_all_ids_including_no_answer(self):
        args = predictions_fixture()
        before = deepcopy(args)
        self.assertEqual(validate_reference_predictions(*args),
                         {"source_documents": 1, "questions": 2, "nbest_candidates": 4})
        self.assertEqual(args, before)
        for index in (1, 2, 3):
            for change in ("missing", "extra"):
                with self.subTest(index=index, change=change):
                    args = predictions_fixture()
                    if change == "missing":
                        args[index].pop("no-answer")
                    else:
                        args[index]["foreign"] = args[index]["positive"]
                    with self.assertRaisesRegex(ValueError, "prediction IDs"):
                        validate_reference_predictions(*args)
        args = predictions_fixture()
        args[0]["data"][0]["paragraphs"][0]["qas"].append({"id": "positive"})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_reference_predictions(*args)

    def test_invalid_prediction_values_are_rejected(self):
        for key, value in (("probability", True), ("probability", float("nan")),
                           ("probability", -1), ("probability", .2),
                           ("start_logit", float("inf")), ("text", None)):
            with self.subTest(key=key, value=value):
                args = predictions_fixture()
                args[1]["positive"][0][key] = value
                with self.assertRaises(ValueError):
                    validate_reference_predictions(*args)
        args = predictions_fixture()
        args[3]["positive"] = float("inf")
        with self.assertRaisesRegex(ValueError, "null score"):
            validate_reference_predictions(*args)

    def test_existing_corrupt_file_is_preserved(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "asset.bin"
            path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "not replaced"):
                verify_file(path, spec(b"correct"))
            self.assertEqual(path.read_bytes(), b"corrupt")
            pinned = {**spec(b"corrupt"), "published_md5": "0" * 32}
            with self.assertRaisesRegex(ValueError, "published Zenodo MD5"):
                verify_file(path, pinned)

    def test_one_conflicting_destination_prevents_all_publication(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "source-a").write_bytes(b"first")
            (root / "source-b").write_bytes(b"second")
            (root / "existing.bin").write_bytes(b"do not replace")
            staged = {"new.bin": root / "source-a", "existing.bin": root / "source-b"}
            specs = {"new.bin": spec(b"first"), "existing.bin": spec(b"second")}
            with self.assertRaises(ValueError):
                publish(root, staged, specs)
            self.assertFalse((root / "new.bin").exists())
            self.assertEqual((root / "existing.bin").read_bytes(), b"do not replace")

    def test_repeat_publication_reuses_verified_files(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "source").write_bytes(b"verified bytes")
            staged = {"output/asset.bin": root / "source"}
            specs = {"output/asset.bin": spec(b"verified bytes")}
            self.assertEqual(publish(root, staged, specs), 1)
            self.assertEqual(publish(root, staged, specs), 0)
            self.assertEqual((root / "output/asset.bin").read_bytes(), b"verified bytes")


if __name__ == "__main__":
    unittest.main()
