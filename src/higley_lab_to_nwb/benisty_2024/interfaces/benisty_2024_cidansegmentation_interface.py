from typing import Optional
from pynwb import NWBFile
from copy import deepcopy


from neuroconv.datainterfaces.ophys.basesegmentationextractorinterface import BaseSegmentationExtractorInterface
from neuroconv.utils import DeepDict, FilePathType

from ..extractors.benisty_2024_cidansegmentation_extractor import (
    Benisty2024CidanSegmentationExtractor,
)

def format_string_for_parameters_dict(dict_obj, indent=2):
    def format_key_value(key, value, level):
        indentation = ' ' * (level * indent)
        if isinstance(value, dict):
            formatted_value = format_dict(value, level + 1)
            return f"{indentation}{key}:\n{formatted_value}"
        else:
            return f"{indentation}{key}: {value}\n"
    
    def format_dict(d, level):
        return ''.join([format_key_value(k, v, level) for k, v in d.items()])
    
    return format_dict(dict_obj, 0)

class Benisty2024CidanSegmentationInterface(BaseSegmentationExtractorInterface):
    """Interface for Suite2p segmentation data."""

    display_name = "CIDAN Segmentation"
    associated_suffixes = (".json", ".mat")
    info = "Interface for CIDAN segmentation."
    Extractor = Benisty2024CidanSegmentationExtractor

    def __init__(
        self,
        parameters_file_path: FilePathType,
        roi_list_file_path: FilePathType,
        mat_file_path: FilePathType,
        sampling_frequency: float,
        plane_segmentation_name: Optional[str] = None,
        verbose: bool = True,
    ):
        """Create SegmentationExtractor object out of CIDAN data type.

        Parameters
        ----------
        parameters_file_path: str or Path
            The path to the CIDAN parameter .json file.
        roi_list_file_path: str or Path
            The path to the CIDAN roi_list .json file.
        mat_file_path: str or Path
            The path to the CIDAN df/f traces .mat file.
        sampling_frequency: float
            The sampling frequency of the fluorescence traces
        plane_segmentation_name: str, optional
            The name of the plane segmentation to be added.
        """

        super().__init__(
            parameters_file_path=parameters_file_path,
            roi_list_file_path=roi_list_file_path,
            mat_file_path=mat_file_path,
            sampling_frequency=sampling_frequency,
        )

        plane_segmentation_name = plane_segmentation_name or "PlaneSegmentation"

        self.plane_segmentation_name = plane_segmentation_name
        self.verbose = verbose

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # No need to update the metadata links for the default plane segmentation name
        default_plane_segmentation_name = metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][0]["name"]
        if self.plane_segmentation_name == default_plane_segmentation_name:
            return metadata

        plane_segmentation_metadata = metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][0]
        default_plane_segmentation_name = plane_segmentation_metadata["name"]
        default_plane_suffix = default_plane_segmentation_name.replace("PlaneSegmentation", "")
        new_plane_name_suffix = self.plane_segmentation_name.replace("PlaneSegmentation", "")
        plane_segmentation_metadata.update(
            name=self.plane_segmentation_name,
        )

        fluorescence_metadata_per_plane = metadata["Ophys"]["Fluorescence"].pop(default_plane_segmentation_name)
        # override the default name of the plane segmentation
        metadata["Ophys"]["Fluorescence"][self.plane_segmentation_name] = fluorescence_metadata_per_plane
        trace_names = [
            property_name for property_name in fluorescence_metadata_per_plane.keys() if property_name != "name"
        ]
        comments=format_string_for_parameters_dict(dict_obj=self.segmentation_extractor.parameters_dict)
        for trace_name in trace_names:
            default_raw_traces_name = fluorescence_metadata_per_plane[trace_name]["name"].replace(
                default_plane_suffix, ""
            )
            fluorescence_metadata_per_plane[trace_name].update(
                name=default_raw_traces_name + new_plane_name_suffix,
                comments=comments,
            )

        return metadata

