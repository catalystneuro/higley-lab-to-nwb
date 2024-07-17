from pathlib import Path
from typing import Tuple
from warnings import warn
import numpy as np
from roiextractors.extraction_tools import PathType, ArrayType, DtypeType, get_package
from roiextractors.imagingextractor import ImagingExtractor
from roiextractors.multiimagingextractor import MultiImagingExtractor


class MesoscopicImagingMultiTiffStackExtractor(MultiImagingExtractor):
    """Specialized extractor for reading multi-file (buffered) TIFF files."""  # TODO add description

    extractor_name = "MesoscopicImagingTiffStackExtractor"
    is_writable = True
    mode = "folder"

    def __init__(
        self,
        folder_path: PathType,
        file_pattern: str,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
    ) -> None:
        """Create a MesoscopicImagingTiffStackExtractor instance from a folder of TIFF files.

        Parameters
        ----------
        folder_path : PathType
            Path to the folder containing the TIFF files.
        file_pattern : str
            Pattern for the TIFF files to read -- see pathlib.Path.glob for details.
        number_of_channels: int
            Number of channels alternating in the acquisition cycle.
        channel_first_frame_index: int
            The frame index corresponding to the first acuisition of the desired channel
        sampling_frequency : float
            The frequency at which the frames were sampled, in Hz.
        """
        self.folder_path = Path(folder_path)
        from natsort import natsorted

        file_paths = natsorted(self.folder_path.glob(file_pattern))

        imaging_extractors = []
        for file_path in file_paths:
            imaging_extractor = MesoscopicImagingTiffStackExtractor(
                file_path=file_path,
                number_of_channels=number_of_channels,
                channel_first_frame_index=channel_first_frame_index,
                sampling_frequency=sampling_frequency,
            )
            imaging_extractors.append(imaging_extractor)
        super().__init__(imaging_extractors=imaging_extractors)


class MesoscopicImagingTiffStackExtractor(ImagingExtractor):
    """Specialized extractor for reading a TIFF file."""  # TODO add description

    extractor_name = "MesoscopicImagingTiffStackExtractor"
    is_writable = True
    mode = "file"

    def __init__(
        self,
        file_path: PathType,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
    ) -> None:
        """Create a MesoscopicImagingTiffStackExtractor instance from a TIFF file.

        The underlying data is stored in a round-robin format collapsed into 3 dimensions (frames, rows, columns).
        I.e. the first frame of each channel is stored, and then the second frame of each channel, etc.

        Parameters
        ----------
        folder_path : PathType
            Path to the folder containing the TIFF files.
        number_of_channels: int
            Number of channels alternating in the acquisition cycle.
        channel_first_frame_index: int
            The frame index corresponding to the first acuisition of the desired channel
        sampling_frequency : float
            The frequency at which the frames were sampled, in Hz.
        Notes
        -----
        """
        tifffile = get_package(package_name="tifffile")

        super().__init__()
        self.file_path = Path(file_path)
        self._sampling_frequency = sampling_frequency
        self._num_channels = number_of_channels
        self.channel_first_frame_index = channel_first_frame_index
        self._channel_names = [f"Channel{i}" for i in range(number_of_channels)]

        try:
            self._raw_video = tifffile.memmap(self.file_path, mode="r")
        except ValueError:
            warn(
                "memmap of TIFF file could not be established. Reading entire matrix into memory. "
                "Consider using the ScanImageTiffExtractor for lazy data access."
            )
            with tifffile.TiffFile(self.file_path) as tif:
                self._raw_video = tif.asarray()

        shape = self._raw_video.shape
        if len(shape) == 3:
            self._total_num_frames, self._num_rows, self._num_columns = shape
            self._num_frames = self._total_num_frames // self._num_channels
        else:
            raise NotImplementedError("Extractor cannot handle 4D Tiff data.")
        self._times = None

    def get_frames(self, frame_idxs: ArrayType) -> np.ndarray:
        """Get specific video frames from indices (not necessarily continuous).

        Parameters
        ----------
        frame_idxs: array-like
            Indices of frames to return.

        Returns
        -------
        frames: numpy.ndarray
            The video frames.
        """
        if isinstance(frame_idxs, int):
            frame_idxs = [frame_idxs]
        self.check_frame_inputs(frame_idxs[-1])

        if not all(np.diff(frame_idxs) == 1):
            return np.concatenate([self._get_single_frame(frame=idx) for idx in frame_idxs])
        else:
            return self.get_video(start_frame=frame_idxs[0], end_frame=frame_idxs[-1] + 1)

    # Data accessed through an open ScanImageTiffReader io gets scrambled if there are multiple calls.
    # Thus, open fresh io in context each time something is needed.
    def _get_single_frame(self, frame: int) -> np.ndarray:
        """Get a single frame of data from the TIFF file.

        Parameters
        ----------
        frame : int
            The index of the frame to retrieve.

        Returns
        -------
        frame: numpy.ndarray
            The frame of data.
        """
        self.check_frame_inputs(frame)
        raw_index = self.frame_to_raw_index(frame)
        return self._raw_video[raw_index : raw_index + 1]

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
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = self._total_num_frames // self._num_channels
        end_frame_inclusive = end_frame - 1
        self.check_frame_inputs(end_frame_inclusive)
        self.check_frame_inputs(start_frame)
        raw_start = self.frame_to_raw_index(start_frame)
        raw_end_inclusive = self.frame_to_raw_index(end_frame_inclusive)
        raw_end = raw_end_inclusive + 1
        video = self._raw_video[raw_start : raw_end : self._num_channels, ...]
        return video

    def get_image_size(self) -> Tuple[int, int]:
        return (self._num_rows, self._num_columns)

    def get_num_frames(self) -> int:
        return self._num_frames

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_num_channels(self) -> int:
        return self._num_channels

    def get_channel_names(self) -> list:
        return self._channel_names

    def get_dtype(self) -> DtypeType:
        return self.get_frames(0).dtype

    def check_frame_inputs(self, frame) -> None:
        """Check that the frame index is valid. Raise ValueError if not.

        Parameters
        ----------
        frame : int
            The index of the frame to retrieve.

        Raises
        ------
        ValueError
            If the frame index is invalid.
        """
        if frame >= self._num_frames:
            raise ValueError(f"Frame index ({frame}) exceeds number of frames ({self._num_frames}).")
        if frame < 0:
            raise ValueError(f"Frame index ({frame}) must be greater than or equal to 0.")

    def frame_to_raw_index(self, frame: int) -> int:
        """Convert a frame index to the raw index in the TIFF file.

        Parameters
        ----------
        frame : int
            The index of the frame to retrieve.

        Returns
        -------
        raw_index: int
            The raw index of the frame in the TIFF file.

        """
        return (frame * self._num_channels) + self.channel_first_frame_index
