"""A segmentation extractor for Higley Lab parcellation output.

Classes
-------
ParcellsSegmentationExtractor
    A segmentation extractor for Higley Lab parcellation output.
"""

from scipy.io import loadmat
import numpy as np
from neuroconv.utils import FilePathType
from roiextractors.extraction_tools import _image_mask_extractor
from roiextractors.segmentationextractor import SegmentationExtractor


def _get_pixel_coordinate(pixel_num, n_cols: int) -> np.ndarray:
    row = (pixel_num - 1) // n_cols
    col = (pixel_num - 1) % n_cols
    return [row[0], col[0], 1]

class ParcellsSegmentationExtractor(SegmentationExtractor):
    """A segmentation extractor for Higley Lab parcellation output."""

    extractor_name = "ParcellsSegmentationExtractor"

    def __init__(
        self,
        mat_file_path: FilePathType,
        sampling_frequency: float,
        image_size: list,
    ):
        """Create SegmentationExtractor object out of CIDAN data type.

        Parameters
        ----------
        mat_file_path: str or Path
            The path to the parcellation output .mat file.
        sampling_frequency: float
            The sampling frequency for the df/f traces.
        image_size: list
            The frame dimension, [n_rows, n_cols].
        """
        self.mat_file_path = mat_file_path
        super().__init__()

        self._sampling_frequency = sampling_frequency

        parcels_time_trace = loadmat(mat_file_path, variable_names=["parcels_time_trace"])
        self._roi_response_raw = parcels_time_trace["parcels_time_trace"].T

        self._image_size = image_size
        self._image_masks = _image_mask_extractor(
            self.get_roi_pixel_masks(),
            self.get_roi_ids(),
            self.get_image_size(),
        )

        parcels_gal = loadmat(mat_file_path, variable_names=["parcels_gal"])
        self._pixel_list_per_roi = np.array(parcels_gal["parcels_gal"][0]["ROI_list"][0]["pixel_list"][0])

        assert len(self._pixel_list_per_roi) == self._roi_response_raw.shape[1], (
            f"Number of ROIs in 'parcels_gal' ({len(self._pixel_list_per_roi)}) must match the number of fluorescent "
            f"traces in 'parcels_time_trace' ({self._roi_response_raw.shape[1]})"
        )

        self.pixel_masks = []
        for pixel_list in self._pixel_list_per_roi:
            self.pixel_masks.append(
                [
                    _get_pixel_coordinate(pixel_num=pixel_num, n_cols=self._image_size[1])
                    for pixel_num in pixel_list
                ]
            )

    def get_roi_pixel_masks(self, roi_ids=None):
        if roi_ids is None:
            roi_idx_ = range(self.get_num_rois())
        else:
            roi_idx = [np.where(np.array(i) == self.get_roi_ids())[0] for i in roi_ids]
            ele = [i for i, j in enumerate(roi_idx) if j.size == 0]
            roi_idx_ = [j[0] for i, j in enumerate(roi_idx) if i not in ele]
        return [self.pixel_masks[i] for i in roi_idx_]

    def get_accepted_list(self):
        return self.get_roi_ids()

    def get_rejected_list(self):
        roi_list = self.get_roi_ids()
        return np.zeros((len(roi_list)))

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_image_size(self):
        return self._image_size
