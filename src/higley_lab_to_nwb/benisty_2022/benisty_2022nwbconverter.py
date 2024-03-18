"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2events_interface import Benisty2022Spike2EventsInterface
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2recording_interface import Benisty2022Spike2RecordingInterface
from higley_lab_to_nwb.benisty_2022.benisty_2022_imaginginterface import Benisty2022ImagingInterface


class Benisty2022NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        TTLSignals=Benisty2022Spike2EventsInterface,
        Wheel=Benisty2022Spike2RecordingInterface,
        ImagingBlueExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingBlueExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingUVExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingUVExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationRedChannel=Benisty2022ImagingInterface,
    )
