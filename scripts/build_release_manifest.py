"""Build a hash-bound manifest for an immutable Git release candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "cat-file", "blob", f"{commit}:{path}"])


def _tracked_paths(commit: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", commit], text=True
    )
    return output.splitlines()


def build_manifest(root: Path, commit: str, release_tag: str, release_dir: str) -> Path:
    target = root / release_dir / "release_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for relative_path in _tracked_paths(commit):
        data = _git_bytes(commit, relative_path)
        files.append(
            {
                "relative_path": relative_path,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    exclusions = [
        "data/raw/r4_candidate_pmc10257194",
        "data/raw/r4_candidate_pmc13212878",
        "reports/review_round_4/pmc10257194_paper_ood",
        "reports/review_round_4/pmc10257194_paper_source_audit",
        "reports/review_round_4/manchester_nanoomic_source",
        "reports/review_round_4/manchester_nanoomic_ood",
        "reports/review_round_4/t214_source_heterogeneity",
        "reports/review_round_4/t217_statistical_amendment",
    ]
    manifest = {
        "schema_version": 1,
        "release_id": f"bioif-empirical-candidate-{release_tag}",
        "status": "CANDIDATE_NOT_DOI_ARCHIVED",
        "intended_git_tag": release_tag,
        "source_commit": commit,
        "source_commit_resolution": (
            f"git rev-parse '{release_tag}^{{}}' "
            "(source/provenance commit before release-metadata commit)"
        ),
        "doi_status": "PENDING_NOT_ARCHIVED",
        "scientific_submission_ready": False,
        "manifest_self_hash_excluded": True,
        "license_boundary": {
            "software": "Apache-2.0",
            "redistributable_data": "Only source-registry-approved tracked assets are included",
            "analysis_only_exclusions": exclusions,
            "claim_boundary": (
                "No independent evaluator, no-author reproduction, external adoption, "
                "DOI archive or scientific submission readiness is claimed."
            ),
        },
        "files": files,
    }
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-dir", required=True)
    args = parser.parse_args()
    target = build_manifest(
        Path.cwd(),
        args.commit,
        args.release_tag,
        args.release_dir,
    )
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"{target} files={len(json.loads(target.read_text(encoding='utf-8'))['files'])} sha256={digest}")


if __name__ == "__main__":
    main()
