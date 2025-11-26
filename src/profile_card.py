"""Profile card image generation for instagram_monitor."""

import os

try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# --- Layout Configuration ---
WIDTH, HEIGHT = 900, 340
PROFILE_PIC_SIZE = 200
PROFILE_PIC_MARGIN_LEFT = 50
PROFILE_PIC_Y_CENTER = HEIGHT // 2
RING_THICKNESS = 8
RING_GAP_THICKNESS = 4
TEXT_AREA_LEFT_MARGIN = PROFILE_PIC_MARGIN_LEFT + PROFILE_PIC_SIZE + 90  # +10px more space from photo
VERIFIED_BADGE_SIZE = 22
VERIFIED_BADGE_PNG = "assets/check-big.png"
WATERMARK_PNG = "assets/instagram-red.png"
WATERMARK_SIZE = 250
WATERMARK_ROTATION = -10
WATERMARK_MARGIN_RIGHT = -125  # Negative to cut off half
WATERMARK_MARGIN_BOTTOM = -125
WATERMARK_OPACITY = 1.0

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (142, 142, 142)
VERIFIED_BLUE = (56, 151, 240)
INSTAGRAM_GRADIENT_COLORS = [
    (253, 184, 51),   # Yellow
    (252, 128, 55),   # Orange
    (221, 42, 123),   # Pink
    (131, 58, 180),   # Purple
    (74, 114, 219),   # Blue
    (253, 184, 51),   # Back to yellow (cycle)
]

# --- Font Paths ---
FONT_MONO_PATHS = [
    "/System/Library/Fonts/SFMono.ttf",
    "/Library/Fonts/SF-Mono-Regular.otf",
    "/System/Library/Fonts/Monaco.ttf",  # Fallback monospace (macOS)
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux fallback
    "src/fonts/RobotoMono-Regular.ttf",
]
FONT_BOLD_PATHS = [
    "/System/Library/Fonts/HelveticaNeue.ttc",  # Helvetica Neue (macOS)
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "src/fonts/Roboto-Bold.ttf",
]
FONT_REGULAR_PATHS = [
    "/System/Library/Fonts/HelveticaNeue.ttc",  # Helvetica Neue (macOS)
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "src/fonts/Roboto-Regular.ttf",
]

# Text supersampling scale for anti-aliasing
TEXT_SUPERSAMPLE = 2


def format_count(n):
    """Format number Instagram-style (1.2M, 456K, etc.)."""
    if not isinstance(n, int):
        return str(n)
    if n >= 1_000_000:
        formatted = f"{n / 1_000_000:.1f}M"
        return formatted.replace(".0M", "M")
    elif n >= 10_000:
        return f"{n // 1000}K"
    elif n >= 1_000:
        formatted = f"{n / 1_000:.1f}K"
        return formatted.replace(".0K", "K")
    return str(n)


def get_font(font_paths, size, index=0):
    """Load font from list of paths with fallbacks."""
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except (OSError, IOError):
                continue
    # Final fallback to PIL default
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def draw_text_antialiased(base_image, position, text, font_paths, font_size, fill, scale=2, font_index=0):
    """Draw anti-aliased text using supersampling."""
    # Load font at higher resolution
    hi_font = get_font(font_paths, font_size * scale, index=font_index)

    # Create temporary image to measure text
    temp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=hi_font)
    text_width = bbox[2] - bbox[0] + 4
    text_height = bbox[3] - bbox[1] + 4

    # Create high-res image for text
    hi_res_img = Image.new("RGBA", (text_width, text_height), (255, 255, 255, 0))
    hi_res_draw = ImageDraw.Draw(hi_res_img)

    # Draw text at high resolution
    hi_res_draw.text((2, 2 - bbox[1]), text, font=hi_font, fill=fill + (255,) if len(fill) == 3 else fill)

    # Downsample for anti-aliasing
    final_width = text_width // scale
    final_height = text_height // scale
    final_img = hi_res_img.resize((final_width, final_height), Image.Resampling.LANCZOS)

    # Paste onto base image
    base_image.paste(final_img, (int(position[0]), int(position[1])), final_img)

    return final_width, final_height


