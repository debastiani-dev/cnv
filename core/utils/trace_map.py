import sys

from PIL import Image, UnidentifiedImageError


def find_start_point(img, width, height, threshold=128):
    """Finds the first dark pixel to start tracing."""
    for r in range(height):
        for c in range(width):
            # Check pixel (c, r)
            if img.getpixel((c, r)) < threshold:
                return r, c
    return None


def get_next_point(curr, backtrack, img, height, width, dr, dc, threshold=128):
    """Scans neighbors to find the next boundary point."""
    # dr, dc are directions: N, NE, E, SE, S, SW, W, NW
    # Indices: 0..7
    # Check 8 neighbors
    for i in range(8):
        idx = (backtrack + 1 + i) % 8
        nr, nc = curr[0] + dr[idx], curr[1] + dc[idx]

        # Check bounds
        if 0 <= nr < height and 0 <= nc < width:
            pixel_val = img.getpixel((nc, nr))
            if pixel_val < threshold:
                # Found next pixel
                # New backtrack direction
                # Move was 'idx'. Standard Moore uses (idx + 4) % 8 as "coming from"
                new_backtrack = (idx + 4) % 8
                return (nr, nc), new_backtrack

    return None, backtrack


def trace_boundary_points(img, start, width, height):
    """Traces the boundary using Moore-Neighbor tracing."""
    boundary = []
    curr = start
    boundary.append(curr)

    # Directions: N, NE, E, SE, S, SW, W, NW
    # (row_change, col_change) -> (y, x)
    dr = [-1, -1, 0, 1, 1, 1, 0, -1]
    dc = [0, 1, 1, 1, 0, -1, -1, -1]

    # Initial backtrack direction (assuming we came from West/Left)
    backtrack = 7  # Start looking at NW? Heuristic from original code

    # Loop limit to prevent infinite loops
    max_steps = 5000

    for _ in range(max_steps):
        next_p, new_backtrack = get_next_point(
            curr, backtrack, img, height, width, dr, dc
        )
        if next_p:
            boundary.append(next_p)
            curr = next_p
            backtrack = new_backtrack

            # Stop if we returned to start with enough points
            if curr == start and len(boundary) > 5:
                break
        else:
            # No next point found (isolated pixel?)
            break

    return boundary


def print_svg_path(points):
    """Simplifies and prints the SVG path string."""
    # Simplify path: take every Nth point
    step = 3
    simplified = points[::step]
    if simplified and simplified[-1] != points[0]:
        simplified.append(points[0])

    # Construct SVG String
    path_data = ["M"]
    for r, c in simplified:
        path_data.append(f"{c},{r}")

    # Join with spaces, but manage the 'M'
    # "M10,10 20,20 ..."
    svg_d = f"M{simplified[0][1]},{simplified[0][0]} "

    # Process rest
    coords = [f"{c},{r}" for r, c in simplified[1:]]
    svg_d += " ".join(coords)
    svg_d += " Z"

    print(f"PATH_START: {svg_d} :PATH_END")


def trace_contour(image_path, output_width=300):
    """Main function to process image and trace contour."""
    try:
        img = Image.open(image_path).convert("L")
    except (FileNotFoundError, UnidentifiedImageError) as e:
        print(f"Error loading image: {e}")
        return

    # Resize
    w, h = img.size
    if w == 0:
        return
    ratio = output_width / w
    new_h = int(h * ratio)
    img = img.resize((output_width, new_h), Image.Resampling.NEAREST)

    # Get dims of resized
    width, height = img.size  # PIL size is (width, height)

    start = find_start_point(img, width, height)

    if not start:
        print("Error: No shape found")
        return

    boundary = trace_boundary_points(img, start, width, height)

    if not boundary:
        # Should not happen if start found, but good check
        print("Error: Could not trace boundary")
        return

    print_svg_path(boundary)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        trace_contour(sys.argv[1])
