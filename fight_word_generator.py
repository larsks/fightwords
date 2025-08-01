#!/usr/bin/env python3
"""
Batman-style fight word generator with black & white dithering
Creates 128x64 pixel images from word list
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os
import sys
import random
import argparse
import fontconfig
from PIL import ImageFilter


class FightWordGenerator:
    def __init__(
        self,
        width=128,
        height=64,
        seed=None,
        font_names=None,
        negate=False,
        distortions=None,
    ):
        self.width = width
        self.height = height
        self.font_names = font_names or []
        self.negate = negate
        self.font_cache = {}  # Cache loaded fonts by size

        # Set allowed distortions
        if distortions is None:
            self.allowed_distortions = ["shear", "fisheye", "perspective"]
        else:
            self.allowed_distortions = distortions

        # Resolve font paths during initialization
        self.font_paths = []
        for font_name in self.font_names:
            if os.path.exists(font_name):
                self.font_paths.append(font_name)
            else:
                font_path = self._find_font_file(font_name)
                if font_path:
                    self.font_paths.append(font_path)

        if seed is not None:
            random.seed(seed)  # For reproducible results in testing

    def apply_dithering(self, image):
        """Apply dithering to convert grayscale to pure B&W using PIL's built-in method"""
        return image.convert("1")  # PIL automatically applies Floyd-Steinberg dithering

    def get_content_bounds(self, image):
        """Find the bounding box of non-white content in the image"""
        # Convert to grayscale if needed
        if image.mode != 'L':
            image = image.convert('L')
        
        width, height = image.size
        left, top, right, bottom = width, height, 0, 0
        
        # Find the bounds of non-white content (anything < 255)
        for y in range(height):
            for x in range(width):
                if image.getpixel((x, y)) < 255:  # Non-white pixel
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)
        
        # If no content found, return full image bounds
        if left >= right or top >= bottom:
            return (0, 0, width, height)
        
        return (left, top, right + 1, bottom + 1)

    def create_starburst_background(self, draw, cx, cy, inner_radius, outer_radius):
        """Create randomized starburst background with varying points and irregularity"""
        points = random.randint(12, 20)  # Variable number of points
        angle_step = 2 * math.pi / points

        for i in range(points):
            angle1 = i * angle_step + random.uniform(
                -0.1, 0.1
            )  # Slight angle variation

            # Add radius variation for irregular spikes
            outer_var = random.uniform(0.7, 1.3)
            inner_var = random.uniform(0.6, 1.2)

            # Outer points with variation
            x1_out = cx + (outer_radius * outer_var) * math.cos(angle1)
            y1_out = cy + (outer_radius * outer_var) * math.sin(angle1)

            # Inner points with variation
            x1_in = cx + (inner_radius * inner_var) * math.cos(angle1 + angle_step / 2)
            y1_in = cy + (inner_radius * inner_var) * math.sin(angle1 + angle_step / 2)

            # Random gray values for more dithering variation
            gray_value = random.randint(160, 200)
            draw.polygon([(cx, cy), (x1_out, y1_out), (x1_in, y1_in)], fill=gray_value)

    def _find_font_file(self, font_name):
        """Find font file by name using fontconfig"""
        try:
            # Use fontconfig.fromName() to find the font
            font_obj = fontconfig.fromName(font_name)
            if font_obj and hasattr(font_obj, "file"):
                font_path = font_obj.file
                if os.path.exists(font_path):
                    return font_path
        except:
            pass

        # Fallback: try common variations of the font name
        name_variants = [
            font_name,
            font_name.replace(" ", ""),
            font_name.replace(" ", "-"),
            font_name.replace(" ", "_"),
        ]

        for variant in name_variants:
            try:
                font_obj = fontconfig.fromName(variant)
                if font_obj and hasattr(font_obj, "file"):
                    font_path = font_obj.file
                    if os.path.exists(font_path):
                        return font_path
            except:
                continue

        return None

    def _load_font(self, font_size):
        """Load font with specified size, randomly selecting from available fonts and caching"""
        if self.font_paths:
            # Check if we already have fonts cached for this size
            if font_size not in self.font_cache:
                self.font_cache[font_size] = []
                # Load all available fonts for this size
                for font_path in self.font_paths:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        self.font_cache[font_size].append(font)
                    except (OSError, IOError):
                        print(f"Warning: Could not load font from '{font_path}'")

            # If we have cached fonts for this size, randomly select one
            if self.font_cache[font_size]:
                return random.choice(self.font_cache[font_size])

        # Try default system fonts
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                font_size,
            )
            return font
        except:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
                return font
            except:
                return ImageFont.load_default()

    def get_font_size(self, text, max_width, max_height):
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

    def draw_text_with_outline(self, draw, text, x, y, font, outline_width=2):
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

    def generate_fight_word(self, word, output_path=None):
        """Generate a single fight word image with randomized distortion and rotation"""
        # Create much larger canvas for distortions - scale factor for safety margin
        scale_factor = 4
        large_width = self.width * scale_factor
        large_height = self.height * scale_factor
        canvas_size = max(large_width, large_height) * 2
        temp_img = Image.new("L", (canvas_size, canvas_size), 255)
        draw = ImageDraw.Draw(temp_img)

        # Calculate center of temp canvas
        temp_cx, temp_cy = canvas_size // 2, canvas_size // 2

        # Load font with dynamic sizing for larger canvas - no safety margins needed
        font_size = self.get_font_size(word, large_width, large_height)
        font = self._load_font(font_size)

        # Get text dimensions
        bbox = draw.textbbox((0, 0), word, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text on temp canvas
        text_x = (canvas_size - text_width) // 2
        text_y = (canvas_size - text_height) // 2

        # Add generous random position offset - bounds detection will handle it
        max_offset_x = max(0, (large_width - text_width) // 3)
        max_offset_y = max(0, (large_height - text_height) // 3)
        
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

        # Draw text with outline on temp canvas - scale outline too
        self.draw_text_with_outline(draw, word, text_x, text_y, font, outline_width=2 * scale_factor)

        # Apply random rotation (-15 to +15 degrees)
        rotation_angle = random.uniform(-15, 15)
        rotated_img = temp_img.rotate(rotation_angle, expand=False, fillcolor=255)

        # Crop to large size from center before distortions
        left = (canvas_size - large_width) // 2
        top = (canvas_size - large_height) // 2
        right = left + large_width
        bottom = top + large_height
        final_img = rotated_img.crop((left, top, right, bottom))

        if "shear" in self.allowed_distortions:
            # More aggressive shear distortion
            shear_x = random.uniform(-0.25, 0.25)
            shear_y = random.uniform(-0.15, 0.15)

            width, height = final_img.size
            distorted = Image.new("L", (width, height), 255)

            for y in range(height):
                for x in range(width):
                    src_x = int(x - shear_x * y)
                    src_y = int(y - shear_y * x)

                    if 0 <= src_x < width and 0 <= src_y < height:
                        pixel = final_img.getpixel((src_x, src_y))
                        distorted.putpixel((x, y), pixel)

            final_img = distorted

        if "fisheye" in self.allowed_distortions:
            # Fish-eye lens distortion - bulges center and compresses edges
            width, height = final_img.size
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

                    if distance < max_radius and distance > 0:
                        # Fish-eye transformation
                        factor = 1 + strength * (1 - distance / max_radius)

                        # Apply bulge effect
                        src_x = int(center_x + dx / factor)
                        src_y = int(center_y + dy / factor)

                        if 0 <= src_x < width and 0 <= src_y < height:
                            pixel = final_img.getpixel((src_x, src_y))
                            distorted.putpixel((x, y), pixel)
                        else:
                            # Keep original pixel if outside bounds
                            distorted.putpixel((x, y), final_img.getpixel((x, y)))
                    else:
                        # Keep pixels outside the effect radius unchanged
                        distorted.putpixel((x, y), final_img.getpixel((x, y)))

            final_img = distorted

        if "perspective" in self.allowed_distortions:
            # Perspective-like distortion by stretching corners
            stretch_factor = random.uniform(0.05, 0.25)
            corner = random.choice(["top", "bottom", "left", "right"])

            width, height = final_img.size
            distorted = Image.new("L", (width, height), 255)

            for y in range(height):
                for x in range(width):
                    if corner == "top":
                        factor = 1 + stretch_factor * (1 - y / height)
                        src_x = int(x / factor + (width * (factor - 1)) / (2 * factor))
                    elif corner == "bottom":
                        factor = 1 + stretch_factor * (y / height)
                        src_x = int(x / factor + (width * (factor - 1)) / (2 * factor))
                    elif corner == "left":
                        factor = 1 + stretch_factor * (1 - x / width)
                        src_y = int(y / factor + (height * (factor - 1)) / (2 * factor))
                        src_x = x
                    else:  # right
                        factor = 1 + stretch_factor * (x / width)
                        src_y = int(y / factor + (height * (factor - 1)) / (2 * factor))
                        src_x = x

                    if corner in ["top", "bottom"]:
                        src_y = y

                    if 0 <= src_x < width and 0 <= src_y < height:
                        pixel = final_img.getpixel((src_x, src_y))
                        distorted.putpixel((x, y), pixel)

            final_img = distorted

        # Find the bounds of text content after all distortions (ignoring background)
        content_bounds = self.get_content_bounds(final_img)
        
        # Crop to content bounds
        cropped_img = final_img.crop(content_bounds)
        
        # Scale cropped content to fill target size while maintaining aspect ratio
        crop_width = content_bounds[2] - content_bounds[0]
        crop_height = content_bounds[3] - content_bounds[1]
        
        # Calculate scale to fit within target dimensions
        scale_x = self.width / crop_width
        scale_y = self.height / crop_height
        scale = min(scale_x, scale_y)  # Use smaller scale to ensure it fits
        
        # Calculate new size and resize
        new_width = int(crop_width * scale)
        new_height = int(crop_height * scale)
        scaled_img = cropped_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Create clean final image and center the optimally-scaled text
        final_img = Image.new("L", (self.width, self.height), 255)
        x_offset = (self.width - new_width) // 2
        y_offset = (self.height - new_height) // 2
        
        # Paste the text image - clean white background with text
        final_img.paste(scaled_img, (x_offset, y_offset))

        # Apply dithering using PIL's built-in method
        dithered_img = self.apply_dithering(final_img)

        # Apply color negation if requested
        if self.negate:
            # Invert the image (0 becomes 255, 255 becomes 0)
            from PIL import ImageOps

            dithered_img = ImageOps.invert(dithered_img.convert("L")).convert("1")

        if output_path:
            dithered_img.save(output_path)

        return dithered_img

    def process_word_list(self, input_file, output_dir="output"):
        """Process entire word list from file"""
        os.makedirs(output_dir, exist_ok=True)

        with open(input_file, "r") as f:
            words = [line.strip() for line in f if line.strip()]

        print(f"Processing {len(words)} fight words...")

        for i, word in enumerate(words, 1):
            if not word:  # Skip empty words
                continue

            # Clean filename
            filename = (
                f"{word.replace('!', '').replace('-', '_').replace(' ', '_')}.png"
            )
            output_path = os.path.join(output_dir, filename)

            print(f"Generating {filename}...")
            self.generate_fight_word(word, output_path)

        print(f"Done! Generated {len([w for w in words if w])} images in {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Batman-style fight word images"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default="words.txt",
        help="Input file containing fight words (default: words.txt)",
    )
    parser.add_argument(
        "--font",
        dest="font_names",
        help="Comma-separated list of font paths or names (e.g., arial.ttf,helvetica.ttf)",
    )
    parser.add_argument(
        "--output",
        dest="output_dir",
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--negate",
        action="store_true",
        help="Reverse colors (white text on black background)",
    )
    parser.add_argument(
        "--distortion",
        dest="distortions",
        help="Comma-separated list of distortions to apply (shear,fisheye,perspective). Default: all",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: {args.input_file} not found!")
        sys.exit(1)

    # Parse distortions
    allowed_distortions = None
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

    generator = FightWordGenerator(
        font_names=font_names, negate=args.negate, distortions=allowed_distortions
    )
    generator.process_word_list(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