def interpolate_color(t, colors):
    """Interpolate color in a list based on factor t (0.0 to 1.0)."""
    num_colors = len(colors)
    if num_colors == 0:
        return (0, 0, 0)
    if num_colors == 1:
        return colors[0]

    segment_length = 1.0 / (num_colors - 1)
    segment_index = int(t / segment_length)
    if segment_index >= num_colors - 1:
        return colors[-1]

    local_t = (t - segment_index * segment_length) / segment_length
    c1 = colors[segment_index]
    c2 = colors[segment_index + 1]

    r = int(c1[0] * (1 - local_t) + c2[0] * local_t)
    g = int(c1[1] * (1 - local_t) + c2[1] * local_t)
    b = int(c1[2] * (1 - local_t) + c2[2] * local_t)
    return (r, g, b)


def draw_circular_profile_pic(
    base_image,
    draw_context,
    img_path,
    center_x,
    center_y,
    size,
    gradient_colors,
    ring_thickness,
    gap_thickness,
    supersample=4,
):
    """Draw circular profile picture with gradient story ring and anti-aliasing."""
    outer_radius = size // 2
    ring_outer_radius = outer_radius + ring_thickness + gap_thickness
    total_size = ring_outer_radius * 2 + 4  # Add small padding

    # Create high-resolution image for anti-aliasing
    scale = supersample
    hi_res_size = total_size * scale
    hi_res_img = Image.new("RGBA", (hi_res_size, hi_res_size), (255, 255, 255, 0))
    hi_res_draw = ImageDraw.Draw(hi_res_img)

    hi_center = hi_res_size // 2
    hi_ring_outer = ring_outer_radius * scale
    hi_ring_thickness = ring_thickness * scale
    hi_gap_radius = (outer_radius + gap_thickness) * scale
    hi_outer_radius = outer_radius * scale

    # 1. Draw Story Ring at high resolution
    ring_bbox = (
        hi_center - hi_ring_outer,
        hi_center - hi_ring_outer,
        hi_center + hi_ring_outer,
        hi_center + hi_ring_outer,
    )

    # Draw gradient ring using arc segments
    segments = 720  # More segments for smoother gradient
    for i in range(segments):
        start_angle = i * 360 / segments
        end_angle = (i + 1) * 360 / segments
        t = i / segments
        current_color = interpolate_color(t, gradient_colors)
        hi_res_draw.arc(ring_bbox, start_angle, end_angle, fill=current_color, width=hi_ring_thickness)

    # 2. Draw white gap circle at high resolution
    gap_bbox = (
        hi_center - hi_gap_radius,
        hi_center - hi_gap_radius,
        hi_center + hi_gap_radius,
        hi_center + hi_gap_radius,
    )
    hi_res_draw.ellipse(gap_bbox, fill=(255, 255, 255, 255))

    # 3. Load and prepare profile picture at high resolution
    hi_pic_size = size * scale
    if img_path and os.path.exists(img_path):
        try:
            profile_img = Image.open(img_path).convert("RGBA")
        except Exception:
            profile_img = Image.new("RGBA", (hi_pic_size, hi_pic_size), (150, 150, 150, 255))
    else:
        profile_img = Image.new("RGBA", (hi_pic_size, hi_pic_size), (150, 150, 150, 255))

    profile_img_resized = profile_img.resize((hi_pic_size, hi_pic_size), Image.Resampling.LANCZOS)

    # Create circular mask at high resolution for smooth edges
    mask = Image.new("L", (hi_pic_size, hi_pic_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, hi_pic_size, hi_pic_size), fill=255)

    # Apply mask to create circular profile picture
    circular_pic = Image.new("RGBA", (hi_pic_size, hi_pic_size), (0, 0, 0, 0))
    circular_pic.paste(profile_img_resized, (0, 0), mask)

    # Paste profile picture onto high-res ring image
    pic_paste_x = hi_center - hi_outer_radius
    pic_paste_y = hi_center - hi_outer_radius
    hi_res_img.paste(circular_pic, (pic_paste_x, pic_paste_y), circular_pic)

    # 4. Downsample for anti-aliasing
    final_img = hi_res_img.resize((total_size, total_size), Image.Resampling.LANCZOS)

    # 5. Paste onto base image
    paste_x = center_x - total_size // 2
    paste_y = center_y - total_size // 2
    base_image.paste(final_img, (paste_x, paste_y), final_img)


def load_verified_badge(size):
    """Load verified badge PNG and resize to target size."""
    badge_path = os.path.join(os.path.dirname(__file__), "..", VERIFIED_BADGE_PNG)
    if os.path.exists(badge_path):
        try:
            badge = Image.open(badge_path).convert("RGBA")
            return badge.resize((size, size), Image.Resampling.LANCZOS)
        except Exception:
            pass
    return None


