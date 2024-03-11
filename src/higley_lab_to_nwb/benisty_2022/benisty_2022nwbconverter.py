"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter

from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2ttlinterface import Benisty2022Spike2TTLInterface


class Benisty2022NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        TTLSignalBlueLED=Benisty2022Spike2TTLInterface,
        TTLSignalVioletLED=Benisty2022Spike2TTLInterface,
        TTLSignalGreenLED=Benisty2022Spike2TTLInterface,
        TTLSignalMesoscopicCamera=Benisty2022Spike2TTLInterface,
        TTLSignalRedMesoscopicCamera=Benisty2022Spike2TTLInterface,
        TTLSignalPupilCamera=Benisty2022Spike2TTLInterface,
        Wheel=Benisty2022Spike2TTLInterface,
    )
