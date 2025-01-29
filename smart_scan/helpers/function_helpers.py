import numpy as np
import ctypes
from ctypes import *
import sys
from smart_scan.dependencies.dwfconstants import *
from enum import IntEnum
import time


class ScanningStragies(IntEnum):
    RASTER = 0
    SNAKE = 1


def mask2active_pixels(
    mask: np.ndarray, scan_strategy: ScanningStragies = ScanningStragies.RASTER
) -> np.ndarray:
    """Coverts a binary mask into a sequence of pixels for which the mask is true.

    Arguments:
    mask -- the binary mask, we skip 0 pixels
    """
    if scan_strategy == ScanningStragies.RASTER:
        active_pixels = np.transpose(np.nonzero(mask))

    elif scan_strategy == ScanningStragies.SNAKE:

        # generate 2 semi-masks with odd and even lines
        semi_mask_1 = np.zeros(mask.shape)
        semi_mask_2 = np.zeros(mask.shape)
        semi_mask_1[::2, :] = mask[::2, :]
        semi_mask_2[1::2, :] = mask[1::2, :]

        pix_1 = np.transpose(np.nonzero(semi_mask_1))
        pix_2 = np.transpose(np.nonzero(semi_mask_2))

        # invert all lines of semi mask 1
        pix_1 = pix_1[np.lexsort((-pix_1[:, 1], pix_1[:, 0]))]

        # concatenate the pixels and sort stably
        active_pixels = np.concatenate((pix_1, pix_2), axis=0)
        active_pixels = active_pixels[active_pixels[:, 0].argsort(kind="stable")]

    return active_pixels


def generate_mask(h: int, w: int, semidim_h: int, semidim_w: int) -> np.ndarray:
    """Generate the binary mask of shape (h,w) with different strategies."""

    # To begin with: ones in the center
    c_w = int(w / 2)
    c_h = int(h / 2)
    semidim_h = semidim_h if (semidim_w < c_w) & (semidim_w < c_h) else min(c_w, c_h)
    semidim_w = semidim_w if (semidim_w < c_w) & (semidim_w < c_h) else min(c_w, c_h)

    mask = np.zeros([h, w])
    mask[c_h - semidim_h : c_h + semidim_h, c_w - semidim_w : c_w + semidim_w] = (
        np.ones([semidim_h * 2, semidim_w * 2])
    )

    # Let's make a cross
    mask[c_h - semidim_w : c_h + semidim_w, c_w - semidim_h : c_w + semidim_h] = (
        np.ones([semidim_w * 2, semidim_h * 2])
    )

    return mask

def normalize_tilewise_vectorized(arr, tile_size):
    """
    Normalize a 2D NumPy array tile-wise to the range [0, 1].
    
    The function divides the array into non-overlapping tiles of the specified size, 
    normalizes each tile independently to the range [0, 1], and recombines them 
    into the original array structure.
    
    Parameters:
    ----------
    arr : np.ndarray
        A 2D NumPy array to be normalized. The array should have numeric values.
    tile_size : int
        The size of each square tile. Both dimensions of the array must be divisible 
        by this value.
    
    Returns:
    -------
    np.ndarray
        A 2D NumPy array of the same shape as `arr`, where each tile is normalized 
        independently to the range [0, 1].
    
    Raises:
    ------
    AssertionError
        If the dimensions of `arr` are not divisible by `tile_size`.
    
    Notes:
    ------
    - Normalization for each tile is performed as:
        normalized_tile = (tile - tile_min) / (tile_max - tile_min)
      where `tile_min` and `tile_max` are the minimum and maximum values within the tile.
    - If `tile_min` equals `tile_max` for a tile (e.g., when all elements in the tile 
      are identical), the corresponding tile in the output will be set to 0 to avoid 
      division by zero.
    - The function assumes no overlap between tiles.
    """
    
    # Get the array shape
    rows, cols = arr.shape
    
    # Ensure the dimensions are divisible by the tile size
    assert rows % tile_size == 0 and cols % tile_size == 0, \
        "Array dimensions must be divisible by the tile size."
    
    # Reshape the array into tiles: (num_tiles_y, tile_size, num_tiles_x, tile_size)
    reshaped = arr.reshape(rows // tile_size, tile_size, cols // tile_size, tile_size)
    
    # Move the tile axes together for simpler broadcasting: (num_tiles_y, num_tiles_x, tile_size, tile_size)
    tiles = reshaped.transpose(0, 2, 1, 3)
    
    # Compute min and max for each tile
    tile_min = tiles.min(axis=(2, 3), keepdims=True)
    tile_max = tiles.max(axis=(2, 3), keepdims=True)
    
    # Avoid division by zero: normalize only where max > min
    normalized_tiles = np.where(
        tile_max > tile_min,
        (tiles - tile_min) / (tile_max - tile_min),
        0
    )
    
    # Reshape back to the original array shape
    normalized_array = normalized_tiles.transpose(0, 2, 1, 3).reshape(rows, cols)
    
    return normalized_array
