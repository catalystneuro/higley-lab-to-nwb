"""Primary class for converting experiment-specific behavior."""

from pathlib import Path
from natsort import natsorted
from datetime import datetime
import numpy as np
from typing import Union, Optional, Tuple
from copy import deepcopy

from neuroconv.utils import FolderPathType, FilePathType

from roiextractors import ImagingExtractor

from roiextractors.extraction_tools import ArrayType, PathType, DtypeType, FloatType
from roiextractors.extractors.tiffimagingextractors.scanimagetiff_utils import (
    extract_extra_metadata,
    _get_scanimage_reader,
)
def extract_file_timestamp(file_path: FilePathType) -> float:
    metadata = extract_extra_metadata(file_path)
    time_object = datetime.strptime(metadata["Time_From_Start"], "%H:%M:%S.%f")
    timestamp_in_seconds = (
        (time_object.hour * 3600) + (time_object.minute * 60) + time_object.second + (time_object.microsecond / 1e6)
    )
    return timestamp_in_seconds

class Benisty2022ImagingExtractor(ImagingExtractor):
    """Specialized extractor for Benisty2022 conversion project: reading ScanImage .tif files"""

    extractor_name = "Benisty2022ImagingExtractor"
    is_writable = True
    mode = "folder"

    def __init__(
        self,
        folder_path: FolderPathType,
    ) -> None:
        self.folder_path = Path(folder_path)
        self.tif_file_paths = natsorted(self.folder_path.glob("*.tif"))
        self.tif_file_paths = self.tif_file_paths[:10] #for testing
        assert self.tif_file_paths, f"The TIF image files are missing from '{self.folder_path}'."

        ScanImageTiffReader = _get_scanimage_reader()
        with ScanImageTiffReader(str(self.tif_file_paths[0])) as io:
            shape = io.shape()  # [rows, columns]
        self._num_rows, self._num_columns = shape
        self._num_frames = len(self.tif_file_paths)
        print(extract_file_timestamp(file_path=self.tif_file_paths[0]))
        self._times = [extract_file_timestamp(file_path=tif_file_path) for tif_file_path in self.tif_file_paths]


    def get_image_size(self) -> Tuple[int, int]:
        return self._num_rows, self._num_columns

    
    def get_num_frames(self) -> int:
        return self._num_frames

    
    def get_sampling_frequency(self) -> float:
        return None

    
    def get_channel_names(self) -> list:
        return None

    
    def get_num_channels(self) -> int:
        return 1
    
    def get_video(
        self, start_frame: Optional[int] = None, end_frame: Optional[int] = None, channel: int = 0
    ) -> np.ndarray:
        ScanImageTiffReader = _get_scanimage_reader()
        video=[]
        if start_frame is None:
            start_frame=0
        if end_frame is None:
            end_frame=self._num_frames
        for frame in range(start_frame,end_frame):
            with ScanImageTiffReader(str(self.tif_file_paths[frame])) as io:
                frame = io.data()
            video.append(frame)
        return np.array(video)

    def get_frames(self, frame_idxs: ArrayType, channel: Optional[int] = 0) -> np.ndarray:
        """Get specific video frames from indices (not necessarily continuous).

        Parameters
        ----------
        frame_idxs: array-like
            Indices of frames to return.
        channel: int, optional
            Channel index.

        Returns
        -------
        frames: numpy.ndarray
            The video frames.
        """
        assert max(frame_idxs) <= self.get_num_frames(), "'frame_idxs' exceed number of frames"
        if np.all(np.diff(frame_idxs) == 0):
            return self.get_video(start_frame=frame_idxs[0], end_frame=frame_idxs[-1])
        relative_indices = np.array(frame_idxs) - frame_idxs[0]
        return self.get_video(start_frame=frame_idxs[0], end_frame=frame_idxs[-1] + 1)[relative_indices, ...]

    def frame_to_time(self, frames: Union[FloatType, np.ndarray]) -> Union[FloatType, np.ndarray]:
        return self._times[frames]

    def time_to_frame(self, times: Union[FloatType, ArrayType]) -> Union[FloatType, np.ndarray]:
        return np.searchsorted(self._times, times).astype("int64")

    