#!/usr/bin/env python3
"""VidSlide Agent CLI - Main entry point."""

import argparse
import sys
from typing import List, Optional

from vidslide import __version__, __engine_baseline__, __baseline_commit__
from vidslide.errors import VidSlideError, get_exit_code
from vidslide.output import output_json, make_result, make_error_result
from vidslide.protocol import CommandStatus


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="vidslide",
        description="VidSlide Agent CLI - AI-native PPT extraction from screen recordings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} (engine: {__engine_baseline__}, baseline: {__baseline_commit__[:8]})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # capabilities
    subparsers.add_parser(
        "capabilities",
        help="Show CLI capabilities and available features",
    )

    # doctor
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check environment and dependencies",
    )
    doctor_parser.add_argument(
        "run",
        nargs="?",
        help="Optional: check specific run directory integrity",
    )

    # probe
    probe_parser = subparsers.add_parser(
        "probe",
        help="Check video file and get metadata",
    )
    probe_parser.add_argument("video", help="Path to video file")

    # extract
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract slides from video",
    )
    extract_parser.add_argument("video", help="Path to video file")
    extract_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: VIDEO.vidslide)",
    )
    extract_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume incomplete extraction",
    )
    extract_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output",
    )

    # validate
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate run directory integrity",
    )
    validate_parser.add_argument("run", help="Path to run directory")

    # export
    export_parser = subparsers.add_parser(
        "export",
        help="Export run to PPTX format",
    )
    export_parser.add_argument("run_dir", help="Path to run directory")
    export_parser.add_argument(
        "--output",
        "-o",
        help="Output PPTX file path (default: RUN_DIR.pptx)",
    )
    export_parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Don't include source metadata in speaker notes",
    )

    # recover
    recover_parser = subparsers.add_parser(
        "recover",
        help="Analyze and recover corrupted runs",
    )
    recover_parser.add_argument("run_dir", help="Path to run directory")
    recover_parser.add_argument(
        "--from-events",
        action="store_true",
        help="Reconstruct manifest from events.jsonl",
    )
    recover_parser.add_argument(
        "--from-assets",
        action="store_true",
        help="Salvage data from asset files",
    )

    # context
    context_parser = subparsers.add_parser(
        "context",
        help="Get semantic context about extracted slides",
    )
    context_parser.add_argument("run_dir", help="Path to run directory")
    context_parser.add_argument(
        "--slide",
        type=int,
        help="Show context for specific slide index (0-based)",
    )
    context_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # overview
    overview_parser = subparsers.add_parser(
        "overview",
        help="Generate summary of run",
    )
    overview_parser.add_argument("run_dir", help="Path to run directory")
    overview_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include additional details",
    )
    overview_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # audit
    audit_parser = subparsers.add_parser(
        "audit",
        help="Get detailed audit trail from events",
    )
    audit_parser.add_argument("run_dir", help="Path to run directory")
    audit_parser.add_argument(
        "--event-type",
        help="Filter by event type",
    )
    audit_parser.add_argument(
        "--asset-id",
        help="Filter by asset ID (show asset history)",
    )
    audit_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # resolve
    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Apply resolution action to run",
    )
    resolve_parser.add_argument("run_dir", help="Path to run directory")
    resolve_parser.add_argument(
        "--action-json",
        required=True,
        help="JSON action specification (see documentation)",
    )
    resolve_parser.add_argument(
        "--reason",
        help="Human-readable reason for the action",
    )

    # TODO: Add other commands (run)

    return parser


def cmd_capabilities(args) -> int:
    """Execute capabilities command."""
    from vidslide.capabilities import get_capabilities

    result = get_capabilities()
    output_json(
        make_result(
            command="capabilities",
            status=CommandStatus.OK,
            result=result,
        )
    )
    return 0


def cmd_doctor(args) -> int:
    """Execute doctor command."""
    from vidslide.doctor import run_doctor

    result = run_doctor(args.run)
    output_json(
        make_result(
            command="doctor",
            status=CommandStatus.OK,
            result=result,
        )
    )
    return 0


def cmd_probe(args) -> int:
    """Execute probe command."""
    from vidslide.probe import probe_video

    result = probe_video(args.video)

    # Add next actions
    next_actions = [
        {
            "command": "extract",
            "args": [result["path"]],
        }
    ]

    output_json(
        make_result(
            command="probe",
            status=CommandStatus.OK,
            result=result,
            next_actions=next_actions,
        )
    )
    return 0


