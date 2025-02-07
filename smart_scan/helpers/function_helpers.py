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


