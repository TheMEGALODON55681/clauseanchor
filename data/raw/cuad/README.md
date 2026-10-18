# CUAD v1 source snapshot

This directory contains an unchanged copy of the CUAD JSON dataset,
curated by The Atticus Project, Inc.

## Attribution and license

- Dataset: Contract Understanding Atticus Dataset (CUAD).
- Publisher: https://www.atticusprojectai.org/cuad/
- License: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
- Publisher's license declaration: https://www.atticusprojectai.org/legal/
- Publisher's disclaimer: https://www.atticusprojectai.org/disclaimer/
- Research authors: Dan Hendrycks, Collin Burns, Anya Chen, and Spencer Ball.
- Research paper: https://arxiv.org/abs/2103.06268

The dataset retains its CC BY 4.0 license independently of
ClauseAnchor's software license. No endorsement by its creators is implied.

## Source identity

- Hugging Face repository: https://huggingface.co/datasets/theatticusproject/cuad
- Revision: a3c393f5d103fd0c516374e4fdff676c8176dcb1
- Upstream file: CUAD_v1/CUAD_v1.json
- Size: 40,128,638 bytes
- SHA-256: ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae
- Modifications to the dataset JSON: none.

The machine-readable source record is in source_manifest.json.

## Inspection

Checked on 2026-10-18 using ml/scripts/inspect_cuad.py:

- Documents: 510
- Paragraphs: 510
- Questions: 20,910
- Questions without answers: 14,208
- Questions with multiple answers: 2,605
- Answer spans: 13,823
- Invalid spans: 0

Every annotated answer matched its exact position in the CUAD context.
This checks text positions, not the legal correctness of annotations.