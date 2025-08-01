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
import glob
from PIL import ImageFilter


class FightWordGenerator:
    def __init__(self, width=128, height=64, seed=None, font_name=None, negate=False):
        self.width = width
        self.height = height
        self.font_name = font_name
        self.negate = negate
        if seed is not None:
            random.seed(seed)  # For reproducible results in testing

    def floyd_steinberg_dither(self, image):
        """Apply Floyd-Steinberg dithering to convert grayscale to pure B&W"""
        img = image.convert("L")  # Convert to grayscale
        pixels = img.load()
        width, height = img.size

        for y in range(height):
            for x in range(width):
                old_pixel = pixels[x, y]
                new_pixel = 255 if old_pixel > 127 else 0
                pixels[x, y] = new_pixel

                error = old_pixel - new_pixel

                # Distribute error to neighboring pixels
                if x + 1 < width:
                    pixels[x + 1, y] = max(
                        0, min(255, pixels[x + 1, y] + error * 7 // 16)
                    )
                if x > 0 and y + 1 < height:
                    pixels[x - 1, y + 1] = max(
                        0, min(255, pixels[x - 1, y + 1] + error * 3 // 16)
                    )
                if y + 1 < height:
                    pixels[x, y + 1] = max(
                        0, min(255, pixels[x, y + 1] + error * 5 // 16)
                    )
                if x + 1 < width and y + 1 < height:
                    pixels[x + 1, y + 1] = max(
                        0, min(255, pixels[x + 1, y + 1] + error * 1 // 16)
                    )

        return img.convert("1")  # Convert to pure B&W

    def create_starburst_background(self, draw, cx, cy, inner_radius, outer_radius):
        """Create randomized starburst background with varying points and irregularity"""
        points = random.randint(12, 20)  # Variable number of points
        angle_step = 2 * math.pi / points

        for i in range(points):
            angle1 = i * angle_step + random.uniform(-0.1, 0.1)  # Slight angle variation
            
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
        """Find font file by name in common system locations"""
        # Common font directories
        font_dirs = [
            "/usr/share/fonts/",
            "/usr/local/share/fonts/",
            "/System/Library/Fonts/",  # macOS
            "C:/Windows/Fonts/",       # Windows
            os.path.expanduser("~/.fonts/"),
            os.path.expanduser("~/.local/share/fonts/"),
        ]
        
        # Clean font name for filename matching
        clean_name = font_name.replace(" ", "").lower()
        name_variants = [
            font_name,
            font_name.replace(" ", ""),
            font_name.replace(" ", "-"),
            font_name.replace(" ", "_"),
            clean_name,
        ]
        
        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue
                
            # Search recursively in font directory
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                        file_lower = file.lower()
                        file_base = os.path.splitext(file)[0].lower()
                        
                        # Check if any variant matches
                        for variant in name_variants:
                            if (variant.lower() in file_lower or 
                                variant.lower() in file_base or
                                file_base in variant.lower()):
                                return os.path.join(root, file)
        
        return None

    def _load_font(self, font_size):
        """Load font with specified size, trying custom font first if provided"""
        if self.font_name:
            # First try as direct path
            if os.path.exists(self.font_name):
                try:
                    font = ImageFont.truetype(self.font_name, font_size)
                    return font
                except (OSError, IOError):
                    pass
            
            # Try to find by name
            font_path = self._find_font_file(self.font_name)
            if font_path:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    return font
                except (OSError, IOError):
                    pass
            
            print(f"Warning: Could not load font '{self.font_name}', falling back to default")
        
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
        # Create larger canvas for rotation
        canvas_size = max(self.width, self.height) * 2
        temp_img = Image.new("L", (canvas_size, canvas_size), 255)
        draw = ImageDraw.Draw(temp_img)

        # Calculate center of temp canvas
        temp_cx, temp_cy = canvas_size // 2, canvas_size // 2

        # Create starburst background on temp canvas
        self.create_starburst_background(draw, temp_cx, temp_cy, 20, canvas_size // 4)

        # Load font with dynamic sizing that ensures text fits
        font_size = self.get_font_size(word, self.width - 20, self.height - 20)
        font = self._load_font(font_size)
        
        # Check if text fits and adjust if needed
        bbox = draw.textbbox((0, 0), word, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # If text is too big for final output, scale down font
        max_attempts = 5
        while (text_width > self.width - 10 or text_height > self.height - 10) and max_attempts > 0:
            font_size = int(font_size * 0.85)  # Reduce by 15%
            font = self._load_font(font_size)
            bbox = draw.textbbox((0, 0), word, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            max_attempts -= 1

        # Center the text on temp canvas
        text_x = (canvas_size - text_width) // 2
        text_y = (canvas_size - text_height) // 2

        # Add smaller random position offset that won't push text off screen
        max_offset_x = min(10, (self.width - text_width) // 4)
        max_offset_y = min(8, (self.height - text_height) // 4)
        offset_x = random.randint(-max_offset_x, max_offset_x)
        offset_y = random.randint(-max_offset_y, max_offset_y)
        text_x += offset_x
        text_y += offset_y

        # Draw text with outline on temp canvas
        self.draw_text_with_outline(draw, word, text_x, text_y, font, outline_width=2)

        # Apply random rotation (-15 to +15 degrees)
        rotation_angle = random.uniform(-15, 15)
        rotated_img = temp_img.rotate(rotation_angle, expand=False, fillcolor=255)

        # Crop back to original size from center
        left = (canvas_size - self.width) // 2
        top = (canvas_size - self.height) // 2
        right = left + self.width
        bottom = top + self.height
        final_img = rotated_img.crop((left, top, right, bottom))

        # Apply random distortion - always apply some form of distortion
        distortion_type = random.choice(['shear', 'fisheye', 'perspective'])
        
        if distortion_type == 'shear':
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
            
        elif distortion_type == 'fisheye':
            # Fish-eye lens distortion - bulges center and compresses edges
            width, height = final_img.size
            distorted = Image.new("L", (width, height), 255)
            
            # Random center point (not always dead center)
            center_x = width // 2 + random.randint(-width//6, width//6)
            center_y = height // 2 + random.randint(-height//6, height//6)
            
            # Random strength and radius
            strength = random.uniform(0.3, 0.8)  # Bulge strength
            max_radius = min(width, height) * 0.6  # Effective radius
            
            for y in range(height):
                for x in range(width):
                    # Distance from center
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    
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
            
        else:  # perspective
            # Perspective-like distortion by stretching corners
            stretch_factor = random.uniform(0.05, 0.15)
            corner = random.choice(['top', 'bottom', 'left', 'right'])
            
            width, height = final_img.size
            distorted = Image.new("L", (width, height), 255)
            
            for y in range(height):
                for x in range(width):
                    if corner == 'top':
                        factor = 1 + stretch_factor * (1 - y / height)
                        src_x = int(x / factor + (width * (factor - 1)) / (2 * factor))
                    elif corner == 'bottom':
                        factor = 1 + stretch_factor * (y / height)
                        src_x = int(x / factor + (width * (factor - 1)) / (2 * factor))
                    elif corner == 'left':
                        factor = 1 + stretch_factor * (1 - x / width)
                        src_y = int(y / factor + (height * (factor - 1)) / (2 * factor))
                        src_x = x
                    else:  # right
                        factor = 1 + stretch_factor * (x / width)
                        src_y = int(y / factor + (height * (factor - 1)) / (2 * factor))
                        src_x = x
                    
                    if corner in ['top', 'bottom']:
                        src_y = y
                    
                    if 0 <= src_x < width and 0 <= src_y < height:
                        pixel = final_img.getpixel((src_x, src_y))
                        distorted.putpixel((x, y), pixel)
            
            final_img = distorted

        # Apply Floyd-Steinberg dithering
        dithered_img = self.floyd_steinberg_dither(final_img)
        
        # Apply color negation if requested
        if self.negate:
            # Invert the image (0 becomes 255, 255 becomes 0)
            from PIL import ImageOps
            dithered_img = ImageOps.invert(dithered_img.convert('L')).convert('1')

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
            filename = f"{i:02d}_{word.replace('!', '').replace('-', '_').replace(' ', '_')}.png"
            output_path = os.path.join(output_dir, filename)

            print(f"Generating {filename}...")
            self.generate_fight_word(word, output_path)

        print(f"Done! Generated {len([w for w in words if w])} images in {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Generate Batman-style fight word images")
    parser.add_argument("input_file", nargs="?", default="words.txt", 
                        help="Input file containing fight words (default: words.txt)")
    parser.add_argument("--font", dest="font_name", 
                        help="Path to custom font file (e.g., /path/to/font.ttf)")
    parser.add_argument("--output", dest="output_dir", default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--negate", action="store_true",
                        help="Reverse colors (white text on black background)")
    
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: {args.input_file} not found!")
        sys.exit(1)

    generator = FightWordGenerator(font_name=args.font_name, negate=args.negate)
    generator.process_word_list(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
