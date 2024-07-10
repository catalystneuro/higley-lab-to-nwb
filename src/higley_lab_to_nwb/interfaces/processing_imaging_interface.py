from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface
from typing import Literal
from neuroconv.utils.dict import DeepDict
from roiextractors.extraction_tools import PathType

from ..extractors import ProcessedImagingExtractor


class ProcessedImagingInterface(BaseImagingExtractorInterface):
    """
    Data Interface for writing processed imaging data using ProcessedImagingExtractor.
    """

    Extractor = ProcessedImagingExtractor

    def __init__(
        self,
        file_path: PathType,
        process_type: Literal["dff_final", "dff_blue", "dff_uv", "blue", "uv", "green"],
        sampling_frequency: float,
        verbose: bool = True,
        photon_series_type: str = "OnePhotonSeries",
    ) -> None:
        """Create a MesoscopicImagingTiffStackExtractor instance from a folder of TIFF files.

        Parameters
        ----------
        file_path : PathType
            Path to the MATLab file.
        process_type : str
            The type of processed imaging data to extract.
            Accepted values: "dff_final", "dff_blue", "dff_uv", "blue", "uv",  "green".
        sampling_frequency : float
            The frequency at which the frames were sampled, in Hz.
        """
        super().__init__(
            file_path=file_path,
            process_type=process_type,
            sampling_frequency=sampling_frequency,
            verbose=verbose,
            photon_series_type=photon_series_type,
        )

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        return metadata
