"""Frozen deployment analyzer and a separate benchmark-only reference path.

Reference __call__ is the unchanged baseline engine; only initialization loads
clean safetensors. No released checkpoint weights or optimizer are loaded.
"""
import gc
import importlib.util
import time

from clauseanchor_core import CandidateOnlyAnalyzer, AnalysisContext, to_dict
from clauseanchor_core.artifacts import require
from run_cuad_baseline import InferenceEngine, cache_tokenizer
from cuad_final_evaluation import inference_input


class CandidateEngine:
    def __init__(self,artifact,artifact_sha,device):
        self.analyzer=CandidateOnlyAnalyzer(artifact,expected_manifest_sha256=artifact_sha,
                                           device=device,batch_size=1,max_windows_per_category=None)

    def __call__(self,task):
        last=time.monotonic()
        def progress(event):
            nonlocal last
            if time.monotonic()-last>=15:
                print(f'  analyzer windows {event.completed_units}/{event.total_units}',flush=True)
                last=time.monotonic()
        return to_dict(self.analyzer.analyze(task['context'],doc_id=task['doc_id'],
            text_sha256=task['source_sha256'],category_ids=(task['category_id'],),
            context=AnalysisContext(),progress=progress))


class OfficialEngine(InferenceEngine):
    def __init__(self,artifact,tokenizer_root,decoder_path,device):
        import torch
        from safetensors.torch import load_file
        from transformers import RobertaConfig, RobertaForQuestionAnswering, RobertaTokenizer
        self.torch,self.device=torch,device
        self.tokenizer=RobertaTokenizer.from_pretrained(str(tokenizer_root),local_files_only=True,
                                                       do_lower_case=False,add_prefix_space=False)
        require(not self.tokenizer.is_fast and self.tokenizer.pad_token_id==1
                and self.tokenizer.cls_token_id==0,'Reference slow tokenizer differs.')
        cache_tokenizer(self.tokenizer)
        config=RobertaConfig.from_json_file(str(artifact/'config.json'))
        require(config.model_type=='roberta' and config.num_labels==2,'Clean QA config differs.')
        config._attn_implementation='eager'
        self.model=RobertaForQuestionAnswering(config)
        state=load_file(str(artifact/'model.safetensors'),device='cpu')
        self.model.load_state_dict(state,strict=True); del state
        require(all(torch.isfinite(p).all().item() for p in self.model.parameters()),'Nonfinite clean weights.')
        self.model.requires_grad_(False).to(device=device,dtype=torch.float32).eval()
        spec=importlib.util.spec_from_file_location('_cuad_final_pinned_decoder',decoder_path)
        self.decoder=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.decoder)

    def __call__(self,task):
        return super().__call__(inference_input(task))


def configure_arm(arm):
    import torch
    torch.use_deterministic_algorithms(arm=='official')
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False
    torch.manual_seed(20261029)


def release_engine(engine):
    # Break GPU ownership before constructing the other arm on a 4 GB device.
    if hasattr(engine,'analyzer'): del engine.analyzer
    if hasattr(engine,'model'): del engine.model
    gc.collect()
    import torch
    if torch.cuda.is_available(): torch.cuda.empty_cache()
