import hashlib
import json
from typing import Any

import numpy as np


def normalize_tilewise_vectorized(arr: np.ndarray, tile_size: int) -> np.ndarray:
    """
    Normalize a 2D NumPy array tile-wise to the range [0, 1].

    The function divides the array into non-overlapping tiles of the specified size,
    normalizes each tile independently to the range [0, 1], and recombines them
    into the original array structure.

    Parameters
    ----------
    arr : np.ndarray
        A 2D NumPy array to be normalized. The array should have numeric values.
    tile_size : int
        The size of each square tile. Both dimensions of the array must be divisible
        by this value.

    Returns
    -------
    np.ndarray
        A 2D NumPy array of the same shape as `arr`, where each tile is normalized
        independently to the range [0, 1].

    Raises
    ------
    AssertionError
        If the dimensions of `arr` are not divisible by `tile_size`.

    Notes
    -----
    - Normalization for each tile is performed as:
        normalized_tile = (tile - tile_min) / (tile_max - tile_min)
      where `tile_min` and `tile_max` are the minimum and maximum values within the tile
    - If `tile_min` equals `tile_max` for a tile (e.g., when all elements in the tile
      are identical), the corresponding tile in the output will be set to 0 to avoid
      division by zero.
    - The function assumes no overlap between tiles.
    """
    # Get the array shape
    rows, cols = arr.shape

    # Ensure the dimensions are divisible by the tile size
    assert (
        rows % tile_size == 0 and cols % tile_size == 0
    ), "Array dimensions must be divisible by the tile size."

    # Reshape the array into tiles: (num_tiles_y, tile_size,
    #                                num_tiles_x, tile_size)
    shape = (rows // tile_size, tile_size, cols // tile_size, tile_size)
    reshaped = arr.reshape(*shape)

    # Move the tile axes together for simpler broadcasting:
    #  (num_tiles_y, num_tiles_x, tile_size, tile_size)
    tiles = reshaped.transpose(0, 2, 1, 3)

    # Compute min and max for each tile
    tile_min = tiles.min(axis=(2, 3), keepdims=True)
    tile_max = tiles.max(axis=(2, 3), keepdims=True)

    # Avoid division by zero: normalize only where max > min
    normalized_tiles = np.where(
        tile_max > tile_min, (tiles - tile_min) / (tile_max - tile_min), 0
    )

    # Reshape back to the original array shape
    normalized_array = normalized_tiles.transpose(0, 2, 1, 3).reshape(rows, cols)

    return normalized_array


def dicts_equal(dict1: dict, dict2: dict) -> bool:
    """Compare dictionaries by serializing them to JSON."""
    try:
        return json.dumps(dict1, sort_keys=True) == json.dumps(dict2, sort_keys=True)
    except TypeError:
        # If the dictionaries contain non-serializable objects (like NumPy arrays)
        # we need a different approach
        pass

    # For dictionaries with NumPy arrays, we can use a specialized approach
    import numpy as np

    # Convert NumPy arrays to lists before serializing
    def convert_numpy(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(item) for item in obj]
        return obj

    dict1_converted = convert_numpy(dict1)
    dict2_converted = convert_numpy(dict2)

    return json.dumps(dict1_converted, sort_keys=True) == json.dumps(
        dict2_converted, sort_keys=True
    )


def hash_dict(d: dict) -> str:
    """Generate a hash for a dictionary, including NumPy arrays."""
    d_copy = d.copy()

    # Convert any NumPy arrays to a hashable representation
    for key, value in d_copy.items():
        if isinstance(value, np.ndarray):
            d_copy[key] = (value.tobytes(), value.shape, value.dtype.str)

    sorted_items = sorted(d_copy.items())
    dict_str = json.dumps(sorted_items, sort_keys=True, default=str)
    return hashlib.md5(dict_str.encode()).hexdigest()
