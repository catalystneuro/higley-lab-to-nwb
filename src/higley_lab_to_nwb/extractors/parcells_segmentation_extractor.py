"""A segmentation extractor for the Higley Lab parcellation output."""

from pathlib import Path

import numpy as np
from roiextractors.segmentationextractor import SegmentationExtractor, _ROIMasks, _RoiResponse
from scipy.io import loadmat


def _get_pixel_coordinate(pixel_num, n_cols: int, n_rows: int) -> list:
    """(row, column, weight) of a 1-based MATLAB (column-major) linear pixel index.

    The coordinate follows the orientation of ProcessedImagingExtractor.get_series, so that the masks overlay the
    DF/F frames.
    """
    pixel_num = np.asarray(pixel_num).reshape(-1)[0]
    row = (pixel_num - 1) % n_rows
    col = (pixel_num - 1) // n_rows
    return [n_rows - 1 - col, n_cols - 1 - row, 1]


class ParcellsSegmentationExtractor(SegmentationExtractor):
    """The functional parcellation of the lab's code: ROI pixel lists and the mean DF/F over each ROI."""

    extractor_name = "ParcellsSegmentationExtractor"

    def __init__(self, file_path: str | Path, sampling_frequency: float, image_size: list):
        """
        Parameters
        ----------
        file_path : str or Path
            The path to the parcellation output .mat file.
        sampling_frequency : float
            The sampling frequency of the traces.
        image_size : list
            The frame dimension, [n_rows, n_cols].
        """
        super().__init__()
        self.file_path = file_path
        self._sampling_frequency = sampling_frequency
        self._image_shape = tuple(image_size)
        n_rows, n_cols = self._image_shape

        traces = loadmat(file_path, variable_names=["parcels_time_trace"])["parcels_time_trace"].T
        parcels_gal = loadmat(file_path, variable_names=["parcels_gal"])["parcels_gal"]
        pixel_list_per_roi = parcels_gal[0]["ROI_list"][0]["pixel_list"][0]
        if len(pixel_list_per_roi) != traces.shape[1]:
            raise ValueError(
                f"Number of ROIs in 'parcels_gal' ({len(pixel_list_per_roi)}) does not match the number of traces in "
                f"'parcels_time_trace' ({traces.shape[1]})."
            )

        roi_ids = list(range(traces.shape[1]))
        pixel_masks = [
            np.array([_get_pixel_coordinate(pixel_num, n_cols=n_cols, n_rows=n_rows) for pixel_num in pixel_list])
            for pixel_list in pixel_list_per_roi
        ]
        self._roi_ids = roi_ids
        self._roi_masks = _ROIMasks(
            data=pixel_masks,
            mask_tpe="nwb-pixel_mask",
            field_of_view_shape=self._image_shape,
            roi_id_map={roi_id: index for index, roi_id in enumerate(roi_ids)},
        )
        self._roi_responses.append(_RoiResponse("dff", traces, roi_ids))

    def get_frame_shape(self) -> tuple[int, int]:
        return self._image_shape

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_native_timestamps(self, start_sample: int | None = None, end_sample: int | None = None) -> None:
        return None
