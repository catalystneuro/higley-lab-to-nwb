"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    TiffImagingInterface,
)

from higley_lab_to_nwb.benisty_2022.benisty_2022_imaginginterface import Benisty2022ImagingInterface


class Benisty2022NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        ImagingBlueExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingBlueExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingUVExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingUVExcitationRedChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationGreenChannel=Benisty2022ImagingInterface,
        ImagingGreenExcitationRedChannel=Benisty2022ImagingInterface,
    )
