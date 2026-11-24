"""A segmentation extractor for the output of the CIDAN software."""

import json
from pathlib import Path

import numpy as np
import scipy.io
from roiextractors.segmentationextractor import SegmentationExtractor, _ROIMasks, _RoiResponse


class CidanSegmentationExtractor(SegmentationExtractor):
    """A segmentation extractor for CIDAN."""

    extractor_name = "CidanSegmentationExtractor"

    def __init__(
        self,
        parameters_file_path: str | Path,
        roi_list_file_path: str | Path,
        mat_file_path: str | Path,
        sampling_frequency: float,
        image_size: list,
    ):
        """
        Parameters
        ----------
        parameters_file_path : str or Path
            The path to the CIDAN parameter .json file.
        roi_list_file_path : str or Path
            The path to the CIDAN roi_list .json file.
        mat_file_path : str or Path
            The path to the CIDAN DF/F traces .mat file.
        sampling_frequency : float
            The sampling frequency of the DF/F traces.
        image_size : list
            The frame dimension.
        """
        super().__init__()
        self.parameters_file_path = parameters_file_path
        self.roi_list_file_path = roi_list_file_path
        self.mat_file_path = mat_file_path
        self._sampling_frequency = sampling_frequency
        self._image_shape = tuple(image_size)

        traces = np.array(scipy.io.loadmat(self.mat_file_path)["deltafoverf"]).T
        with open(self.roi_list_file_path) as file:
            roi_list = json.load(file)
        pixel_masks = [np.array([[x, y, 1] for x, y in roi["coordinates"]]) for roi in roi_list]

        roi_ids = list(range(len(pixel_masks)))
        self._roi_ids = roi_ids
        self._roi_masks = _ROIMasks(
            data=pixel_masks,
            mask_tpe="nwb-pixel_mask",
            field_of_view_shape=self._image_shape,
            roi_id_map={roi_id: index for index, roi_id in enumerate(roi_ids)},
        )
        self._roi_responses.append(_RoiResponse("denoised", traces, roi_ids))

        with open(self.parameters_file_path) as file:
            self.parameters_dict = json.load(file)
        # Keep only the parameters that describe the segmentation algorithm
        self.parameters_dict.pop("dataset_params")
        self.parameters_dict.pop("global_params")

    def get_frame_shape(self) -> tuple[int, int]:
        return self._image_shape

    def get_sampling_frequency(self) -> float:
        return self._sampling_frequency

    def get_native_timestamps(self, start_sample: int | None = None, end_sample: int | None = None) -> None:
        return None
