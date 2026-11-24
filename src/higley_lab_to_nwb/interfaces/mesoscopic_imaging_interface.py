from pathlib import Path
from typing import Literal

from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface

from ..extractors import MesoscopicImagingMultiTiffSingleFrameExtractor, MesoscopicImagingMultiTiffStackExtractor


class MesoscopicImagingMultiTiffStackInterface(BaseImagingExtractorInterface):
    """One excitation channel of multi-frame TIFF files, read with MesoscopicImagingMultiTiffStackExtractor."""

    @classmethod
    def get_extractor_class(cls):
        return MesoscopicImagingMultiTiffStackExtractor

    def __init__(
        self,
        folder_path: str | Path,
        file_pattern: str,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
        metadata_key: str | None = None,
        photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "OnePhotonSeries",
        verbose: bool = False,
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
        metadata_key : str, optional
            The key of this series in metadata["Ophys"]["MicroscopySeries"].
        """
        super().__init__(
            folder_path=folder_path,
            file_pattern=file_pattern,
            number_of_channels=number_of_channels,
            channel_first_frame_index=channel_first_frame_index,
            sampling_frequency=sampling_frequency,
            metadata_key=metadata_key,
            photon_series_type=photon_series_type,
            verbose=verbose,
        )


class MesoscopicImagingMultiTiffSingleFrameInterface(BaseImagingExtractorInterface):
    """One excitation channel and camera of single-frame TIFF files, read with MesoscopicImagingMultiTiffSingleFrameExtractor."""

    @classmethod
    def get_extractor_class(cls):
        return MesoscopicImagingMultiTiffSingleFrameExtractor

    def __init__(
        self,
        folder_path: str | Path,
        file_pattern: str,
        number_of_channels: int,
        channel_first_frame_index: int,
        sampling_frequency: float,
        frame_side: Literal["left", "right"] = "left",
        metadata_key: str | None = None,
        photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "OnePhotonSeries",
        verbose: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        folder_path : str or Path
            Path to the folder containing the TIFF files.
        file_pattern : str
            The prefix of the TIFF file names.
        number_of_channels : int
            Number of channels alternating in the acquisition cycle.
        channel_first_frame_index : int
            The frame index of the first acquisition of the desired channel.
        sampling_frequency : float
            The frame rate of one channel, in Hz.
        frame_side : {"left", "right"}
            The half of the frame (camera) to keep.
        metadata_key : str, optional
            The key of this series in metadata["Ophys"]["MicroscopySeries"].
        """
        super().__init__(
            folder_path=folder_path,
            file_pattern=file_pattern,
            number_of_channels=number_of_channels,
            channel_first_frame_index=channel_first_frame_index,
            sampling_frequency=sampling_frequency,
            frame_side=frame_side,
            metadata_key=metadata_key,
            photon_series_type=photon_series_type,
            verbose=verbose,
        )