def draw_verified_badge(draw, x, y, size):
    """Draw Instagram verified badge (blue circle with white checkmark). Fallback if PNG unavailable."""
    draw.ellipse((x, y, x + size, y + size), fill=VERIFIED_BLUE)

    # Draw white checkmark using two line segments
    checkmark_coords = [
        (x + size * 0.2, y + size * 0.5),
        (x + size * 0.45, y + size * 0.7),
        (x + size * 0.8, y + size * 0.3),
    ]

    line_width = max(2, int(size * 0.12))
    draw.line([checkmark_coords[0], checkmark_coords[1]], fill=WHITE, width=line_width)
    draw.line([checkmark_coords[1], checkmark_coords[2]], fill=WHITE, width=line_width)


def draw_watermark(base_image, watermark_path, size, rotation, margin_right, margin_bottom, opacity=0.15):
    """Draw rotated watermark in bottom-right corner with transparency."""
    if not os.path.exists(watermark_path):
        return

    try:
        watermark = Image.open(watermark_path).convert("RGBA")
        watermark = watermark.resize((size, size), Image.Resampling.LANCZOS)

        # Rotate watermark
        watermark = watermark.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)

        # Apply opacity
        alpha = watermark.split()[3]
        alpha = alpha.point(lambda x: int(x * opacity))
        watermark.putalpha(alpha)

        # Calculate position (bottom-right)
        x = base_image.width - watermark.width - margin_right
        y = base_image.height - watermark.height - margin_bottom

        base_image.paste(watermark, (x, y), watermark)
    except Exception:
        pass


