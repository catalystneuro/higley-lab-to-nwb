"""A segmentation extractor for Suite2p.

Classes
-------
Suite2pSegmentationExtractor
    A segmentation extractor for Suite2p.
"""

import scipy.io
import json
import numpy as np
from neuroconv.utils import FilePathType
from roiextractors.extraction_tools import _image_mask_extractor
from roiextractors.segmentationextractor import SegmentationExtractor


class Benisty2024CidanSegmentationExtractor(SegmentationExtractor):
    """A segmentation extractor for CIDAN."""

    extractor_name = "Benisty2024CidanSegmentationExtractor"
    installed = True  # check at class level if installed or not
    is_writable = False
    mode = "file"
    installation_mesg = ""  # error message when not installed

    def __init__(
        self,
        parameters_file_path: FilePathType,
        roi_list_file_path: FilePathType,
        mat_file_path: FilePathType,
        sampling_frequency: float,
    ):
        """Create SegmentationExtractor object out of CIDAN data type.

        Parameters
        ----------
        parameters_file_path: str or Path
            The path to the CIDAN parameter .json file.
        roi_list_file_path: str or Path
            The path to the CIDAN roi_list .json file.
        mat_file_path: str or Path
            The path to the CIDAN df/f traces .mat file.
        """
        self.parameters_file_path = parameters_file_path
        self.roi_list_file_path = roi_list_file_path
        self.mat_file_path = mat_file_path
        super().__init__()

        self._sampling_frequency = sampling_frequency

        mat_contents = scipy.io.loadmat(self.mat_file_path)
        self._roi_response_denoised = np.array(mat_contents["deltafoverf"]).T

        self._image_size = (512, 512)

        self._image_masks = _image_mask_extractor(
            self.get_roi_pixel_masks(),
            self.get_roi_ids(),
            self.get_image_size(),
        )

    def get_roi_pixel_masks(self, roi_ids=None):
        pixel_mask = []
        with open(self.roi_list_file_path) as file:
            roi_list = json.load(file)
            for roi in roi_list:
                pixel_mask.append(np.stack([[x, y, 1] for [x, y] in roi["coordinates"]]))

        if roi_ids is None:
            roi_idx_ = range(self.get_num_rois())
        else:
            roi_idx = [np.where(np.array(i) == self.get_roi_ids())[0] for i in roi_ids]
            ele = [i for i, j in enumerate(roi_idx) if j.size == 0]
            roi_idx_ = [j[0] for i, j in enumerate(roi_idx) if i not in ele]
        return [pixel_mask[i] for i in roi_idx_]

    def get_image_size(self):
        return self._image_size

    def get_accepted_list(self):
        return self.get_roi_ids()

    def get_rejected_list(self):
        roi_list = self.get_roi_ids()
        return np.zeros((len(roi_list)))

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency
