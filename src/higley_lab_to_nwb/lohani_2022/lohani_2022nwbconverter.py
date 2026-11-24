"""Primary NWBConverter class for this dataset."""

from typing import Dict, List
from pynwb import NWBFile
from neuroconv import NWBConverter
from neuroconv.datainterfaces import VideoInterface
from neuroconv.utils import DeepDict
from neuroconv.tools.nwb_helpers import make_or_load_nwbfile
from higley_lab_to_nwb.interfaces import (
    MesoscopicImagingMultiTiffSingleFrameInterface,
    Spike2SignalsInterface,
    ExternalStimuliInterface,
    ProcessedBehaviorInterface,
    ProcessedImagingInterface,
    ParcellsSegmentationInterface,
    AllenParcelsInterface,
    FacemapInterface,
)

# The lab's detrending (detrend_all_pixels.m, filter length 1000) removes the first 499 frames of each excitation
# channel, so DF/F frame 0 is raw frame 499 (0-based), as in the lab's smrxExtractionPreProcessing.m.
FIRST_DFF_FRAME_INDEX = 499
# The parcellation traces have 300 frames fewer than the DF/F; their frame 0 is DF/F frame 150.
FIRST_PARCELLATED_FRAME_INDEX = FIRST_DFF_FRAME_INDEX + 150


class Lohani2022NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        Spike2Signals=Spike2SignalsInterface,
        Video=VideoInterface,
        FacemapInterface=FacemapInterface,
        VisualStimulusInterface=ExternalStimuliInterface,
        AirpuffInterface=ExternalStimuliInterface,
        ProcessedWheelSignalInterface=ProcessedBehaviorInterface,
        ParcellsSegmentationInterface=ParcellsSegmentationInterface,
    )

    def __init__(
        self,
        excitation_type_channel_combination: dict,
        source_data: Dict[str, dict],
        ophys_metadata: Dict[str, dict],
        verbose: bool = True,
    ):
        self.excitation_type_channel_combination = excitation_type_channel_combination
        for excitation_type, channel in self.excitation_type_channel_combination.items():
            suffix = f"{excitation_type}Excitation{channel}Channel"
            interface_name = f"Imaging{suffix}"
            self.data_interface_classes[interface_name] = MesoscopicImagingMultiTiffSingleFrameInterface
            interface_name = f"DFFImaging{suffix}"
            self.data_interface_classes[interface_name] = ProcessedImagingInterface
        # After the imaging interfaces, so that the imaging planes exist when the parcels are added
        self.data_interface_classes["AllenParcels"] = AllenParcelsInterface

        self.verbose = verbose
        self._validate_source_data(source_data=source_data, verbose=self.verbose)

        self.data_interface_objects = {
            name: data_interface(**source_data[name])
            for name, data_interface in self.data_interface_classes.items()
            if name in source_data
        }

        self.ophys_metadata = ophys_metadata

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        metadata["Ophys"]["Device"] = self.ophys_metadata["Ophys"]["Device"]
        metadata["Ophys"]["OnePhotonSeries"] = self.ophys_metadata["Ophys"]["OnePhotonSeries"]
        metadata["Ophys"]["ImagingPlane"] = self.ophys_metadata["Ophys"]["ImagingPlane"]

        if "ParcellsSegmentationInterface" in self.data_interface_objects.keys():
            parcells_segmentation_metadata = self.data_interface_objects["ParcellsSegmentationInterface"].get_metadata()
            for segmentation_metadata_ind in range(
                len(parcells_segmentation_metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"])
            ):
                metadata["Ophys"]["ImageSegmentation"]["plane_segmentations"][segmentation_metadata_ind][
                    "imaging_plane"
                ] = self.ophys_metadata["Ophys"]["ImagingPlane"][2][
                    "name"
                ]  # Green excitation Red Channel, the parcellation is of the calcium DF/F

        return metadata

    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["Spike2Signals"]

        # Synch imaging
        for excitation_type, channel in self.excitation_type_channel_combination.items():
            imaging_interface = self.data_interface_objects[f"Imaging{excitation_type}Excitation{channel}Channel"]
            stream_id = next(
                (
                    stream_id
                    for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                    if stream_name == f"TTLSignal{excitation_type}LED"
                ),
                None,
            )
            ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
            imaging_interface.set_aligned_starting_time(ttl_times[0])

            # Synch processing imaging
            if f"DFFImaging{excitation_type}Excitation{channel}Channel" in self.data_interface_objects.keys():
                dff_imaging_interface = self.data_interface_objects[
                    f"DFFImaging{excitation_type}Excitation{channel}Channel"
                ]
                dff_imaging_interface.set_aligned_starting_time(ttl_times[FIRST_DFF_FRAME_INDEX])

            # The Allen parcel traces are averages of the DF/F frames, so they start with them
            if "AllenParcels" in self.data_interface_objects.keys():
                channel_name = excitation_type.lower() if excitation_type != "Violet" else "uv"
                self.data_interface_objects["AllenParcels"].set_aligned_starting_time(
                    channel=channel_name, starting_time=ttl_times[FIRST_DFF_FRAME_INDEX]
                )

            # Synch parcellated output, which is computed on the Green excitation (calcium) DF/F
            if excitation_type == "Green" and "ParcellsSegmentationInterface" in self.data_interface_objects.keys():
                parcells_segmentation_interface = self.data_interface_objects["ParcellsSegmentationInterface"]
                parcells_segmentation_interface.set_aligned_starting_time(ttl_times[FIRST_PARCELLATED_FRAME_INDEX])

        # Synch behaviour: video frame i is at pupil camera pulse i, as in the lab's analysis code
        stream_id = next(
            (
                stream_id
                for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                if stream_name == "TTLSignalPupilCamera"
            ),
            None,
        )
        pupil_camera_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)

        if "Video" in self.data_interface_objects.keys():
            video_interface = self.data_interface_objects["Video"]
            num_video_frames = len(video_interface.get_original_timestamps()[0])
            if len(pupil_camera_times) < num_video_frames:
                raise ValueError(
                    f"Fewer pupil camera pulses ({len(pupil_camera_times)}) than video frames ({num_video_frames})."
                )
            video_interface.set_aligned_timestamps([pupil_camera_times[:num_video_frames]])

        if "FacemapInterface" in self.data_interface_objects.keys():
            facemap_interface = self.data_interface_objects["FacemapInterface"]
            num_facemap_frames = len(facemap_interface.get_original_timestamps())
            if len(pupil_camera_times) < num_facemap_frames:
                raise ValueError(
                    f"Fewer pupil camera pulses ({len(pupil_camera_times)}) than FaceMap frames ({num_facemap_frames})."
                )
            facemap_interface.set_aligned_timestamps(pupil_camera_times[:num_facemap_frames])
