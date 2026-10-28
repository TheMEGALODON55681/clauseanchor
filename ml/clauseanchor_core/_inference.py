"""Inference-only copies of frozen producer logic; parity tests pin behavior.

FeatureTokenizer/window_count: prepare_cuad_features.py.
window_candidates: cuad_development.py. exact_candidates: validate_cuad_decoder.py.
No producer file is modified; no annotation/evaluation imports at deployment.
"""

from copy import deepcopy
import math
import numpy as np
from .artifacts import require

def window_count(tokens, question_tokens):
    capacity = 512 - question_tokens - 4
    require(tokens > 0 and 0 < question_tokens <= 64, "Empty context or invalid question budget.")
    return 1 + max(0, math.ceil((tokens - capacity) / (capacity - 128)))


class FeatureTokenizer:
    def __init__(self, directory):
        from tokenizers import Tokenizer
        from transformers import RobertaTokenizerFast
        self.tokenizer = RobertaTokenizerFast.from_pretrained(
            str(directory), local_files_only=True, add_prefix_space=False, trim_offsets=True)
        self.backend = self.tokenizer.backend_tokenizer
        self.backend.no_padding()
        self.backend.no_truncation()
        # Apply the postprocessor ONCE after truncation to avoid double-trimming
        # RoBERTa's whitespace offsets. Preserve global source coordinates.
        self.raw = Tokenizer.from_str(self.backend.to_str())
        self.raw.post_processor = None
        self.raw.no_padding()
        self.raw.no_truncation()
        self.questions = {}

    def question(self, text):
        if text not in self.questions:
            encoding = self.raw.encode(text, add_special_tokens=False)
            original = len(encoding.ids)
            require(original > 0, "Empty question tokens.")
            encoding.truncate(64)
            self.questions[text] = (encoding, original)
        return self.questions[text]

    def context(self, text):
        raw = self.raw.encode(text, add_special_tokens=False)
        require(len(raw.ids) > 0, "Empty context.")
        offsets = self.backend.post_process(raw, add_special_tokens=False).offsets
        covered = bytearray(len(text))
        for start, end in offsets:
            require(0 <= start <= end <= len(text), "Context offsets are not source code points.")
            covered[start:end] = b"\1" * (end - start)
        require(all(covered[i] or c.isspace() for i, c in enumerate(text)), "Tokenizer lost source characters.")
        return raw, offsets

    def windows(self, raw_context, full_offsets, question):
        query, _ = self.question(question)
        query_ids, source_ids = query.ids, raw_context.ids
        capacity = 512 - len(query_ids) - 4
        context = deepcopy(raw_context)
        context.truncate(capacity, stride=128)
        rows = [context, *context.overflowing]
        require(len(rows) == window_count(len(source_ids), len(query_ids)), "Wrong overflow count.")
        for index, part in enumerate(rows):
            start = index * (capacity - 128)
            encoding = self.backend.post_process(query, part, add_special_tokens=True)
            encoding.pad(512, pad_id=1, pad_token="<pad>")
            ids, offsets, sequences = encoding.ids, encoding.offsets, encoding.sequence_ids
            positions = [i for i, s in enumerate(sequences) if s == 1]
            require(len(ids) == 512 and ids[0] == 0 and len(positions) == len(part.ids), "Unexpected pair layout or null token.")
            require([ids[i] for i in positions] == source_ids[start:start + len(positions)]
                    and [offsets[i] for i in positions] == full_offsets[start:start + len(positions)],
                    "Overflow lost context token identity or source offsets.")
            require([ids[i] for i, s in enumerate(sequences) if s == 0] == query_ids,
                    "Question truncation differs from the first 64 tokens.")
            yield start, encoding, positions


