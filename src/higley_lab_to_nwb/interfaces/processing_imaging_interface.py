from pathlib import Path
from typing import Literal

from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface

from ..extractors import ProcessedImagingExtractor


class ProcessedImagingInterface(BaseImagingExtractorInterface):
    """Processed (DF/F) imaging data saved by the lab's MATLAB code, read with ProcessedImagingExtractor."""

    @classmethod
    def get_extractor_class(cls):
        return ProcessedImagingExtractor

    def __init__(
        self,
        file_path: str | Path,
        process_type: Literal["dff_final", "dff_blue", "dff_uv", "blue", "uv", "green"],
        sampling_frequency: float,
        metadata_key: str | None = None,
        photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "OnePhotonSeries",
        verbose: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        file_path : str or Path
            Path to the MATLAB file.
        process_type : str
            The variable to read: "dff_final", "dff_blue", "dff_uv", "blue", "uv" or "green".
        sampling_frequency : float
            The frame rate, in Hz.
        metadata_key : str, optional
            The key of this series in metadata["Ophys"]["MicroscopySeries"].
        """
        super().__init__(
            file_path=file_path,
            process_type=process_type,
            sampling_frequency=sampling_frequency,
            metadata_key=metadata_key,
            photon_series_type=photon_series_type,
            verbose=verbose,
        )
