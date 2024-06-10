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
class Lohani2022MesoscopicImagingInterface(BaseImagingExtractorInterface):
    """Data Interface for writing imaging data for the Higley lab to NWB file using TiffImagingExtractor."""

    Extractor = TiffImagingExtractor

    def __init__(
        self,
        file_path : FilePathType,
        sampling_frequency: float,
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
        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, verbose=verbose, photon_series_type="OnePhotonSeries")

    def get_metadata_schema(self):
        metadata_schema=super().get_metadata_schema()
        return metadata_schema
    
    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        return metadata
