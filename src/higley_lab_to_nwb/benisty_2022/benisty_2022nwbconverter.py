"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2signals_interface import Benisty2022Spike2SignalsInterface
from higley_lab_to_nwb.benisty_2022.benisty_2022_imaginginterface import Benisty2022ImagingInterface

from neuroconv.datainterfaces import VideoInterface, FacemapInterface


class Benisty2022NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        Spike2Signals=Benisty2022Spike2SignalsInterface, 
        Video=VideoInterface,
        FacemapInterface=FacemapInterface,
        ImagingBlueExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingBlueExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingVioletExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingVioletExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationRedChannel=Benisty2022ImagingInterface,
    )

    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["Spike2Signals"]
        # Synch imaging
        excitation_types = ["Blue", "Violet", "Green"]
        for excitation_type in excitation_types:
            imaging_interface_green = self.data_interface_objects[f"Imaging{excitation_type}ExcitationGreenChannel"]
            imaging_interface_red = self.data_interface_objects[f"Imaging{excitation_type}ExcitationRedChannel"]
            stream_id = next(
                (
                    stream_id
                    for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                    if stream_name == f"TTLSignal{excitation_type}LED"
                ),
                None,
            )
            ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
            imaging_interface_green.set_aligned_starting_time(ttl_times[0])
            imaging_interface_red.set_aligned_starting_time(ttl_times[0])

        # Synch behaviour
        video_interface = self.data_interface_objects["Video"]
        facemap_interface = self.data_interface_objects["FacemapInterface"]
        video_interface._timestamps = video_interface.get_timestamps()
        stream_id = next(
            (
                stream_id
                for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                if stream_name == "TTLSignalPupilCamera"
            ),
            None,
        )
        ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
        video_interface.set_aligned_starting_time(ttl_times[0])
        facemap_interface.set_aligned_starting_time(ttl_times[0])
