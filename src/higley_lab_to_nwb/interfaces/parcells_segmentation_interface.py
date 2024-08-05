from typing import Optional


from neuroconv.datainterfaces.ophys.basesegmentationextractorinterface import BaseSegmentationExtractorInterface
from neuroconv.utils import DeepDict, FilePathType

from ..extractors import ParcellsSegmentationExtractor


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


class ParcellsSegmentationInterface(BaseSegmentationExtractorInterface):
    """Interface for parcellation algorithm for segmenting imaging data."""

    display_name = "Parcells Segmentation"
    associated_suffixes = ".mat"
    info = "Interface for parcellation algorithm for segmenting imaging data."
    Extractor = ParcellsSegmentationExtractor

    def __init__(
        self,
        file_path: FilePathType,
        sampling_frequency: float,
        image_size: list,
        plane_segmentation_name: Optional[str] = None,
        verbose: bool = True,
    ):
        """Create SegmentationExtractor object out of Parcells data type.

        Parameters
        ----------
        file_path: str or Path
            The path to the CIDAN df/f traces .mat file.
        sampling_frequency: float
            The sampling frequency of the fluorescence traces
        image_size: list
            The frame dimension.
        plane_segmentation_name: str, optional
            The name of the plane segmentation to be added.
        """

        super().__init__(
            file_path=file_path,
            sampling_frequency=sampling_frequency,
            image_size=image_size,
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
        for trace_name in trace_names:
            default_traces_name = fluorescence_metadata_per_plane[trace_name]["name"].replace(default_plane_suffix, "")
            fluorescence_metadata_per_plane[trace_name].update(
                name=default_traces_name + new_plane_name_suffix,
                description="Fluorescence traces extracted from parcellation algorithm",
            )

        return metadata
