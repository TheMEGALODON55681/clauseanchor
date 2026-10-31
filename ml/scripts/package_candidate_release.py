"""Package the frozen candidate prototype without training or evaluation inference.

Build from the reviewed export and final evidence. Nothing is uploaded. The
portable ZIP contains runtime source, clean weights and measured limitations;
no optimizer, dataset, training cache or evaluation prediction dump is included.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
from tempfile import TemporaryDirectory
from zipfile import ZIP_STORED, ZipFile

VERSION = 'clauseanchor-candidate-prototype-v0'
ROOT = 'data/processed/cuad/candidate_release_v0'
ARTIFACT = 'models/clauseanchor_candidate_v0'
FINAL = 'data/processed/cuad/final_evaluation_v1'
MANIFEST = 'release-manifest.json'
ZIP_NAME = VERSION + '.zip'
ARTIFACT_PIN = 'ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8'
WEIGHTS_PIN = 'cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36'
FINAL_PINS = {
    'identity.json': '0de0bbd440ebc2ba3797c84e82c18dd074ba9b6a42d36f055a849bd531946a7c',
    'results/report.json': '83d670a3f90b41a5ba289112ee2465620a7617ba774689af0519ef95ed11cf6d',
    'results/official_curves.json': '02d2e7507b777137cc61a9ab9496b41b3767b4cde1218dab5e390c03acd9f769',
}
POLICY_PIN = '63141c142fee44491c3d4830229b02d5d1d73880861ce9ab2884fbad96780310'
SOURCE_FILES = (
    'LICENSE', 'ml/pyproject.toml', 'ml/requirements-inference.txt',
    'ml/scripts/package_candidate_release.py', 'ml/scripts/check_candidate_release.py',
    'docs/ml/CandidateRelease.md', 'docs/ml/CUAD_FinalEvaluation.md',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_bytes().decode('utf-8'))


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, sort_keys=True, indent=2,
                                     ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))


def file_spec(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(block)
    return {'size_bytes': Path(path).stat().st_size, 'sha256': h.hexdigest()}


def safe_name(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and name and not p.is_absolute()
            and p.as_posix() == name and all(part not in ('.', '..') for part in p.parts)
            and '\\' not in name and ':' not in name
            and all(not part.endswith((' ', '.')) for part in p.parts), 'Unsafe package path.')
    return name


def validate_manifest(manifest, digest):
    require(canonical_sha256(manifest) == digest, 'Release manifest hash differs.')
    require(manifest['version'] == VERSION and manifest['artifact_manifest_sha256'] == ARTIFACT_PIN
            and manifest['final_evidence_sha256'] == FINAL_PINS
            and manifest['core_contract_version'] == '2.0'
            and manifest['confidence'] is None and manifest['candidate_only'] is True
            and manifest['accepted_findings_enabled'] is False and manifest['absence_enabled'] is False,
            'Release identity or candidate-only policy differs.')
    names = [safe_name(n) for n in manifest['files']]
    require(MANIFEST not in names and len({n.casefold() for n in names}) == len(names),
            'Duplicate/conflicting release paths.')
    for spec in manifest['files'].values():
        require(set(spec) == {'size_bytes', 'sha256'} and type(spec['size_bytes']) is int
                and spec['size_bytes'] >= 0 and len(spec['sha256']) == 64
                and all(c in '0123456789abcdef' for c in spec['sha256']), 'Invalid file specification.')


def verify_tree(root, digest):
    root = Path(root)
    manifest = read_json(root / MANIFEST)
    validate_manifest(manifest, digest)
    entries = list(root.rglob('*'))
    require(not root.is_symlink() and not any(p.is_symlink() for p in entries), 'Linked release path.')
    actual = {p.relative_to(root).as_posix() for p in entries if p.is_file()}
    require(actual == set(manifest['files']) | {MANIFEST}, 'Release file inventory differs.')
    for name, spec in manifest['files'].items():
        require(file_spec(root / name) == spec, f'Release file damaged: {name}')
    return manifest


def verify_zip(path, digest, destination=None):
    """Check bytes before extraction; stream entries, rejecting duplicate/linked paths."""
    destination = Path(destination) if destination is not None else None
    if destination is not None:
        require(destination.is_dir() and not any(destination.iterdir()), 'Extraction destination must be empty.')
    with ZipFile(path) as archive:
        infos = archive.infolist()
        names = [safe_name(info.filename) for info in infos]
        require(len(set(names)) == len(names) == len({n.casefold() for n in names})
                and MANIFEST in names, 'Duplicate/missing ZIP entries.')
        meta = archive.getinfo(MANIFEST)
        require(meta.file_size <= 1024 * 1024, 'Oversized release manifest.')
        manifest_bytes = archive.read(meta)
        manifest = json.loads(manifest_bytes.decode('utf-8'))
        validate_manifest(manifest, digest)
        require(set(names) == set(manifest['files']) | {MANIFEST}, 'ZIP inventory differs.')
        # Validate every header before creating any member.
        for info in infos:
            require(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16)
                    and not (info.flag_bits & 1), 'Linked/directory/encrypted ZIP entry.')
            if info.filename != MANIFEST:
                require(info.file_size == manifest['files'][info.filename]['size_bytes'], 'ZIP size differs.')
        for info in infos:
            digest_bytes = hashlib.sha256()
            size = 0
            with archive.open(info) as source:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    size += len(block)
                    digest_bytes.update(block)
            if info.filename != MANIFEST:
                require({'size_bytes': size, 'sha256': digest_bytes.hexdigest()} == manifest['files'][info.filename],
                        f'ZIP payload damaged: {info.filename}')
        if destination is not None:
            for info in infos:
                target = destination / info.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
    return manifest


def source_inputs(repo):
    """Read reviewed metadata and hash files; do not load model tensors or examples."""
    repo = Path(repo)
    sys.path.insert(0, str(repo / 'ml'))
    import clauseanchor_core
    from clauseanchor_core.artifacts import CODE_FILES, verify_bundle
    require(Path(clauseanchor_core.__file__).resolve() == (repo/'ml/clauseanchor_core/__init__.py').resolve(),
            'Core import is outside this checkout.')
    artifact, _, _ = verify_bundle(repo / ARTIFACT, ARTIFACT_PIN)
    require(artifact['files']['model.safetensors']['sha256'] == WEIGHTS_PIN, 'Wrong selected weights.')
    evidence = {}
    for name, pin in FINAL_PINS.items():
        value = read_json(repo / FINAL / name)
        require(canonical_sha256(value) == pin, f'Reviewed final evidence differs: {name}')
        evidence[name] = value
    identity, report = evidence['identity.json'], evidence['results/report.json']
    require(report['identity_sha256'] == FINAL_PINS['identity.json']
            and report['official_curves_sha256'] == FINAL_PINS['results/official_curves.json']
            and report['completed_by_deadline'] is True, 'Final evidence bindings differ.')
    policy = identity['closed_policy']['candidate_policy']
    require(canonical_sha256(policy) == POLICY_PIN and policy['confidence'] is None
            and not policy['accepted_findings_enabled'] and not policy['absence_enabled'], 'Operating policy differs.')
    for name, pin in identity['code_sha256_lf'].items():
        actual = hashlib.sha256((repo/'ml/scripts'/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        require(actual == pin, f'Frozen final producer changed: {name}')
    files = {name: repo/name for name in SOURCE_FILES}
    files.update({f'ml/clauseanchor_core/{n}': repo/'ml/clauseanchor_core'/n for n in CODE_FILES})
    files.update({f'{ARTIFACT}/{n}': repo/ARTIFACT/n for n in (*artifact['files'], 'manifest.json')})
    files.update({f'evidence/{Path(n).name}': repo/FINAL/n for n in FINAL_PINS})
    require(all(p.is_file() and not p.is_symlink() for p in files.values()), 'Missing/linked release input.')
    specs = {name: file_spec(path) for name, path in sorted(files.items())}
    manifest = {'version': VERSION, 'core_contract_version': '2.0', 'artifact_manifest_sha256': ARTIFACT_PIN,
        'final_evidence_sha256': FINAL_PINS, 'candidate_only': True, 'confidence': None,
        'accepted_findings_enabled': False, 'absence_enabled': False,
        'parser_app_integration_verified': False, 'files': specs}
    return files, manifest


def build(repo):
    repo = Path(repo).resolve()
    print('Verifying frozen inference export and reviewed final evidence...', flush=True)
    files, manifest = source_inputs(repo)
    digest = canonical_sha256(manifest)
    root = repo / ROOT
    target = root / 'package'
    root.mkdir(parents=True, exist_ok=True)
    # An existing package is immutable; verify and reuse it without inference.
    if target.exists():
        receipt = read_json(target/'receipt.json')
        require(receipt['release_manifest_sha256'] == digest and receipt['version'] == VERSION,
                'Existing release inputs differ; preserve the package, do not overwrite it.')
        require(file_spec(target/ZIP_NAME) == receipt['archive'], 'Existing release archive differs.')
        verify_zip(target/ZIP_NAME, digest)
        print('Verified existing package; no rebuild or inference.', flush=True)
        return receipt
    with TemporaryDirectory(prefix='.pending-package-', dir=root) as temporary:
        stage = Path(temporary)/'package'
        stage.mkdir()
        print('Writing portable ZIP (uncompressed weights; allow about 1.5 GB free disk)...', flush=True)
        with ZipFile(stage/ZIP_NAME, 'w', compression=ZIP_STORED, allowZip64=True) as archive:
            archive.writestr(MANIFEST, (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode('utf-8'))
            for name, path in sorted(files.items()):
                archive.write(path, name)
        verify_zip(stage/ZIP_NAME, digest)
        receipt = {'version': VERSION, 'release_manifest_sha256': digest, 'archive': file_spec(stage/ZIP_NAME),
                   'artifact_manifest_sha256': ARTIFACT_PIN, 'final_identity_sha256': FINAL_PINS['identity.json'],
                   'cpu_package_check': 'pending', 'parser_app_integration_verified': False}
        write_json(stage/'receipt.json', receipt)
        require(not target.exists(), 'Another package appeared; preserve it.')
        os.rename(stage, target)
    print(f'PASS: portable package built. Release manifest SHA-256: {digest}', flush=True)
    print(f'ZIP: {target/ZIP_NAME}\nReceipt: {target/"receipt.json"}', flush=True)
    print('CPU package check still required. No upload, model change or evaluation rerun.', flush=True)
    return receipt


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[2])
