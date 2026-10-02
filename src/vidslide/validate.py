"""State validation for VidSlide run directories.

Verifies the integrity of manifest.json, assets, events.jsonl, and their consistency.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json

from vidslide.run import Run
from vidslide.protocol import RunState


class ValidationIssue:
    """Represents a validation issue."""

    SEVERITY_ERROR = "error"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"

    def __init__(
        self,
        severity: str,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.severity = severity
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class RunValidator:
    """Validates VidSlide run directory integrity."""

    def __init__(self, run_dir: Path):
        """Initialize validator.

        Args:
            run_dir: Path to run directory
        """
        self.run_dir = Path(run_dir)
        self.issues: List[ValidationIssue] = []

    def validate(self) -> Dict[str, Any]:
        """Run all validation checks.

        Returns:
            Validation report dictionary
        """
        self.issues = []

        # Check directory exists
        if not self.run_dir.exists():
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_ERROR,
                    "RUN_DIR_NOT_FOUND",
                    f"Run directory does not exist: {self.run_dir}",
                )
            )
            return self._build_report(passed=False)

        if not self.run_dir.is_dir():
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_ERROR,
                    "RUN_DIR_NOT_DIRECTORY",
                    f"Path is not a directory: {self.run_dir}",
                )
            )
            return self._build_report(passed=False)

        # Load run
        try:
            run = Run(self.run_dir)
            if not run.is_valid():
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_ERROR,
                        "RUN_INVALID",
                        "Run directory is not valid (missing manifest.json)",
                    )
                )
                return self._build_report(passed=False)
        except Exception as e:
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_ERROR,
                    "RUN_LOAD_FAILED",
                    f"Failed to load run: {e}",
                )
            )
            return self._build_report(passed=False)

        # Run checks
        self._check_manifest_integrity(run)
        self._check_assets_exist(run)
        self._check_sequence_validity(run)
        self._check_events_integrity(run)
        self._check_orphaned_assets(run)

        # Determine overall status
        has_errors = any(
            issue.severity == ValidationIssue.SEVERITY_ERROR for issue in self.issues
        )
        return self._build_report(passed=not has_errors)

    def _check_manifest_integrity(self, run: Run) -> None:
        """Check manifest.json integrity."""
        try:
            manifest = run.manifest

            # Check required fields
            required_fields = ["schema_version", "run_id", "state", "assets"]
            for field in required_fields:
                if field not in manifest.data:
                    self.issues.append(
                        ValidationIssue(
                            ValidationIssue.SEVERITY_ERROR,
                            "MANIFEST_MISSING_FIELD",
                            f"Manifest missing required field: {field}",
                        )
                    )

            # Check ULID format for run_id
            run_id = manifest.data.get("run_id", "")
            if not run_id.startswith("run_"):
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_ERROR,
                        "INVALID_RUN_ID",
                        f"Invalid run_id format: {run_id}",
                    )
                )

            # Check state validity
            state_str = manifest.data.get("state", "")
            try:
                RunState(state_str)
            except ValueError:
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_ERROR,
                        "INVALID_STATE",
                        f"Invalid state: {state_str}",
                    )
                )

            # Check asset ULID format
            assets = manifest.data.get("assets", {})
            for asset_id in assets.keys():
                if not asset_id.startswith("a_"):
                    self.issues.append(
                        ValidationIssue(
                            ValidationIssue.SEVERITY_WARNING,
                            "INVALID_ASSET_ID",
                            f"Asset ID does not follow convention: {asset_id}",
                        )
                    )

        except Exception as e:
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_ERROR,
                    "MANIFEST_CHECK_FAILED",
                    f"Failed to check manifest: {e}",
                )
            )

    def _check_assets_exist(self, run: Run) -> None:
        """Check that all referenced assets exist."""
        assets = run.manifest.data.get("assets", {})
        assets_dir = run.assets_dir

        for asset_id, asset_data in assets.items():
            asset_path = asset_data.get("path", "")
            full_path = assets_dir / asset_path

            if not full_path.exists():
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_ERROR,
                        "ASSET_MISSING",
                        f"Asset file missing: {asset_path}",
                        {"asset_id": asset_id, "path": str(full_path)},
                    )
                )
            elif not full_path.is_file():
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_ERROR,
                        "ASSET_NOT_FILE",
                        f"Asset path is not a file: {asset_path}",
                        {"asset_id": asset_id},
                    )
                )

    def _check_sequence_validity(self, run: Run) -> None:
        """Check that sequence references valid assets."""
        sequence = run.manifest.data.get("sequence", [])
        assets = run.manifest.data.get("assets", {})

        for i, asset_id in enumerate(sequence):
            if asset_id not in assets:
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_ERROR,
                        "SEQUENCE_INVALID_REF",
                        f"Sequence references non-existent asset: {asset_id}",
                        {"index": i},
                    )
                )

        # Check for duplicates in sequence
        seen = set()
        for i, asset_id in enumerate(sequence):
            if asset_id in seen:
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_WARNING,
                        "SEQUENCE_DUPLICATE",
                        f"Asset appears multiple times in sequence: {asset_id}",
                        {"index": i},
                    )
                )
            seen.add(asset_id)

    def _check_events_integrity(self, run: Run) -> None:
        """Check events.jsonl integrity."""
        events_file = run.run_dir / "events.jsonl"

        if not events_file.exists():
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_WARNING,
                    "EVENTS_MISSING",
                    "events.jsonl file not found",
                )
            )
            return

        try:
            line_count = 0
            with open(events_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json.loads(line)
                        line_count += 1
                    except json.JSONDecodeError as e:
                        self.issues.append(
                            ValidationIssue(
                                ValidationIssue.SEVERITY_ERROR,
                                "EVENTS_INVALID_JSON",
                                f"Invalid JSON at line {line_num}: {e}",
                            )
                        )

            if line_count == 0:
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_WARNING,
                        "EVENTS_EMPTY",
                        "events.jsonl is empty",
                    )
                )

        except Exception as e:
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_ERROR,
                    "EVENTS_CHECK_FAILED",
                    f"Failed to check events: {e}",
                )
            )

    def _check_orphaned_assets(self, run: Run) -> None:
        """Check for assets on disk not in manifest."""
        try:
            assets_in_manifest = {
                asset_data["path"]
                for asset_data in run.manifest.data.get("assets", {}).values()
            }

            assets_on_disk = set()
            if run.assets_dir.exists():
                for item in run.assets_dir.iterdir():
                    if item.is_file():
                        assets_on_disk.add(item.name)

            orphaned = assets_on_disk - assets_in_manifest
            if orphaned:
                self.issues.append(
                    ValidationIssue(
                        ValidationIssue.SEVERITY_INFO,
                        "ORPHANED_ASSETS",
                        f"Found {len(orphaned)} asset(s) not referenced in manifest",
                        {"files": sorted(list(orphaned))},
                    )
                )

        except Exception as e:
            self.issues.append(
                ValidationIssue(
                    ValidationIssue.SEVERITY_WARNING,
                    "ORPHAN_CHECK_FAILED",
                    f"Failed to check for orphaned assets: {e}",
                )
            )

    def _build_report(self, passed: bool) -> Dict[str, Any]:
        """Build validation report."""
        return {
            "status": "ok" if passed else "error",
            "passed": passed,
            "checks": {
                "manifest_valid": not self._has_issue_code("MANIFEST_"),
                "assets_complete": not self._has_issue_code("ASSET_"),
                "sequence_valid": not self._has_issue_code("SEQUENCE_"),
                "events_valid": not self._has_issue_code("EVENTS_INVALID_JSON"),
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "summary": {
                "errors": sum(
                    1
                    for issue in self.issues
                    if issue.severity == ValidationIssue.SEVERITY_ERROR
                ),
                "warnings": sum(
                    1
                    for issue in self.issues
                    if issue.severity == ValidationIssue.SEVERITY_WARNING
                ),
                "info": sum(
                    1
                    for issue in self.issues
                    if issue.severity == ValidationIssue.SEVERITY_INFO
                ),
            },
        }

    def _has_issue_code(self, prefix: str) -> bool:
        """Check if any issue code starts with prefix."""
        return any(
            issue.code.startswith(prefix)
            and issue.severity == ValidationIssue.SEVERITY_ERROR
            for issue in self.issues
        )


def validate_run(run_dir: str) -> Dict[str, Any]:
    """Validate a VidSlide run directory.

    Args:
        run_dir: Path to run directory

    Returns:
        Validation report dictionary
    """
    validator = RunValidator(Path(run_dir))
    return validator.validate()


__all__ = ["validate_run", "RunValidator", "ValidationIssue"]
