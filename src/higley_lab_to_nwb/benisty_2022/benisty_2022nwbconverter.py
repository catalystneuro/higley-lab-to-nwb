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
        ImagingUVExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingUVExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationRedChannel=Benisty2022ImagingInterface,
    )

    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["Spike2Signals"]
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
