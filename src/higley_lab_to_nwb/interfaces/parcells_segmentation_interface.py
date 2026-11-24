from pathlib import Path

from neuroconv.datainterfaces.ophys.basesegmentationextractorinterface import BaseSegmentationExtractorInterface

from ..extractors import ParcellsSegmentationExtractor


class ParcellsSegmentationInterface(BaseSegmentationExtractorInterface):
    """Interface for the functional parcellation of the lab's code."""

    display_name = "Parcells Segmentation"
    associated_suffixes = (".mat",)
    info = "Interface for the functional parcellation output of the Higley lab code."

    @classmethod
    def get_extractor_class(cls):
        return ParcellsSegmentationExtractor

    def __init__(
        self,
        file_path: str | Path,
        sampling_frequency: float,
        image_size: list,
        metadata_key: str | None = None,
        verbose: bool = False,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            The path to the parcellation output .mat file.
        sampling_frequency : float
            The sampling frequency of the traces.
        image_size : list
            The frame dimension, [n_rows, n_cols].
        metadata_key : str, optional
            The key of this segmentation in metadata["Ophys"]["PlaneSegmentations"] and ["RoiResponses"].
        """
        super().__init__(
            file_path=file_path,
            sampling_frequency=sampling_frequency,
            image_size=image_size,
            metadata_key=metadata_key,
            verbose=verbose,
        )
