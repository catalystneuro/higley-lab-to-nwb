"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter

from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2events_interface import Benisty2022Spike2EventsInterface
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2recording_interface import Benisty2022Spike2RecordingInterface
from neuroconv.datainterfaces import VideoInterface


class Benisty2022NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        TTLSignals=Benisty2022Spike2EventsInterface, Wheel=Benisty2022Spike2RecordingInterface, Video=VideoInterface
    )

    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["TTLSignals"]
        video_interface = self.data_interface_objects["Video"]
        video_interface._timestamps = video_interface.get_timestamps()
        stream_id = next(
            (
                stream_id
                for stream_id, stream_name in ttlsignal_interface.stream_ids_to_names_map.items()
                if stream_name == "TTLSignalPupilCamera"
            ),
            None,
        )
        ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
        video_interface.set_aligned_starting_time(ttl_times[0])
