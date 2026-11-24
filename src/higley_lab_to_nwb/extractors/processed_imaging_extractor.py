from pathlib import Path
from typing import Literal

import h5py
import numpy as np
from roiextractors.imagingextractor import ImagingExtractor

DUAL_IMAGING_PROCESS_TYPES = ("dff_final", "dff_blue", "dff_uv")
ONE_PHOTON_PROCESS_TYPES = ("blue", "uv", "green")


class ProcessedImagingExtractor(ImagingExtractor):
    """Processed (DF/F) imaging data saved by the lab's MATLAB code as a pixels matrix.

    The .mat file holds one row per frame and one column per pixel. The lab's code saves the pixels of the frame
    rotated by 180 degrees, so frame pixel (r, c) is column (n_rows - 1 - r) * n_cols + (n_cols - 1 - c), counting
    only the pixels inside the mask when the file has one ("dff_final", "dff_blue", "dff_uv"). Pixels outside the
    mask and pixels the lab's output leaves as NaN are returned as NaN. Frames are read from the file on request.
    """

    extractor_name = "ProcessedImagingExtractor"

    def __init__(
        self,
        file_path: str | Path,
        sampling_frequency: float,
        process_type: Literal["dff_final", "dff_blue", "dff_uv", "blue", "uv", "green"],
    ) -> None:
        """
        Parameters
        ----------
        file_path : str or Path
            Path to the MATLAB (v7.3) file.
        sampling_frequency : float
            The frame rate, in Hz.
        process_type : str
            The variable to read: "dff_final", "dff_blue" or "dff_uv" (a pixels matrix and a "mask"), or "blue",
            "uv" or "green" (fields of "dFoF", with the frame size in "R" and "C").
        """
        accepted_process_types = DUAL_IMAGING_PROCESS_TYPES + ONE_PHOTON_PROCESS_TYPES
        if process_type not in accepted_process_types:
            raise ValueError(f"process_type '{process_type}' must be one of {accepted_process_types}.")

        super().__init__()
        self.file_path = Path(file_path)
        self.process_type = process_type
        self._sampling_frequency = sampling_frequency

        with h5py.File(self.file_path, "r") as file:
            dataset = self._get_dataset(file)
            self._num_samples, number_of_pixels = dataset.shape
            if process_type in DUAL_IMAGING_PROCESS_TYPES:
                mask = file["mask"][:]
                self._num_rows, self._num_columns = mask.shape
            else:
                mask = None
                self._num_rows = int(file["R"][()].item())
                self._num_columns = int(file["C"][()].item())

        if number_of_pixels == self._num_rows * self._num_columns:
            flipped_mask = np.ones((self._num_rows, self._num_columns), dtype=bool)
        elif mask is not None and number_of_pixels == np.count_nonzero(mask):
            flipped_mask = mask[::-1, ::-1] != 0
        else:
            raise ValueError(
                f"Can't reconstruct the frames of {self.file_path}: it has {number_of_pixels} pixels per frame, which "
                f"is neither the frame size {self._num_rows} x {self._num_columns} nor the number of pixels in its mask."
            )
        # Row and column, in the 180-degree rotated frame, of each column of the pixels matrix (row-major order)
        self._flipped_rows, self._flipped_columns = np.nonzero(flipped_mask)

    def _get_dataset(self, file: h5py.File) -> h5py.Dataset:
        if self.process_type in DUAL_IMAGING_PROCESS_TYPES:
            return file[self.process_type]
        return file["dFoF"][self.process_type]

    def get_series(self, start_sample: int | None = None, end_sample: int | None = None) -> np.ndarray:
        start_sample = 0 if start_sample is None else start_sample
        end_sample = self._num_samples if end_sample is None else end_sample
        with h5py.File(self.file_path, "r") as file:
            pixels = self._get_dataset(file)[start_sample:end_sample].astype("float32")

        flipped_series = np.full((pixels.shape[0], self._num_rows, self._num_columns), np.nan, dtype="float32")
        flipped_series[:, self._flipped_rows, self._flipped_columns] = pixels
        return flipped_series[:, ::-1, ::-1]

    def get_image_shape(self) -> tuple[int, int]:
        return (self._num_rows, self._num_columns)

    def get_num_samples(self) -> int:
        return self._num_samples

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_dtype(self) -> np.dtype:
        return np.dtype("float32")

    def get_native_timestamps(self, start_sample: int | None = None, end_sample: int | None = None) -> None:
        return None
