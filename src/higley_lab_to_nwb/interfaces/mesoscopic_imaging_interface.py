from dateutil.parser import parse as dateparse
import datetime
from pathlib import Path
from natsort import natsorted

from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface
from neuroconv.utils import FolderPathType
from neuroconv.utils.dict import DeepDict

from ..extractors import MesoscopicImagingMultiTiffStackExtractor


class MesoscopicImagingMultiTiffStackInterface(BaseImagingExtractorInterface):
    """
    Data Interface for writing mesoscopic imaging data using MesoscopicImagingMultiTiffStackExtractor.
    """

    Extractor = MesoscopicImagingMultiTiffStackExtractor

    def __init__(
        self,
        folder_path: FolderPathType,
        file_pattern: str,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
        verbose: bool = True,
        photon_series_type: str = "OnePhotonSeries",
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
        super().__init__(
            folder_path=folder_path,
            file_pattern=file_pattern,
            number_of_channels=number_of_channels,
            channel_first_frame_index=channel_first_frame_index,
            sampling_frequency=sampling_frequency,
            verbose=verbose,
            photon_series_type=photon_series_type,
        )


    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        return metadata
