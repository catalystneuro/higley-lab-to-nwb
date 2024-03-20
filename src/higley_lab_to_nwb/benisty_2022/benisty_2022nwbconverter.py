"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter

from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2events_interface import Benisty2022Spike2EventsInterface
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2recording_interface import Benisty2022Spike2RecordingInterface
from neuroconv.datainterfaces import VideoInterface


class Benisty2022NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        TTLSignals=Benisty2022Spike2EventsInterface,
        Wheel=Benisty2022Spike2RecordingInterface,
        Video=VideoInterface
    )

