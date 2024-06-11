"""Primary NWBConverter class for this dataset."""

from typing import Dict
from neuroconv import NWBConverter
from neuroconv.utils import DeepDict

from neuroconv.datainterfaces import ScanImageMultiFileImagingInterface, Suite2pSegmentationInterface
from .interfaces import Benisty2024CidanSegmentationInterface
from higley_lab_to_nwb.lohani_2022.interfaces import Lohani2022Spike2SignalsInterface
class Benisty2024NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        TwoPhotonImaging=ScanImageMultiFileImagingInterface,
        Suite2pSegmentation=Suite2pSegmentationInterface,
        CIDANSegmentation=Benisty2024CidanSegmentationInterface,
        Spike2Signals=Lohani2022Spike2SignalsInterface,
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
    
    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["Spike2Signals"]
        # Synch imaging
        imaging_interface = self.data_interface_objects["TwoPhotonImaging"]
        segmentation_interface = self.data_interface_objects["Suite2pSegmentation"]
        stream_id = next(
            (
                stream_id
                for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                if stream_name == "TTLSignal2PExcitation"
            ),
            None,
        )
        ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
        imaging_interface.set_aligned_starting_time(ttl_times[0])
        segmentation_interface.set_aligned_starting_time(ttl_times[0])