def window_candidates(start, end, sequences, offsets, context, row, clipped_left, clipped_right):
    require(start.shape == end.shape == sequences.shape and offsets.shape == (len(start), 2)
            and np.isfinite(start).all() and np.isfinite(end).all(), "Invalid decoder logits or maps.")
    positions = np.flatnonzero(sequences == 1)
    require(len(positions) > 0, "Window has no context tokens.")
    spans = offsets[positions]
    require(((spans[:, 0] >= 0) & (spans[:, 0] <= spans[:, 1]) & (spans[:, 1] <= len(context))).all(),
            "Context offset outside source text.")
    valid = positions[spans[:, 0] < spans[:, 1]]
    require(len(valid) > 0, "No nonempty context token.")
    # Score ties resolve by lower token index, independent of sort implementation.
    starts = valid[np.lexsort((valid, -start[valid]))[:20]]
    ends = valid[np.lexsort((valid, -end[valid]))[:20]]
    null = float(start[0]) + float(end[0])
    candidates = []
    for s in starts:
        for e in ends:
            if not s <= e < s + 256:
                continue
            left, right = int(offsets[s, 0]), int(offsets[e, 1])
            require(0 <= left < right <= len(context), "Invalid decoded source interval.")
            candidates.append({"start": left, "end": right, "text": context[left:right],
                               "margin": float(start[s]) + float(end[e]) - null,
                               "window_row": int(row), "start_token": int(s), "end_token": int(e),
                               "null_score": null,
                               "boundary_review": bool((clipped_left and s == valid[0])
                                                       or (clipped_right and e == valid[-1]))})
    return sorted(candidates, key=lambda c: (-c["margin"], c["start"], c["end"], c["start_token"], c["end_token"]))[:20]


def exact_candidates(raw):
    """Preserve original exact-dedup semantics without its overlap suppression."""
    complete = {(c["start"], c["end"]) for c in raw if not c["boundary_review"]}
    ordered = sorted(raw, key=lambda c: (-c["margin"], c["boundary_review"], c["start"], c["end"], c["window_row"]))
    result = {}
    for c in ordered:
        key = c["start"], c["end"]
        if key not in result:
            result[key] = {**c, "boundary_review": key not in complete}
    return list(result.values())



def disjoint_candidates(raw):
    # Same stable order and overlap test as select_candidates(..., "disjoint").
    kept = []
    for c in sorted((c for c in exact_candidates(raw) if c["margin"] > 0),
                    key=lambda c: -c["margin"]):
        if not any(min(c["end"], p["end"]) > max(c["start"], p["start"]) for p in kept):
            kept.append(c)
    return kept


class TorchBackend:
    def __init__(self, root, device):
        import torch
        from safetensors.torch import load_file
        from transformers import RobertaConfig, RobertaForQuestionAnswering
        self.device = torch.device(device)
        require(device in ("cpu", "cuda"), "Use device=cpu or cuda.")
        require(device != "cuda" or torch.cuda.is_available(), "CUDA is unavailable; request CPU explicitly.")
        config = RobertaConfig.from_json_file(str(root / "config.json"))
        require(config.model_type == "roberta" and config.num_labels == 2, "Expected a RoBERTa QA config.")
        config._attn_implementation = "sdpa"
        self.model = RobertaForQuestionAnswering(config)
        state = load_file(str(root / "model.safetensors"), device="cpu")
        self.model.load_state_dict(state, strict=True)
        del state
        require(all(torch.isfinite(p).all().item() for p in self.model.parameters()), "Nonfinite model weights.")
        self.model.requires_grad_(False).to(self.device).eval()

    def predict(self, encodings):
        import torch
        ids = torch.tensor([e.ids for e in encodings], dtype=torch.long, device=self.device)
        mask = torch.tensor([e.attention_mask for e in encodings], dtype=torch.long, device=self.device)
        with torch.inference_mode(), torch.autocast(device_type=self.device.type,
                dtype=torch.float16, enabled=self.device.type == "cuda"):
            output = self.model(input_ids=ids, attention_mask=mask)
        return output.start_logits.float().cpu().numpy(), output.end_logits.float().cpu().numpy()
