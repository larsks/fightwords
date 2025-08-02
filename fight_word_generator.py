#!/usr/bin/env python3
"""
Batman-style fight word generator with black & white dithering
Creates 128x64 pixel images from word list
"""

import math
import os
import random
import sys
import argparse

from typing import cast
from dataclasses import dataclass
from functools import cache

from PIL import Image, ImageDraw, ImageFont, ImageOps
from matplotlib import font_manager


@dataclass
class Args:
    input_file: str
    font_names: str
    output_dir: str
    distortions: str
    negate: bool


class FontManager:
    """Handles font loading and caching"""

    font_names: list[str]
    font_paths: list[str]
    font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont]

    def __init__(self, font_names: list[str] | None = None):
        self.font_names = font_names or []
        self.font_cache = {}
        self.font_paths = self._resolve_font_paths()

    def _resolve_font_paths(self) -> list[str]:
        """Resolve font names to actual file paths"""
        paths: list[str] = []
        for font_name in self.font_names:
            font_path = os.path.expanduser(font_name)
            if os.path.exists(font_path):
                paths.append(font_path)
            else:
                font_path = self._find_font_file(font_name)

            if font_path:
                paths.append(font_path)
        return paths

    @cache
    def _find_font_file(self, font_name: str) -> str | None:
        """Find font file by name using matplotlib font manager"""
        # Try common variations of the font name
        name_variants: list[str] = [
            font_name,
            font_name.replace(" ", ""),
            font_name.replace(" ", "-"),
            font_name.replace(" ", "_"),
        ]

        # Get all system fonts
        try:
            system_fonts: list[str] = font_manager.findSystemFonts()  # pyright:ignore[reportUnknownMemberType]
        except Exception:
            return None

        for variant in name_variants:
            variant_lower = variant.lower()

            # Search through system fonts
            for font_path in system_fonts:
                try:
                    # Get font properties
                    font_props = font_manager.FontProperties(fname=font_path)
                    font_family: str = font_props.get_name().lower()

                    # Check if variant matches font family name
                    if variant_lower in font_family or font_family in variant_lower:
                        if os.path.exists(font_path):
                            return font_path

                    # Also check the filename without extension
                    font_filename = os.path.splitext(os.path.basename(font_path))[
                        0
                    ].lower()
                    if variant_lower in font_filename or font_filename in variant_lower:
                        if os.path.exists(font_path):
                            return font_path

                except Exception:
                    continue

        return None

    def get_font(self, font_size: int):
        """Get a font of specified size, randomly selecting from available fonts"""
        if self.font_paths:
            # Randomly select a font path first
            selected_font_path = random.choice(self.font_paths)

            # Create cache key combining path and size
            cache_key = (selected_font_path, font_size)

            # Check if this specific font+size combination is cached
            if cache_key not in self.font_cache:
                try:
                    font = ImageFont.truetype(selected_font_path, font_size)
                    self.font_cache[cache_key] = font
                except (OSError, IOError):
                    print(f"Warning: Could not load font from '{selected_font_path}'")
                    # Fall through to default fonts
                    return self._get_default_font(font_size)

            return self.font_cache[cache_key]

        # No custom fonts available, use default
        return self._get_default_font(font_size)

    @cache
    def _get_default_font(
        self, font_size: int
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get default system font for given size"""
        # Try default system fonts
        try:
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                font_size,
            )
        except Exception:
            try:
                return ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                return ImageFont.load_default()


class TextRenderer:
    """Handles text rendering with outlines"""

    font_manager: FontManager

    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager

    def calculate_font_size(self, text: str, max_width: int, max_height: int):
        """Calculate optimal font size for the given text and constraints with random variation"""
        # More aggressive sizing - aim to fill more of the available space
        if len(text) <= 4:  # Short words like "POW!", "BAM!"
            base_font_size = min(max_width // len(text) * 3, max_height * 0.7)
        elif len(text) <= 7:  # Medium words like "KAPOW!"
            base_font_size = min(max_width // len(text) * 2.5, max_height * 0.6)
        else:  # Long words like "AWKKKKKK!"
            base_font_size = min(max_width // len(text) * 2, max_height * 0.5)

        base_font_size = max(12, min(base_font_size, 64))  # Expanded bounds

        # Add random variation (±20%)
        variation = random.uniform(0.8, 1.2)
        font_size = int(base_font_size * variation)
        return max(12, min(font_size, 64))  # Keep within expanded bounds

    def draw_text_with_outline(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
        outline_width: int = 2,
    ):
        """Draw text with bold black outline"""
        # Draw outline
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x != 0 or adj_y != 0:
                    draw.text(
                        (x + adj_x, y + adj_y), text, font=font, fill=0
                    )  # Black outline

        # Draw main text in white
        draw.text((x, y), text, font=font, fill=255)

    def render_text(
        self,
        text: str,
        canvas_size: int,
        target_width: int,
        target_height: int,
        scale_factor: int,
    ):
        """Render text on a canvas with optimal sizing and positioning"""
        # Create canvas
        img = Image.new("L", (canvas_size, canvas_size), 255)
        draw = ImageDraw.Draw(img)

        # Calculate font size and load font
        font_size = self.calculate_font_size(text, target_width, target_height)
        font = self.font_manager.get_font(font_size)

        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text on canvas
        text_x = int((canvas_size - text_width) // 2)
        text_y = int((canvas_size - text_height) // 2)

        # Add random position offset
        max_offset_x = int(max(0, (target_width - text_width) // 3))
        max_offset_y = int(max(0, (target_height - text_height) // 3))

        if max_offset_x > 0:
            offset_x = random.randint(-max_offset_x, max_offset_x)
        else:
            offset_x = 0

        if max_offset_y > 0:
            offset_y = random.randint(-max_offset_y, max_offset_y)
        else:
            offset_y = 0

        text_x += offset_x
        text_y += offset_y

        # Draw text with outline
        self.draw_text_with_outline(
            draw, text, text_x, text_y, font, outline_width=2 * scale_factor
        )

        return img


class ImageDistorter:
    """Handles various image distortion effects"""

    all_distortions: list[str] = ["shear", "fisheye", "perspective"]
    enabled_distortions: list[str]

    def __init__(self, enabled_distortions: list[str] | None = None):
        if enabled_distortions is None:
            self.enabled_distortions = self.all_distortions
        else:
            self.enabled_distortions = enabled_distortions

    def apply_shear(self, image: Image.Image):
        """Apply shear distortion"""
        shear_x = random.uniform(-0.25, 0.25)
        shear_y = random.uniform(-0.15, 0.15)

        width, height = image.size
        distorted = Image.new("L", (width, height), 255)

        for y in range(height):
            for x in range(width):
                src_x = int(x - shear_x * y)
                src_y = int(y - shear_y * x)

                if 0 <= src_x < width and 0 <= src_y < height:
                    pixel: int = cast(int, image.getpixel((src_x, src_y)))
                    distorted.putpixel((x, y), pixel)

                    # Why would pixel ever be None?

        return distorted

    def apply_fisheye(self, image: Image.Image):
        """Apply fisheye lens distortion"""
        width, height = image.size
        distorted = Image.new("L", (width, height), 255)

        # Random center point (not always dead center)
        center_x = width // 2 + random.randint(-width // 6, width // 6)
        center_y = height // 2 + random.randint(-height // 6, height // 6)

        # Random strength and radius
        strength = random.uniform(0.3, 0.9)  # Bulge strength
        max_radius = min(width, height) * 0.7  # Effective radius

        for y in range(height):
            for x in range(width):
                # Distance from center
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx * dx + dy * dy)

                # Default to original pixel
                pixel: int = cast(int, image.getpixel((x, y)))

                if distance < max_radius and distance > 0:
                    # Fish-eye transformation
                    factor = 1 + strength * (1 - distance / max_radius)

                    # Apply bulge effect
                    src_x = int(center_x + dx / factor)
                    src_y = int(center_y + dy / factor)

                    if 0 <= src_x < width and 0 <= src_y < height:
                        pixel = cast(int, image.getpixel((src_x, src_y)))

                distorted.putpixel((x, y), pixel)

        return distorted

    def apply_perspective(self, image: Image.Image):
        """Apply perspective-like distortion by stretching corners"""
        stretch_factor = random.uniform(0.05, 0.25)
        corner = random.choice(["top", "bottom", "left", "right"])

        width, height = image.size
        distorted = Image.new("L", (width, height), 255)

        for y in range(height):
            for x in range(width):
                # Initialize both coordinates
                src_x = x
                src_y = y

                if corner == "top":
                    factor = 1 + stretch_factor * (1 - y / height)
                    src_x = int(x / factor + (width * (factor - 1)) / (2 * factor))
                elif corner == "bottom":
                    factor = 1 + stretch_factor * (y / height)
                    src_x = int(x / factor + (width * (factor - 1)) / (2 * factor))
                elif corner == "left":
                    factor = 1 + stretch_factor * (1 - x / width)
                    src_y = int(y / factor + (height * (factor - 1)) / (2 * factor))
                else:  # right
                    factor = 1 + stretch_factor * (x / width)
                    src_y = int(y / factor + (height * (factor - 1)) / (2 * factor))

                if 0 <= src_x < width and 0 <= src_y < height:
                    pixel: int = cast(int, image.getpixel((src_x, src_y)))
                    distorted.putpixel((x, y), pixel)

        return distorted

    def apply_distortions(self, image: Image.Image):
        """Apply all enabled distortions to the image"""
        result = image

        if "shear" in self.enabled_distortions:
            result = self.apply_shear(result)

        if "fisheye" in self.enabled_distortions:
            result = self.apply_fisheye(result)

        if "perspective" in self.enabled_distortions:
            result = self.apply_perspective(result)

        return result


@dataclass
class WordGenerator:
    """Main class for generating fight word images"""

    width: int = 128
    height: int = 64
    negate: bool = False
    seed: int | None = None
    font_names: list[str] | None = None
    distortions: list[str] | None = None
    font_manager: FontManager | None = None
    text_renderer: TextRenderer | None = None
    distorter: ImageDistorter | None = None

    def __post_init__(
        self,
    ):
        # Initialize components
        self.font_manager = FontManager(self.font_names)
        self.text_renderer = TextRenderer(self.font_manager)
        self.distorter = ImageDistorter(self.distortions)

        if self.seed is not None:
            random.seed(self.seed)

    def get_content_bounds(self, image: Image.Image):
        """Find the bounding box of non-white content in the image"""
        if image.mode != "L":
            image = image.convert("L")

        width, height = image.size
        left, top, right, bottom = width, height, 0, 0

        # Find the bounds of non-white content (anything < 255)
        for y in range(height):
            for x in range(width):
                if cast(int, image.getpixel((x, y))) < 255:  # Non-white pixel
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)

        # If no content found, return full image bounds
        if left >= right or top >= bottom:
            return (0, 0, width, height)

        return (left, top, right + 1, bottom + 1)

    def apply_rotation(self, image: Image.Image):
        """Apply random rotation to the image"""
        rotation_angle = random.uniform(-15, 15)
        return image.rotate(rotation_angle, expand=False, fillcolor=255)

    def scale_to_target(self, image: Image.Image):
        """Scale image to target dimensions while maintaining aspect ratio"""
        # Find content bounds
        content_bounds = self.get_content_bounds(image)

        # Crop to content bounds
        cropped_img = image.crop(content_bounds)

        # Calculate scale to fit within target dimensions
        crop_width = content_bounds[2] - content_bounds[0]
        crop_height = content_bounds[3] - content_bounds[1]

        scale_x = self.width / crop_width
        scale_y = self.height / crop_height
        scale = min(scale_x, scale_y)  # Use smaller scale to ensure it fits

        # Calculate new size and resize
        new_width = int(crop_width * scale)
        new_height = int(crop_height * scale)
        scaled_img: Image.Image = cropped_img.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )

        # Create final image and center the scaled content
        final_img = Image.new("L", (self.width, self.height), 255)
        x_offset = (self.width - new_width) // 2
        y_offset = (self.height - new_height) // 2
        final_img.paste(scaled_img, (x_offset, y_offset))

        return final_img

    def apply_dithering(self, image: Image.Image):
        """Apply dithering to convert grayscale to pure B&W"""
        return image.convert("1")

    def generate(self, word: str, output_path: str | None = None) -> Image.Image:
        """Generate a fight word image"""
        # Set up canvas dimensions
        scale_factor = 4
        large_width = self.width * scale_factor
        large_height = self.height * scale_factor
        canvas_size = max(large_width, large_height) * 2

        # Make type checker happy
        assert self.text_renderer is not None
        assert self.distorter is not None

        # Render text
        text_img = self.text_renderer.render_text(
            word, canvas_size, large_width, large_height, scale_factor
        )

        # Apply rotation
        rotated_img = self.apply_rotation(text_img)

        # Crop to working size
        left = (canvas_size - large_width) // 2
        top = (canvas_size - large_height) // 2
        right = left + large_width
        bottom = top + large_height
        working_img = rotated_img.crop((left, top, right, bottom))

        # Apply distortions
        distorted_img = self.distorter.apply_distortions(working_img)

        # Scale to target size
        final_img = self.scale_to_target(distorted_img)

        # Apply dithering
        dithered_img = self.apply_dithering(final_img)

        # Apply color negation if requested
        if self.negate:
            dithered_img = ImageOps.invert(dithered_img.convert("L")).convert("1")

        # Save if output path provided
        if output_path:
            dithered_img.save(output_path)

        return dithered_img

    def process_word_list(self, input_file: str, output_dir: str = "output"):
        """Process entire word list from file"""
        os.makedirs(output_dir, exist_ok=True)

        with open(input_file, "r") as f:
            words = [line.strip() for line in f if line.strip()]

        print(f"Processing {len(words)} fight words...")

        for word in words:
            if not word:  # Skip empty words
                continue

            if word.startswith("#"):  # Skip comments
                continue

            # Clean filename
            filename = (
                f"{word.replace('!', '').replace('-', '_').replace(' ', '_')}.png"
            )
            output_path = os.path.join(output_dir, filename)

            print(f"Generating {filename}...")
            _ = self.generate(word, output_path)

        print(f"Done! Generated {len([w for w in words if w])} images in {output_dir}/")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Batman-style fight word images"
    )
    _ = parser.add_argument(
        "input_file",
        nargs="?",
        default="words.txt",
        help="Input file containing fight words (default: words.txt)",
    )
    _ = parser.add_argument(
        "--font",
        dest="font_names",
        help="Comma-separated list of font paths or names (e.g., arial.ttf,helvetica.ttf)",
    )
    _ = parser.add_argument(
        "--output",
        dest="output_dir",
        default="output",
        help="Output directory (default: output)",
    )
    _ = parser.add_argument(
        "--negate",
        action="store_true",
        help="Reverse colors (white text on black background)",
    )
    _ = parser.add_argument(
        "--distortion",
        dest="distortions",
        help="Comma-separated list of distortions to apply (shear,fisheye,perspective). Default: all",
    )

    return Args(**vars(parser.parse_args()))  # pyright:ignore[reportAny]


def main():
    args = parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: {args.input_file} not found!")
        sys.exit(1)

    # Parse distortions
    allowed_distortions: list[str] | None = None
    if args.distortions:
        allowed_distortions = [d.strip() for d in args.distortions.split(",")]
        valid_distortions = ["shear", "fisheye", "perspective"]
        invalid = [d for d in allowed_distortions if d not in valid_distortions]
        if invalid:
            print(f"Error: Invalid distortion types: {', '.join(invalid)}")
            print(f"Valid options: {', '.join(valid_distortions)}")
            sys.exit(1)

    # Parse font names
    font_names = []
    if args.font_names:
        font_names = [name.strip() for name in args.font_names.split(",")]

    generator = WordGenerator(
        font_names=font_names, negate=args.negate, distortions=allowed_distortions
    )
    generator.process_word_list(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
