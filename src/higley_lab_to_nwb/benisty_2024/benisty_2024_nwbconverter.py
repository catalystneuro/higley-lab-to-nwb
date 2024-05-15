"""Primary NWBConverter class for this dataset."""

from typing import Dict
from neuroconv import NWBConverter
from neuroconv.datainterfaces import ScanImageMultiFileImagingInterface, Suite2pSegmentationInterface
from neuroconv.utils import DeepDict

class Benisty2024NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        TwoPhotonImagingGreenChannel=ScanImageMultiFileImagingInterface,
        SegmentationGreenChannel=Suite2pSegmentationInterface,
    )
    def __init__(self, source_data: Dict[str, dict],ophys_metadata: Dict[str, dict],  verbose: bool = True):
        super().__init__(source_data, verbose)
        self.ophys_metadata=ophys_metadata

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        segmentation_metadata = self.data_interface_objects["SegmentationGreenChannel"].get_metadata()
        for segmentation_metadata_ind in range(len(segmentation_metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"])):
            metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][segmentation_metadata_ind]["imaging_plane"] = self.ophys_metadata["Ophys"]["ImagingPlane"][0]["name"]
        
        metadata["Ophys"]["Device"] = self.ophys_metadata["Ophys"]["Device"]
        metadata["Ophys"]["TwoPhotonSeries"] = self.ophys_metadata["Ophys"]["TwoPhotonSeries"]
        metadata["Ophys"]["ImagingPlane"] = self.ophys_metadata["Ophys"]["ImagingPlane"]

        return metadata