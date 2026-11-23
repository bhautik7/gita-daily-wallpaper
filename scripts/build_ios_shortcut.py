#!/usr/bin/env python3
"""Build an unsigned Apple Shortcuts (.shortcut) binary plist for daily iPhone wallpaper updates."""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import uuid


DEFAULT_DAILY_BASE_URL = "https://bhautik7.github.io/gita-daily-wallpaper/daily/"
DEFAULT_SHORTCUT_URL = DEFAULT_DAILY_BASE_URL


def build_shortcut_dict(daily_base_url: str = DEFAULT_DAILY_BASE_URL) -> dict:
    """Construct the 6-action Shortcuts workflow targeting daily/<yyyy-MM-dd>.jpg."""
    base_url = daily_base_url if daily_base_url.endswith("/") else f"{daily_base_url}/"

    fmt_uuid = str(uuid.uuid4()).upper()
    url_uuid = str(uuid.uuid4()).upper()
    download_uuid = str(uuid.uuid4()).upper()
    convert_uuid = str(uuid.uuid4()).upper()
    save_uuid = str(uuid.uuid4()).upper()

    actions = [
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.format.date",
            "WFWorkflowActionParameters": {
                "UUID": fmt_uuid,
                "WFDate": {
                    "Value": {
                        "Type": "CurrentDate",
                    },
                    "WFSerializationType": "WFTextTokenAttachment",
                },
                "WFDateFormatStyle": "Custom",
                "WFDateFormat": "yyyy-MM-dd",
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.url",
            "WFWorkflowActionParameters": {
                "UUID": url_uuid,
                "WFURLActionURL": {
                    "Value": {
                        "string": f"{base_url}\ufffc.jpg",
                        "attachmentsByRange": {
                            f"{{{len(base_url)}, 1}}": {
                                "OutputName": "Formatted Date",
                                "OutputUUID": fmt_uuid,
                                "Type": "ActionOutput",
                            }
                        },
                    },
                    "WFSerializationType": "WFTextTokenString",
                },
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
            "WFWorkflowActionParameters": {
                "UUID": download_uuid,
                "WFURL": {
                    "Value": {
                        "string": "\ufffc",
                        "attachmentsByRange": {
                            "{0, 1}": {
                                "OutputName": "URL",
                                "OutputUUID": url_uuid,
                                "Type": "ActionOutput",
                            }
                        },
                    },
                    "WFSerializationType": "WFTextTokenString",
                },
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.image.convert",
            "WFWorkflowActionParameters": {
                "UUID": convert_uuid,
                "WFImageFormat": "JPEG",
                "WFImageCompressionQuality": 0.95,
                "WFInput": {
                    "Value": {
                        "OutputName": "Contents of URL",
                        "OutputUUID": download_uuid,
                        "Type": "ActionOutput",
                    },
                    "WFSerializationType": "WFTextTokenAttachment",
                },
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.savetocameraroll",
            "WFWorkflowActionParameters": {
                "UUID": save_uuid,
                "WFAlbumName": "Recents",
                "WFInput": {
                    "Value": {
                        "OutputName": "Converted Image",
                        "OutputUUID": convert_uuid,
                        "Type": "ActionOutput",
                    },
                    "WFSerializationType": "WFTextTokenAttachment",
                },
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.wallpaper.set",
            "WFWorkflowActionParameters": {
                "WFWallpaperLocation": "Lock Screen",
                "WFWallpaperShowPreview": False,
                "WFWallpaperSmartCrop": False,
                "WFInput": {
                    "Value": {
                        "OutputName": "Saved Photo",
                        "OutputUUID": save_uuid,
                        "Type": "ActionOutput",
                    },
                    "WFSerializationType": "WFTextTokenAttachment",
                },
            },
        },
    ]

    return {
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowClientVersion": "2605.0.5",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 4282601983,
            "WFWorkflowIconGlyphNumber": 59771,
        },
        "WFWorkflowActions": actions,
        "WFWorkflowInputContentItemClasses": [
            "WFGenericFileContentItem",
            "WFImageContentItem",
            "WFStringContentItem",
            "WFURLContentItem",
        ],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
    }


def write_shortcut(out_path: Path, daily_base_url: str = DEFAULT_DAILY_BASE_URL) -> Path:
    """Write the shortcut binary plist to out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    workflow = build_shortcut_dict(daily_base_url=daily_base_url)
    with out_path.open("wb") as fp:
        plistlib.dump(workflow, fp, fmt=plistlib.FMT_BINARY)
    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unsigned Daily Gita Wallpaper .shortcut file.")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for the unsigned .shortcut binary plist",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_DAILY_BASE_URL,
        help=f"Base URL for daily YYYY-MM-DD.jpg wallpapers (default: {DEFAULT_DAILY_BASE_URL})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    written = write_shortcut(args.out, daily_base_url=args.url)
    print(f"Wrote unsigned shortcut plist: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
