from pathlib import Path
from typing import Tuple, Literal
import numpy as np
from roiextractors.extraction_tools import PathType, DtypeType, get_package
from roiextractors.imagingextractor import ImagingExtractor
import h5py


from datetime import datetime


def _load_data_from_dual_imaging_configuration(file_path: str, process_type: str) -> np.ndarray:
    """Load pixels matrix from MATLab file generated processing imaging data in dual imaging configuration."""

    with h5py.File(file_path, "r") as file:
        pixels_matrix = file[process_type][:]
        mask = file["mask"][:]
        num_rows, num_columns = mask.shape

    return np.nan_to_num(pixels_matrix), num_rows, num_columns, mask


def _load_data_from_1p_imaging_configuration(file_path: str, process_type: str) -> np.ndarray:
    """Load pixels matrix from MATLab file generated processing imaging data in 1p-imaging only configuration."""

    with h5py.File(file_path, "r") as file:
        pixels_matrix = file["dFoF"][process_type][:]

        num_rows = int(file["R"][:])
        num_columns = int(file["C"][:])

    return np.nan_to_num(pixels_matrix), num_rows, num_columns


class ProcessedImagingExtractor(ImagingExtractor):
    """Specialized extractor for reading processed imaging data from a MATLab file."""

    extractor_name = "ProcessedImagingExtractor"
    is_writable = True
    mode = "file"

    def __init__(
        self,
        file_path: PathType,
        sampling_frequency: float,
        process_type: Literal["dff_final", "dff_blue", "dff_uv", "blue", "uv", "green"],
    ) -> None:
        """Create a ProcessedImagingExtractor instance from a MATLab file.

        Parameters
        ----------
        file_path : PathType
            Path to the MATLab file.
        sampling_frequency : float
            The frequency at which the frames were sampled, in Hz.
        process_type : str
            The type of processed imaging data to extract.
            Accepted values: "dff_final", "dff_blue", "dff_uv", "blue", "uv",  "green".
        Notes
        -----
        """
        super().__init__()
        self.file_path = Path(file_path)
        self._sampling_frequency = sampling_frequency
        self._times = None

        self._channel_names = process_type

        if process_type in ["dff_final", "dff_blue", "dff_uv"]:
            self._pixels_matrix, self._num_rows, self._num_columns, self.mask = (
                _load_data_from_dual_imaging_configuration(file_path=file_path, process_type=process_type)
            )
        elif process_type in ["blue", "uv", "green"]:
            self._pixels_matrix, self._num_rows, self._num_columns = _load_data_from_1p_imaging_configuration(
                file_path=file_path, process_type=process_type
            )

        self._num_frames, number_of_pixels = self._pixels_matrix.shape
        self._dtype = self._pixels_matrix[0].dtype
        if number_of_pixels == self._num_rows * self._num_columns:
            self._mask = None

        elif number_of_pixels != np.count_nonzero(self.mask):
            raise ValueError(
                f"Can't reconstruct frame from pixel matrix. The total number of pixels {number_of_pixels} does "
                f"not match the frame dimension {self._num_rows} * {self._num_columns} or the non-zero elements in "
                f"the frame mask {np.count_nonzero(self.mask)}."
            )
        accepted_process_types = ["dff_final", "dff_blue", "dff_uv", "blue", "uv", "green"]
        assert (
            process_type in accepted_process_types
        ), f"{process_type} must be one of the following values: {accepted_process_types}"

    def _get_single_frame(self, frame_idx: int) -> np.ndarray:
        frame = np.zeros((self._num_rows, self._num_columns))
        i = 0
        for r in range(self._num_rows):
            for c in range(self._num_columns):
                # "dff_blue" and "dff_uv" pixel matrix contains the pixel trace for only the non-zero elements of the
                # mask (different pixel indexing)
                if self._mask is not None and self._mask[r, c] != 0:
                    frame[r, c] = self._pixels_matrix[frame_idx, i]
                    i += 1
                elif self._mask is None:
                    frame[r, c] = self._pixels_matrix[frame_idx, i]
                    i += 1
        return frame

    def get_video(self, start_frame=None, end_frame=None, channel: int = 0) -> np.ndarray:
        """Get the video frames.

        Parameters
        ----------
        start_frame: int, optional
            Start frame index (inclusive).
        end_frame: int, optional
            End frame index (exclusive).

        Returns
        -------
        video: numpy.ndarray
            The video frames.
        """

        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = self._num_frames
        num_frames = end_frame - start_frame

        video = np.zeros((num_frames, self._num_rows, self._num_columns))
        i = 0
        for r in range(self._num_rows):
            for c in range(self._num_columns):
                # "dff_blue" and "dff_uv" pixel matrix contains the pixel trace for only the non-zero elements of the
                # mask (different pixel indexing)
                if self._mask is not None and self._mask[r, c] != 0:
                    video[:, r, c] = self._pixels_matrix[start_frame:end_frame, i]
                    i += 1
                elif self._mask is None:
                    video[:, r, c] = self._pixels_matrix[start_frame:end_frame, i]
                    i += 1

        return video

    def get_image_size(self) -> Tuple[int, int]:
        return (self._num_rows, self._num_columns)

    def get_num_frames(self) -> int:
        return self._num_frames

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_num_channels(self) -> int:
        return 1

    def get_channel_names(self) -> list:
        return self._channel_names

    def get_dtype(self) -> DtypeType:
        return self._dtype
