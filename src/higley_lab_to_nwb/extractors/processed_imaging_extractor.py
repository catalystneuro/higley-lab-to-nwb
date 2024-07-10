from pathlib import Path
from typing import Tuple, Literal
import numpy as np
from roiextractors.extraction_tools import PathType, DtypeType, get_package
from roiextractors.imagingextractor import ImagingExtractor


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

        pymatreader = get_package(package_name="pymatreader")
        mat = pymatreader.read_mat(str(file_path))

        dual_configuration_streams = {
            "dff_final": "HemodynamicCorrection",
            "dff_blue": "DFFBlueExcitation",
            "dff_uv": "DFFVioletExcitation",
        }
        only_1p_configuration_streams = {
            "blue": "DFFBlueExcitation",
            "uv": "DFFVioletExcitation",
            "green": "DFFGreenExcitation",
        }

        if process_type in dual_configuration_streams.keys():
            self._pixels_matrix = mat[process_type]
            mask = mat["mask"]
            self._num_rows, self._num_columns = mask.shape
            self._channel_names = [dual_configuration_streams[process_type]]

        elif process_type in only_1p_configuration_streams.keys():
            self._pixels_matrix = mat["dFoF"][process_type]
            self._num_rows = int(mat["R"])
            self._num_columns = int(mat["C"])
            self._channel_names = [only_1p_configuration_streams[process_type]]
        else:
            raise f"{process_type} does not exist in {file_path}"

        number_of_pixels, self._num_frames = self._pixels_matrix.shape
        self._raw_video = np.full((self._num_frames, self._num_rows, self._num_columns), np.nan)

        if number_of_pixels == self._num_rows * self._num_columns:
            self._mask = None

        elif number_of_pixels == np.count_nonzero(mask):
            self._mask = mask

        else:
            raise (
                f"Can't reconstruct frame from pixel matrix. The total number of pixels {number_of_pixels} does "
                f"not match the frame dimension {self._num_rows} * {self._num_columns} or the non-zero elements in "
                f"the frame mask {np.count_nonzero(mask)}."
            )

    def get_video(self, start_frame=None, end_frame=None) -> np.ndarray:
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
        video = np.full((self._num_frames, self._num_rows, self._num_columns), np.nan)
        i = 0
        for c in range(self._num_columns):
            for r in range(self._num_rows):
                if self._mask is not None and self._mask[r, c] != 0:
                    video[start_frame:end_frame, r, c] = self._pixels_matrix[i, start_frame:end_frame]
                    i += 1
                elif self._mask is None:
                    video[start_frame:end_frame, r, c] = self._pixels_matrix[i, start_frame:end_frame]
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
        return self.get_frames(0).dtype
