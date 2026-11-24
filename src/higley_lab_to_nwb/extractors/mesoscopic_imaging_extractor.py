from pathlib import Path
from typing import Literal
from warnings import warn

import numpy as np
import tifffile
from natsort import natsorted
from roiextractors.imagingextractor import ImagingExtractor
from roiextractors.multiimagingextractor import MultiImagingExtractor


class MesoscopicImagingMultiTiffStackExtractor(MultiImagingExtractor):
    """One excitation channel of a set of multi-frame TIFF files whose frames cycle through the channels."""

    extractor_name = "MesoscopicImagingMultiTiffStackExtractor"

    def __init__(
        self,
        folder_path: str | Path,
        file_pattern: str,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
    ) -> None:
        """
        Parameters
        ----------
        folder_path : str or Path
            Path to the folder containing the TIFF files.
        file_pattern : str
            Pattern for the TIFF files to read, see pathlib.Path.glob.
        number_of_channels : int
            Number of channels alternating in the acquisition cycle.
        channel_first_frame_index : int
            The frame index of the first acquisition of the desired channel.
        sampling_frequency : float
            The frame rate of one channel, in Hz.
        """
        self.folder_path = Path(folder_path)
        file_paths = natsorted(self.folder_path.glob(file_pattern))
        imaging_extractors = [
            MesoscopicImagingTiffStackExtractor(
                file_path=file_path,
                number_of_channels=number_of_channels,
                channel_first_frame_index=channel_first_frame_index,
                sampling_frequency=sampling_frequency,
            )
            for file_path in file_paths
        ]
        super().__init__(imaging_extractors=imaging_extractors)


class MesoscopicImagingTiffStackExtractor(ImagingExtractor):
    """One excitation channel of a multi-frame TIFF file whose frames cycle through the channels.

    The frames are stored round-robin: the first frame of each channel, then the second frame of each channel, etc.
    """

    extractor_name = "MesoscopicImagingTiffStackExtractor"

    def __init__(
        self,
        file_path: str | Path,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
    ) -> None:
        super().__init__()
        self.file_path = Path(file_path)
        self._sampling_frequency = sampling_frequency
        self._num_channels = number_of_channels
        self.channel_first_frame_index = channel_first_frame_index

        try:
            self._raw_video = tifffile.memmap(self.file_path, mode="r")
        except ValueError:
            warn(f"Could not memory-map {self.file_path}; reading it into memory.")
            with tifffile.TiffFile(self.file_path) as tif:
                self._raw_video = tif.asarray()

        if self._raw_video.ndim != 3:
            raise NotImplementedError("Only 3D (frames, rows, columns) TIFF data is supported.")
        total_num_frames, self._num_rows, self._num_columns = self._raw_video.shape
        self._num_samples = len(range(channel_first_frame_index, total_num_frames, number_of_channels))

    def get_series(self, start_sample: int | None = None, end_sample: int | None = None) -> np.ndarray:
        start_sample = 0 if start_sample is None else start_sample
        end_sample = self._num_samples if end_sample is None else end_sample
        raw_start = start_sample * self._num_channels + self.channel_first_frame_index
        raw_end = (end_sample - 1) * self._num_channels + self.channel_first_frame_index + 1
        return np.asarray(self._raw_video[raw_start : raw_end : self._num_channels])

    def get_image_shape(self) -> tuple[int, int]:
        return (self._num_rows, self._num_columns)

    def get_num_samples(self) -> int:
        return self._num_samples

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_dtype(self) -> np.dtype:
        return self._raw_video.dtype

    def get_native_timestamps(self, start_sample: int | None = None, end_sample: int | None = None) -> None:
        return None


class MesoscopicImagingMultiTiffSingleFrameExtractor(ImagingExtractor):
    """One excitation channel and one camera of a folder of single-frame TIFF files.

    The files cycle through the excitation channels. Each frame holds the two cameras side by side, 512 columns
    each; `frame_side` picks one. Frames are transposed so that they are (rows, columns) of the camera.
    """

    extractor_name = "MesoscopicImagingMultiTiffSingleFrameExtractor"

    def __init__(
        self,
        folder_path: str | Path,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
        frame_side: Literal["left", "right"] = "left",
        file_pattern: str = "",
    ) -> None:
        """
        Parameters
        ----------
        folder_path : str or Path
            Path to the folder containing the TIFF files.
        number_of_channels : int
            Number of channels alternating in the acquisition cycle.
        channel_first_frame_index : int
            The frame index of the first acquisition of the desired channel.
        sampling_frequency : float
            The frame rate of one channel, in Hz.
        frame_side : {"left", "right"}
            The half of the frame to keep.
        file_pattern : str
            The prefix of the TIFF file names.
        """
        if frame_side not in ("left", "right"):
            raise ValueError("frame_side must be either 'left' or 'right'.")
        super().__init__()
        tiff_file_paths = natsorted(Path(folder_path).glob(file_pattern + "*.tif"))
        self._selected_tiff_file_paths = tiff_file_paths[channel_first_frame_index::number_of_channels]
        self._num_samples = len(self._selected_tiff_file_paths)
        self.frame_side = frame_side
        self._sampling_frequency = sampling_frequency
        self._columns = slice(None, 512) if frame_side == "left" else slice(512, None)

    def get_series(self, start_sample: int | None = None, end_sample: int | None = None) -> np.ndarray:
        start_sample = 0 if start_sample is None else start_sample
        end_sample = self._num_samples if end_sample is None else end_sample
        video = np.stack(
            [
                tifffile.memmap(file_path, mode="r")[:, self._columns]
                for file_path in self._selected_tiff_file_paths[start_sample:end_sample]
            ]
        )
        return video.transpose((0, 2, 1))

    def get_image_shape(self) -> tuple[int, int]:
        return self.get_series(start_sample=0, end_sample=1).shape[1:]

    def get_num_samples(self) -> int:
        return self._num_samples

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_dtype(self) -> np.dtype:
        return self.get_series(start_sample=0, end_sample=1).dtype

    def get_native_timestamps(self, start_sample: int | None = None, end_sample: int | None = None) -> None:
        return None
