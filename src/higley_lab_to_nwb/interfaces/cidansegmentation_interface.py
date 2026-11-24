from pathlib import Path

from neuroconv.datainterfaces.ophys.basesegmentationextractorinterface import BaseSegmentationExtractorInterface
from neuroconv.utils import DeepDict

from ..extractors import CidanSegmentationExtractor


def format_string_for_parameters_dict(dict_obj, indent=2):
    def format_key_value(key, value, level):
        indentation = " " * (level * indent)
        if isinstance(value, dict):
            formatted_value = format_dict(value, level + 1)
            return f"{indentation}{key}:\n{formatted_value}"
        else:
            return f"{indentation}{key}: {value}\n"

    def format_dict(d, level):
        return "".join([format_key_value(k, v, level) for k, v in d.items()])

    return format_dict(dict_obj, 0)


class CidanSegmentationInterface(BaseSegmentationExtractorInterface):
    """Interface for CIDAN segmentation data."""

    display_name = "CIDAN Segmentation"
    associated_suffixes = (".json", ".mat")
    info = "Interface for CIDAN segmentation."

    @classmethod
    def get_extractor_class(cls):
        return CidanSegmentationExtractor

    def __init__(
        self,
        parameters_file_path: str | Path,
        roi_list_file_path: str | Path,
        mat_file_path: str | Path,
        sampling_frequency: float,
        image_size: list,
        metadata_key: str = "cidan",
        verbose: bool = False,
    ):
        """
        Parameters
        ----------
        parameters_file_path : str or Path
            The path to the CIDAN parameter .json file.
        roi_list_file_path : str or Path
            The path to the CIDAN roi_list .json file.
        mat_file_path : str or Path
            The path to the CIDAN DF/F traces .mat file.
        sampling_frequency : float
            The sampling frequency of the traces.
        image_size : list
            The frame dimension.
        metadata_key : str, default: "cidan"
            The key of this segmentation in metadata["Ophys"]["PlaneSegmentations"] and ["RoiResponses"].
        """
        super().__init__(
            parameters_file_path=parameters_file_path,
            roi_list_file_path=roi_list_file_path,
            mat_file_path=mat_file_path,
            sampling_frequency=sampling_frequency,
            image_size=image_size,
            metadata_key=metadata_key,
            verbose=verbose,
        )

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        comments = format_string_for_parameters_dict(dict_obj=self.segmentation_extractor.parameters_dict)
        metadata["Ophys"]["RoiResponses"][self.metadata_key]["denoised"] = dict(
            name="RoiResponseSeriesCIDAN",
            description="Fluorescence traces extracted with the CIDAN software.",
            comments=comments,
            unit="n.a.",
        )
        return metadata
