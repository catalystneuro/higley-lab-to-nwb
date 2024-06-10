"""Primary NWBConverter class for this dataset."""

from typing import Dict
from neuroconv import NWBConverter
from neuroconv.utils import DeepDict

from neuroconv.datainterfaces import ScanImageMultiFileImagingInterface, Suite2pSegmentationInterface
from .interfaces import Benisty2024CidanSegmentationInterface

class Benisty2024NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        TwoPhotonImaging=ScanImageMultiFileImagingInterface,
        Suite2pSegmentation=Suite2pSegmentationInterface,
        CIDANSegmentation=Benisty2024CidanSegmentationInterface,
    )
    def __init__(self, source_data: Dict[str, dict],ophys_metadata: Dict[str, dict],  verbose: bool = True):
        super().__init__(source_data, verbose)
        self.ophys_metadata=ophys_metadata

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        suite2p_segmentation_metadata = self.data_interface_objects["Suite2pSegmentation"].get_metadata()
        for segmentation_metadata_ind in range(len(suite2p_segmentation_metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"])):
            metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][segmentation_metadata_ind]["imaging_plane"] = self.ophys_metadata["Ophys"]["ImagingPlane"][0]["name"]

        if "CIDANSegmentation" in self.data_interface_objects.keys():
            cidan_segmentation_metadata = self.data_interface_objects["CIDANSegmentation"].get_metadata()
            for segmentation_metadata_ind in range(len(cidan_segmentation_metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"])):
                metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][segmentation_metadata_ind]["imaging_plane"] = self.ophys_metadata["Ophys"]["ImagingPlane"][0]["name"]
            
        metadata["Ophys"]["Device"] = self.ophys_metadata["Ophys"]["Device"]
        metadata["Ophys"]["TwoPhotonSeries"] = self.ophys_metadata["Ophys"]["TwoPhotonSeries"]
        metadata["Ophys"]["ImagingPlane"] = self.ophys_metadata["Ophys"]["ImagingPlane"]

        return metadata