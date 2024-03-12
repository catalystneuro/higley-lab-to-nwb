"""Primary class for converting experiment-specific behavior."""

from pathlib import Path
from natsort import natsorted
from datetime import datetime
import tifffile
import numpy as np
from typing import Union, Optional, Tuple, Literal
from copy import deepcopy
from neuroconv.utils import FolderPathType, FilePathType
from neuroconv.utils.dict import DeepDict
from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface
from roiextractors.extractors.tiffimagingextractors.tiffimagingextractor import TiffImagingExtractor

class Benisty2022ImagingInterface(BaseImagingExtractorInterface):
    """Data Interface for writing imaging data for the Higley lab to NWB file using TiffImagingExtractor."""

    Extractor = TiffImagingExtractor

    def __init__(
        self,
        file_path : FilePathType,
        sampling_frequency: float,
        channel: str,
        excitation_type: str,
        verbose: bool = True,
    ):
        """
        Initialize reading of TIFF file.

        Parameters
        ----------
        file_path : FilePathType
        sampling_frequency : float
        verbose : bool, default: True
        """
        self.channel = channel
        self.excitation_type = excitation_type
        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, verbose=verbose)

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        indicators = dict(Red="ACh3.0", Green="jRCaMP1b")

        excitation_lambdas = dict(Blue=470.0, UV=395.0, Green=575.0)

        channel_metadata = {
            "Green": {
                "name": "Green",
                "emission_lambda": 525.0,
                "description": "Green channel of the microscope, 525/50 nm filter.",
            },
            "Red": {
                "name": "Red",
                "emission_lambda": 630.0,
                "description": "Red channel of the microscope, 630/75 nm filter.",
            },
        }[self.channel]

        optical_channel_metadata = channel_metadata

        device_name = "CustomMicroscope"
        metadata["Ophys"]["Device"][0].update(
            name=device_name,
            description="Camera Type: DUAL_DCAM, Camera Name: C13440-20C S/N: 301751 S/N: 300073",
            manufacturer="Hamamatsu Inc.",
        )

        indicator = indicators[self.channel]
        excitation_lambda = excitation_lambdas[self.excitation_type]

        suffix = f"{self.excitation_type}Excitation{self.channel}Channel"
        imaging_plane_name = f"ImagingPlane{suffix}"
        imaging_plane_metadata = metadata["Ophys"]["ImagingPlane"][0]
        imaging_plane_metadata.update(
            name=imaging_plane_name,
            optical_channel=[optical_channel_metadata],
            device=device_name,
            excitation_lambda=excitation_lambda,
            indicator=indicator,
            imaging_rate=self.imaging_extractor.get_sampling_frequency(),
            location="whole brain",  # TODO check
            # grid_spacing=grid_spacing,
            # grid_spacing_unit="meters",
        )

        two_photon_series_metadata = metadata["Ophys"]["OnePhotonSeries"][0]
        two_photon_series_metadata.update(
            name=f"OnePhotonSeries{suffix}",
            imaging_plane=imaging_plane_name,
            description=f"imaging data acuired through the {self.channel} upon {self.excitation_type} light excitation",
            unit="n.a.",
            # field_of_view=field_of_view,
            # dimension=image_size_in_pixels,
        )

        return metadata
