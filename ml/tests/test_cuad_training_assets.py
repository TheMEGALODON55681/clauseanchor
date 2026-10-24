"""Guard the base checkpoint identity and code-point/overlap tokenizer checks."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import read_json
from prepare_cuad_training_assets import (
    CONFIG, validate_config, validate_model_metadata, validate_tensor_shapes, validate_window_maps,
)


def window(indices):
    ids, offsets, sequences = [0, 20, 2, 2], [(0, 0), (0, 1), (0, 0), (0, 0)], [None, 0, None, None]
    for index in indices:
        ids.append(100 + index)
        offsets.append((index, index + 1))
        sequences.append(1)
    missing = 512 - len(ids)
    return ids + [1] * missing, offsets + [(0, 0)] * missing, sequences + [None] * missing


def check(windows, context, overlap=128):
    return validate_window_maps([w[0] for w in windows], [w[1] for w in windows],
                                [w[2] for w in windows], context, overlap)


class CuadTrainingAssetTests(unittest.TestCase):
    def test_source_pin_rejects_changed_backbone_files_and_overlap(self):
        config = read_json(Path(__file__).resolve().parents[2] / CONFIG)
        validate_config(config)
        changes = []
        for field, value in (("repo_id", "other/model"), ("revision", "0" * 40), ("source_version", True)):
            changed = deepcopy(config)
            changed[field] = value
            changes.append(changed)
        changed = deepcopy(config)
        changed["files"]["model.safetensors"]["sha256"] = "0" * 64
        changes.append(changed)
        changed = deepcopy(config)
        changed["feature_defaults"]["context_token_overlap"] = 256
        changes.append(changed)
        for changed in changes:
            with self.assertRaisesRegex(ValueError, "source or feature defaults changed"):
                validate_config(changed)

    def test_metadata_rejects_a_qa_checkpoint(self):
        config = {"architectures": ["RobertaForMaskedLM"], "model_type": "roberta", "hidden_size": 768,
                  "num_hidden_layers": 12, "num_attention_heads": 12, "vocab_size": 50265,
                  "max_position_embeddings": 514, "bos_token_id": 0, "eos_token_id": 2, "pad_token_id": 1}
        validate_model_metadata(config)
        config["architectures"] = ["RobertaForQuestionAnswering"]
        with self.assertRaisesRegex(ValueError, "architecture"):
            validate_model_metadata(config)

    def test_tensor_inventory_rejects_task_heads_missing_layers_and_wrong_shapes(self):
        shapes = {"roberta.embeddings.word_embeddings.weight": [50265, 768],
                  "roberta.embeddings.position_embeddings.weight": [514, 768], "lm_head.dense.weight": [768, 768]}
        shapes.update({f"roberta.encoder.layer.{i}.attention.self.query.weight": [768, 768] for i in range(12)})
        validate_tensor_shapes(shapes)
        for change in ("head", "layer", "shape"):
            changed = deepcopy(shapes)
            if change == "head":
                changed["qa_outputs.weight"] = [2, 768]
            elif change == "layer":
                del changed["roberta.encoder.layer.11.attention.self.query.weight"]
            else:
                changed["roberta.embeddings.word_embeddings.weight"] = [50265, 1024]
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_tensor_shapes(changed)

    def test_code_point_offsets_allow_repeated_tokens_for_one_unicode_character(self):
        w = window([0, 0])
        rows = check([w], "₹")
        self.assertEqual(rows[0], [(100, 0, 1), (100, 0, 1)])

    def test_utf8_byte_offsets_cannot_replace_code_point_offsets(self):
        w = window([0])
        w[1][4] = (0, 3)
        with self.assertRaisesRegex(ValueError, "code-point"):
            check([w], "₹")

    def test_missing_non_whitespace_fails_but_trimmed_whitespace_is_allowed(self):
        check([window([0, 2])], "a b")
        with self.assertRaisesRegex(ValueError, "lost source characters"):
            check([window([0, 2])], "abc")

    def test_overlap_requires_identical_tokens_and_source_offsets(self):
        windows = [window(range(7)), window(range(5, 10))]
        check(windows, "abcdefghij", overlap=2)
        windows[1][1][4] = (4, 5)
        with self.assertRaisesRegex(ValueError, "overlap"):
            check(windows, "abcdefghij", overlap=2)

    def test_special_token_offsets_and_window_lengths_are_validated(self):
        w = window([0])
        w[1][0] = (0, 1)
        with self.assertRaisesRegex(ValueError, "Special/padding"):
            check([w], "a")
        w = window([0])
        w[0].pop()
        with self.assertRaisesRegex(ValueError, "512-token"):
            check([w], "a")


if __name__ == "__main__":
    unittest.main()
