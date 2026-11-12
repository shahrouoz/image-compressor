#!/usr/bin/env python3
"""
Image Compressor - Batch compress images with quality control
Supports JPEG, PNG, and WebP formats.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is not installed.")
    print("Install it with: pip install Pillow")
    sys.exit(1)


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_image_files(input_path: Path) -> List[Path]:
    """Collect all supported image files from a file or directory."""
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [input_path]
        return []

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(input_path.rglob(f"*{ext}"))
        files.extend(input_path.rglob(f"*{ext.upper()}"))
    return sorted(set(files))


def compress_image(
    input_file: Path,
    output_file: Path,
    quality: int,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    convert_to: Optional[str] = None,
) -> tuple[bool, str]:
    """Compress a single image. Returns (success, message)."""
    try:
        with Image.open(input_file) as img:
            original_size = input_file.stat().st_size

            # Convert mode if needed
            if img.mode in ("RGBA", "P") and convert_to in ("jpeg", "jpg"):
                img = img.convert("RGB")
            elif img.mode == "P":
                img = img.convert("RGBA")

            # Resize if requested
            if max_width or max_height:
                img.thumbnail(
                    (max_width or img.width, max_height or img.height),
                    Image.Resampling.LANCZOS,
                )

            # Determine output format
            output_format = convert_to.upper() if convert_to else img.format or "JPEG"
            if output_format == "JPG":
                output_format = "JPEG"

            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Save with compression
            save_kwargs = {"optimize": True}
            if output_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = quality
            if output_format == "PNG":
                save_kwargs["optimize"] = True

            img.save(output_file, format=output_format, **save_kwargs)

            new_size = output_file.stat().st_size
            reduction = (1 - new_size / original_size) * 100 if original_size > 0 else 0

            return True, f"{reduction:.1f}% smaller ({original_size//1024}KB → {new_size//1024}KB)"

    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Batch compress images (JPEG, PNG, WebP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./photos
  %(prog)s ./photos -q 75 -o ./compressed
  %(prog)s image.jpg --max-width 1920
  %(prog)s ./folder --convert webp -q 80
        """,
    )
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: creates 'compressed' subfolder or overwrites with --overwrite)",
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=85,
        help="Compression quality 1-100 (default: 85)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        help="Maximum width in pixels (maintains aspect ratio)",
    )
    parser.add_argument(
        "--max-height",
        type=int,
        help="Maximum height in pixels (maintains aspect ratio)",
    )
    parser.add_argument(
        "--convert",
        choices=["jpeg", "jpg", "png", "webp"],
        help="Convert all images to this format",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite original files (use with caution)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually compressing",
    )

    args = parser.parse_args()

    # Validate quality
    if not 1 <= args.quality <= 100:
        print("Error: Quality must be between 1 and 100")
        sys.exit(1)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: Path does not exist: {input_path}")
        sys.exit(1)

    # Collect files
    files = get_image_files(input_path)
    if not files:
        print("No supported image files found.")
        print(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(0)

    print(f"Found {len(files)} image(s)\n")

    # Determine output strategy
    if args.overwrite:
        output_base = None
    elif args.output:
        output_base = Path(args.output).resolve()
    else:
        if input_path.is_file():
            output_base = input_path.parent / "compressed"
        else:
            output_base = input_path / "compressed"

    success_count = 0
    fail_count = 0

    for i, file in enumerate(files, 1):
        if args.overwrite:
            output_file = file
        else:
            if input_path.is_file():
                rel_path = file.name
            else:
                rel_path = file.relative_to(input_path)
            output_file = output_base / rel_path

            # Change extension if converting
            if args.convert:
                ext_map = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}
                output_file = output_file.with_suffix(ext_map[args.convert])

        status = f"[{i}/{len(files)}] {file.name}"

        if args.dry_run:
            print(f"{status} → {output_file}")
            continue

        success, message = compress_image(
            file,
            output_file,
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
            convert_to=args.convert,
        )

        if success:
            print(f"{status} ✓ {message}")
            success_count += 1
        else:
            print(f"{status} ✗ Error: {message}")
            fail_count += 1

    if not args.dry_run:
        print(f"\nDone: {success_count} compressed, {fail_count} failed")
        if output_base and not args.overwrite:
            print(f"Output folder: {output_base}")


if __name__ == "__main__":
    main()
