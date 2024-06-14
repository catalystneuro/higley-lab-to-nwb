"""Primary NWBConverter class for this dataset."""

from typing import Dict
from neuroconv import NWBConverter
from neuroconv.utils import DeepDict

from neuroconv.datainterfaces import ScanImageMultiFileImagingInterface, Suite2pSegmentationInterface
from higley_lab_to_nwb.interfaces import (
    Spike2SignalsInterface,
    VisualStimulusInterface,
    Spike2SignalsInterface,
    CidanSegmentationInterface,
    MesoscopicImagingMultiTiffStackInterface,
)
from neuroconv.datainterfaces import VideoInterface, FacemapInterface


class Benisty2024NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        TwoPhotonImaging=ScanImageMultiFileImagingInterface,
        Suite2pSegmentation=Suite2pSegmentationInterface,
        Spike2Signals=Spike2SignalsInterface,
        CIDANSegmentation=CidanSegmentationInterface,
        Video=VideoInterface,
        FacemapInterface=FacemapInterface,
        VisualStimulusInterface=VisualStimulusInterface,
        OnePhotonImaging=MesoscopicImagingMultiTiffStackInterface,
        OnePhotonImagingIsosbestic=MesoscopicImagingMultiTiffStackInterface,
    )

    def __init__(self, source_data: Dict[str, dict], ophys_metadata: Dict[str, dict], verbose: bool = True):
        super().__init__(source_data, verbose)
        self.ophys_metadata = ophys_metadata

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        suite2p_segmentation_metadata = self.data_interface_objects["Suite2pSegmentation"].get_metadata()
        for segmentation_metadata_ind in range(
            len(suite2p_segmentation_metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"])
        ):
            metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][segmentation_metadata_ind][
                "imaging_plane"
            ] = self.ophys_metadata["Ophys"]["ImagingPlane"][0]["name"]

        if "CIDANSegmentation" in self.data_interface_objects.keys():
            cidan_segmentation_metadata = self.data_interface_objects["CIDANSegmentation"].get_metadata()
            for segmentation_metadata_ind in range(
                len(cidan_segmentation_metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"])
            ):
                metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][segmentation_metadata_ind][
                    "imaging_plane"
                ] = self.ophys_metadata["Ophys"]["ImagingPlane"][0]["name"]

        metadata["Ophys"]["Device"] = self.ophys_metadata["Ophys"]["Device"]
        metadata["Ophys"]["TwoPhotonSeries"] = self.ophys_metadata["Ophys"]["TwoPhotonSeries"]
        if "OnePhotonSeries" in metadata["Ophys"]:
            metadata["Ophys"]["OnePhotonSeries"] = self.ophys_metadata["Ophys"]["OnePhotonSeries"]
        metadata["Ophys"]["ImagingPlane"] = self.ophys_metadata["Ophys"]["ImagingPlane"]

        return metadata


    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["Spike2Signals"]

        # Synch 2p imaging
        two_photon_imaging_interface = self.data_interface_objects["TwoPhotonImaging"]
        segmentation_interface = self.data_interface_objects["Suite2pSegmentation"]
        channel_name = "TTLSignal2PExcitation"
        ttl_times = ttlsignal_interface.get_event_times_from_ttl_channel_name(channel_name=channel_name)
        two_photon_imaging_interface.set_aligned_starting_time(ttl_times[0])
        segmentation_interface.set_aligned_starting_time(ttl_times[0])

        # Synch 1p imaging
        if "OnePhotonImaging" in self.data_interface_objects.keys():
            one_photon_imaging_interface = self.data_interface_objects["OnePhotonImaging"]
            channel_name = "TTLSignalBlueLED"
            ttl_times = ttlsignal_interface.get_event_times_from_ttl_channel_name(channel_name=channel_name)
            one_photon_imaging_interface.set_aligned_starting_time(ttl_times[0])

        # Synch 1p isosbestic imaging
        if "OnePhotonImagingIsosbestic" in self.data_interface_objects.keys():
            one_photon_imaging_interface = self.data_interface_objects["OnePhotonImagingIsosbestic"]
            channel_name = "TTLSignalVioletLED"
            ttl_times = ttlsignal_interface.get_event_times_from_ttl_channel_name(channel_name=channel_name)
            one_photon_imaging_interface.set_aligned_starting_time(ttl_times[0])

        # Synch behaviour
        if "Video" in self.data_interface_objects.keys():
            video_interface = self.data_interface_objects["Video"]
            # facemap_interface = self.data_interface_objects["FacemapInterface"]
            video_interface._timestamps = video_interface.get_timestamps()
            channel_name = "TTLSignalPupilCamera"
            ttl_times = ttlsignal_interface.get_event_times_from_ttl_channel_name(channel_name=channel_name)
            video_interface.set_aligned_starting_time(ttl_times[0])
            # facemap_interface.set_aligned_starting_time(ttl_times[0])