def cmd_extract(args) -> int:
    """Execute extract command."""
    from vidslide.extract import extract_video

    result = extract_video(
        video_path=args.video,
        output_dir=args.output,
        overwrite=args.overwrite,
        resume=args.resume,
    )

    # Add next actions
    next_actions = [
        {
            "command": "validate",
            "run": result["run_dir"],
        }
    ]

    output_json(
        make_result(
            command="extract",
            status=CommandStatus.OK,
            result=result,
            next_actions=next_actions,
        )
    )
    return 0


def cmd_validate(args) -> int:
    """Execute validate command."""
    from vidslide.validate import validate_run

    result = validate_run(args.run)

    output_json(
        make_result(
            command="validate",
            status=CommandStatus.OK if result["passed"] else CommandStatus.ERROR,
            result=result,
        )
    )
    return 0 if result["passed"] else 1


def cmd_export(args) -> int:
    """Execute export command."""
    from vidslide.export import export_to_pptx

    try:
        result = export_to_pptx(
            run_dir=args.run_dir,
            output_path=args.output if args.output else None,
            include_metadata=not args.no_metadata,
        )

        output_json(
            make_result(
                command="export",
                status=CommandStatus.OK,
                result=result,
            )
        )
        return 0

    except Exception as e:
        output_json(
            make_error_result(
                command="export",
                error_code="EXPORT_FAILED",
                error_message=str(e),
            )
        )
        return 1


def cmd_recover(args) -> int:
    """Execute recover command."""
    from vidslide.recover import analyze_run, reconstruct_from_events, RecoveryError

    run_dir = Path(args.run_dir)

    if args.from_events:
        # Reconstruct from events
        try:
            manifest_data = reconstruct_from_events(run_dir)

            # Save reconstructed manifest
            manifest_path = run_dir / "manifest.json.recovered"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2)

            result = {
                "success": True,
                "action": "reconstructed",
                "output": str(manifest_path),
                "message": "Manifest reconstructed from events.jsonl"
            }

            output_json(
                make_result(
                    command="recover",
                    status=CommandStatus.OK,
                    result=result,
                )
            )
            return 0

        except RecoveryError as e:
            output_json(
                make_error_result(
                    command="recover",
                    error_code="RECOVERY_FAILED",
                    error_message=str(e),
                )
            )
            return 1
    else:
        # Analyze only
        report = analyze_run(str(run_dir))

        output_json(
            make_result(
                command="recover",
                status=CommandStatus.OK if report.recoverable else CommandStatus.ERROR,
                result=report.to_dict(),
            )
        )
        return 0 if report.recoverable else 1


def cmd_context(args) -> int:
    """Execute context command."""
    from vidslide.context import cmd_context as context_handler

    return context_handler(args)


def cmd_overview(args) -> int:
    """Execute overview command."""
    from vidslide.overview import cmd_overview as overview_handler

    return overview_handler(args)


def cmd_audit(args) -> int:
    """Execute audit command."""
    from vidslide.audit import cmd_audit as audit_handler

    return audit_handler(args)


def cmd_resolve(args) -> int:
    """Execute resolve command."""
    from vidslide.resolve import cmd_resolve as resolve_handler

    return resolve_handler(args)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 2

    try:
        # Dispatch to command handler
        command_handlers = {
            "capabilities": cmd_capabilities,
            "doctor": cmd_doctor,
            "probe": cmd_probe,
            "extract": cmd_extract,
            "validate": cmd_validate,
            "export": cmd_export,
            "recover": cmd_recover,
            "context": cmd_context,
            "overview": cmd_overview,
            "audit": cmd_audit,
            "resolve": cmd_resolve,
        }

        handler = command_handlers.get(args.command)
        if not handler:
            output_json(
                make_error_result(
                    command=args.command,
                    error_code="NOT_IMPLEMENTED",
                    error_message=f"Command '{args.command}' not implemented yet",
                )
            )
            return 1

        return handler(args)

    except VidSlideError as e:
        output_json(
            make_error_result(
                command=args.command,
                error_code=e.code,
                error_message=e.message,
                retryable=e.retryable,
                **e.details,
            )
        )
        return get_exit_code(e.code)

    except KeyboardInterrupt:
        output_json(
            make_error_result(
                command=args.command,
                error_code="CANCELLED",
                error_message="Operation cancelled by user",
            )
        )
        return 21

    except Exception as e:
        output_json(
            make_error_result(
                command=args.command,
                error_code="INTERNAL_ERROR",
                error_message=str(e),
            )
        )
        return 50


if __name__ == "__main__":
    sys.exit(main())
