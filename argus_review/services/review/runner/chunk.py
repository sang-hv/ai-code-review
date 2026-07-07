def _chunk(files: list[str], size: int) -> list[list[str]]:
    """
    Split `files` into chunks of at most `size` files each.

    `size <= 0` (or a size that already covers every file) disables chunking:
    a single chunk containing all files is returned, preserving the previous
    single-session behavior.
    """
    if size <= 0 or len(files) <= size:
        return [files]

    return [files[i:i + size] for i in range(0, len(files), size)]
