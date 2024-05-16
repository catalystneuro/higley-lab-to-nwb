"""Primary NWBConverter class for this dataset."""


from neuroconv import NWBConverter
from neuroconv.datainterfaces import ScanImageMultiFileImagingInterface

class Benisty2024NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        TwoPhotonImagingGreenChannel=ScanImageMultiFileImagingInterface,
    )