from pathlib import Path
from PIL import Image


def create_thumbnail(
    file_name: str, out_path: str, size: tuple[int, int] = (300, 300)
) -> None:
    """
    Creates a thumbnail of the image to display in a carousel.
    This will store the result in the 'uploads/thumbnails/' directory
    """
    with Image.open(file_name) as img:
        img.thumbnail(size=size)
        out_put = out_path + file_name + ".thumbnail"
        img.save(out_put, "jpeg")