def generate_profile_card(
    username,
    display_name,
    followers,
    following,
    profile_pic_path,
    output_path,
    category="",
):
    """Generate an Instagram-style profile card image.

    Args:
        username: Instagram username
        display_name: User's display name (full name)
        followers: Follower count
        following: Following count
        profile_pic_path: Path to profile picture file
        output_path: Path to save the generated card
        category: Optional category label (e.g., 'Artist', 'Musician')

    Returns:
        Output path on success, None on failure.
    """
    if not PIL_AVAILABLE:
        print("* Warning: PIL/Pillow not available, cannot generate profile card")
        return None

    # Create canvas as RGBA for compositing anti-aliased text
    img = Image.new("RGBA", (WIDTH, HEIGHT), WHITE + (255,))
    draw = ImageDraw.Draw(img)

    # Font sizes (refined hierarchy)
    size_username = 36      # +12% larger, clear visual anchor
    size_stats_num = 16     # -10% smaller than handle
    size_stats_label = 16   # Match stats numbers
    size_name = 24          # +8% larger than stats, secondary to handle
    size_category = 14      # -12% smaller than name

    # Font indices for Helvetica Neue .ttc: 0 = Regular, 1 = Bold, 4 = Medium
    bold_index = 1
    medium_index = 4        # Medium weight for stats numbers
    regular_index = 0

    # Load fonts for measuring (at display size)
    font_username = get_font(FONT_MONO_PATHS, size_username, index=0)
    font_stats_num = get_font(FONT_BOLD_PATHS, size_stats_num, index=bold_index)
    font_stats_label = get_font(FONT_REGULAR_PATHS, size_stats_label, index=regular_index)
    font_name = get_font(FONT_BOLD_PATHS, size_name, index=bold_index)
    font_category = get_font(FONT_REGULAR_PATHS, size_category, index=regular_index)

    # Draw profile picture with gradient ring
    pic_center_x = PROFILE_PIC_MARGIN_LEFT + (PROFILE_PIC_SIZE // 2) + RING_THICKNESS + RING_GAP_THICKNESS
    pic_center_y = PROFILE_PIC_Y_CENTER

    draw_circular_profile_pic(
        img,
        draw,
        profile_pic_path,
        pic_center_x,
        pic_center_y,
        PROFILE_PIC_SIZE,
        INSTAGRAM_GRADIENT_COLORS,
        RING_THICKNESS,
        RING_GAP_THICKNESS,
    )

    # Calculate text positions for vertical centering
    # Get text heights
    username_bbox = draw.textbbox((0, 0), username, font=font_username)
    username_h = username_bbox[3] - username_bbox[1]

    stats_text = f"{format_count(followers)} followers   {format_count(following)} following"
    stats_bbox = draw.textbbox((0, 0), stats_text, font=font_stats_label)
    stats_h = stats_bbox[3] - stats_bbox[1]

    name_h = 0
    if display_name:
        name_bbox = draw.textbbox((0, 0), display_name, font=font_name)
        name_h = name_bbox[3] - name_bbox[1]

    category_h = 0
    if category:
        category_bbox = draw.textbbox((0, 0), category, font=font_category)
        category_h = category_bbox[3] - category_bbox[1]

    # Gaps between lines (tight vertical rhythm)
    gap1 = 12  # Handle → Stats: spacing below username/badge row
    gap2 = 9   # Stats → Name: 8-10px
    gap3 = 5   # Name → Category: 4-6px

    # Calculate total text block height
    total_height = username_h + gap1 + stats_h
    if display_name:
        total_height += gap2 + name_h
    if category:
        total_height += gap3 + category_h

    # Calculate starting Y to vertically center text block
    current_y = (HEIGHT - total_height) // 2
    text_x = TEXT_AREA_LEFT_MARGIN

    # Draw username (anti-aliased, SF Mono font)
    username_width, _ = draw_text_antialiased(
        img, (text_x, current_y), username,
        FONT_MONO_PATHS, size_username, BLACK,
        scale=TEXT_SUPERSAMPLE, font_index=0
    )

    # Draw verified badge next to username (6px margin)
    badge_x = text_x + username_width + 6
    badge_y = current_y + (username_h - VERIFIED_BADGE_SIZE) // 2
    badge_img = load_verified_badge(VERIFIED_BADGE_SIZE)
    if badge_img:
        img.paste(badge_img, (int(badge_x), int(badge_y)), badge_img)
    else:
        draw_verified_badge(draw, badge_x, badge_y, VERIFIED_BADGE_SIZE)

    # Draw stats
    current_y += username_h + gap1

    followers_formatted = format_count(followers)
    following_formatted = format_count(following)

    # Followers count (medium weight, anti-aliased)
    followers_width, _ = draw_text_antialiased(
        img, (text_x, current_y), followers_formatted,
        FONT_BOLD_PATHS, size_stats_num, BLACK,
        scale=TEXT_SUPERSAMPLE, font_index=medium_index
    )

    # "followers" label (anti-aliased)
    followers_label_width, _ = draw_text_antialiased(
        img, (text_x + followers_width + 4, current_y), "followers",
        FONT_REGULAR_PATHS, size_stats_label, GREY,
        scale=TEXT_SUPERSAMPLE, font_index=regular_index
    )

    # Following count (medium weight, anti-aliased) - 14px gap for consistent spacing
    following_x = text_x + followers_width + 4 + followers_label_width + 14
    following_width, _ = draw_text_antialiased(
        img, (following_x, current_y), following_formatted,
        FONT_BOLD_PATHS, size_stats_num, BLACK,
        scale=TEXT_SUPERSAMPLE, font_index=medium_index
    )

    # "following" label (anti-aliased)
    draw_text_antialiased(
        img, (following_x + following_width + 4, current_y), "following",
        FONT_REGULAR_PATHS, size_stats_label, GREY,
        scale=TEXT_SUPERSAMPLE, font_index=regular_index
    )

    # Draw full name (anti-aliased)
    if display_name:
        current_y += stats_h + gap2
        draw_text_antialiased(
            img, (text_x, current_y), display_name,
            FONT_BOLD_PATHS, size_name, BLACK,
            scale=TEXT_SUPERSAMPLE, font_index=bold_index
        )

    # Draw category (anti-aliased)
    if category:
        current_y += (name_h if display_name else stats_h) + gap3
        draw_text_antialiased(
            img, (text_x, current_y), category,
            FONT_REGULAR_PATHS, size_category, GREY,
            scale=TEXT_SUPERSAMPLE, font_index=regular_index
        )

    # Draw watermark in bottom-right corner
    watermark_path = os.path.join(os.path.dirname(__file__), "..", WATERMARK_PNG)
    draw_watermark(img, watermark_path, WATERMARK_SIZE, WATERMARK_ROTATION,
                   WATERMARK_MARGIN_RIGHT, WATERMARK_MARGIN_BOTTOM, WATERMARK_OPACITY)

    # Convert to RGB and save
    rgb_img = Image.new("RGB", img.size, WHITE)
    rgb_img.paste(img, mask=img.split()[3])
    rgb_img.save(output_path, "JPEG", quality=95)
    return output_path
