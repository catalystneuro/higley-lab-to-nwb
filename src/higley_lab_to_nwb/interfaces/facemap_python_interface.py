"""Facemap output from the Python implementation of Facemap (.npy converted to .mat), as used in Benisty 2024.

The output of the MATLAB Facemap GUI is read with neuroconv.datainterfaces.FacemapInterface.
"""

from pathlib import Path
from typing import Literal, Optional

import numpy as np
import scipy.io
from ndx_facemap_motionsvd import MotionSVDMasks, MotionSVDSeries
from neuroconv import BaseTemporalAlignmentInterface
from neuroconv.datainterfaces.behavior.video.video_utils import get_video_timestamps
from neuroconv.tools import get_module
from neuroconv.utils import DeepDict, get_base_schema, get_schema_from_hdmf_class
from pynwb.base import TimeSeries
from pynwb.behavior import EyeTracking, PupilTracking, SpatialSeries
from pynwb.core import DynamicTableRegion
from pynwb.file import NWBFile


class FacemapPythonInterface(BaseTemporalAlignmentInterface):
    display_name = "FacemapPython"
    help = "Interface for Facemap output generated with the Python implementation of Facemap software."  # TODO check with the point person

    keywords = ["eye tracking"]

    def __init__(
        self,
        mat_file_path: str | Path,
        video_file_path: str | Path,
        first_n_components: int = 500,
        svd_mask_names: list = ["Face"],
        verbose: bool = True,
    ):
        """
        Load and prepare data for facemap.

        Parameters
        ----------
        mat_file_path : string or Path
            Path to the .mat file.
        original_timestamps : list
            The original timestamps from the behavioural video.
        first_n_components : int, default: 500
            Number of components to store.
        svd_mask_names : list, default: ["Face", "Whiskers"]
            List of names for the motion SVD ROIs.
        verbose : bool, default: True
            Allows verbose.
        """
        super().__init__(mat_file_path=mat_file_path, video_file_path=video_file_path, verbose=verbose)
        self.first_n_components = first_n_components
        self.original_timestamps = None
        self.timestamps = None
        self.svd_mask_names = svd_mask_names

        try:
            face_motion = scipy.io.loadmat(mat_file_path, variable_names=["motion_0"])
            # TODO remove this line of code once we have the actual timestamps from the original video
            self.original_timestamps = list(range(face_motion["motion_0"].shape[1]))
        except NotImplementedError:
            print("The .mat file is not in HDF5 format")
        except Exception as e:
            print(f"An error occurred with scipy.io.loadmat: {e}")

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Behavior"] = get_base_schema(tag="Behavior")
        spatial_series_metadata_schema = get_schema_from_hdmf_class(SpatialSeries)
        time_series_metadata_schema = get_schema_from_hdmf_class(TimeSeries)
        metadata_schema["properties"]["Behavior"].update(
            required=["EyeTracking", "PupilTracking", "MotionSVDMasks", "MotionSVDSeries"],
            properties=dict(
                EyeTracking=dict(
                    type="array",
                    minItems=1,
                    items=spatial_series_metadata_schema,
                ),
                PupilTracking=dict(
                    type="array",
                    minItems=1,
                    items=time_series_metadata_schema,
                ),
                MotionSVDMasks=dict(
                    type="object",
                    properties=dict(
                        name=dict(type="string"),
                        description=dict(type="string"),
                    ),
                    required=["name", "description"],
                ),
                MotionSVDSeries=dict(
                    type="object",
                    properties=dict(
                        name=dict(type="string"),
                        description=dict(type="string"),
                    ),
                    required=["name", "description"],
                ),
            ),
        )

        return metadata_schema

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        behavior_metadata = dict(
            EyeTracking=[
                dict(
                    name="eye_center_of_mass",
                    description="The position of the eye measured in degrees.",
                    reference_frame="unknown",
                    unit="degrees",
                ),
                dict(
                    name="eye_center_of_mass_smooth",
                    description="The preprocessed position of the eye measured in degrees.",
                    reference_frame="unknown",
                    unit="degrees",
                ),
            ],
            PupilTracking=[
                dict(name="pupil_area", description="Area of pupil.", unit="unknown"),
                dict(name="pupil_area_smooth", description="Preprocessed area of pupil.", unit="unknown"),
            ],
            MotionSVDMasks=dict(name="MotionSVDMasks", description="Motion masks"),
            MotionSVDSeries=dict(name="MotionSVDSeries", description="Motion SVD components"),
        )
        metadata["Behavior"] = behavior_metadata
        return metadata

    def add_eye_tracking(
        self, nwbfile: NWBFile, metadata: DeepDict, eye_tracking_trace_type: Literal["com_smooth", "com"] = "com"
    ):

        if self.timestamps is None:
            self.timestamps = self.get_timestamps()

        pupil_data = scipy.io.loadmat(self.source_data["mat_file_path"], variable_names=["pupil"])
        if pupil_data["pupil"].size == 0:
            print(f"No eye tracking data available in {self.source_data['mat_file_path']}")
            return

        data = pupil_data["pupil"][0, 0][eye_tracking_trace_type][0, 0]

        behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")
        eye_tracking_metadata_ind = 0 if eye_tracking_trace_type == "com" else 1
        eye_tracking_metadata = metadata["Behavior"]["EyeTracking"][eye_tracking_metadata_ind]

        eye_com = SpatialSeries(
            name=eye_tracking_metadata["name"],
            description=eye_tracking_metadata["description"],
            data=data,
            reference_frame=eye_tracking_metadata["reference_frame"],
            unit=eye_tracking_metadata["unit"],
            timestamps=self.timestamps,
        )
        if "EyeTracking" not in behavior_module.data_interfaces:
            eye_tracking = EyeTracking(name="EyeTracking")
            behavior_module.add(eye_tracking)
        else:
            eye_tracking = behavior_module.data_interfaces["EyeTracking"]

        eye_tracking.add_spatial_series(eye_com)

    def add_pupil_data(
        self, nwbfile: NWBFile, metadata: DeepDict, pupil_trace_type: Literal["area_smooth", "area"] = "area"
    ):
        if self.timestamps is None:
            self.timestamps = self.get_timestamps()
        pupil_data = scipy.io.loadmat(self.source_data["mat_file_path"], variable_names=["pupil"])
        if pupil_data["pupil"].size == 0:
            print(f"No pupil area data available in {self.source_data['mat_file_path']}")
            return

        data = pupil_data["pupil"][0, 0][pupil_trace_type][0, 0].T
        behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")

        pupil_area_metadata_ind = 0 if pupil_trace_type == "area" else 1
        pupil_area_metadata = metadata["Behavior"]["PupilTracking"][pupil_area_metadata_ind]

        pupil_trace = TimeSeries(
            name=pupil_area_metadata["name"],
            description=pupil_area_metadata["description"],
            data=data,
            unit=pupil_area_metadata["unit"],
            timestamps=self.timestamps,
        )

        if "PupilTracking" not in behavior_module.data_interfaces:
            pupil_tracking = PupilTracking(name="PupilTracking")
            behavior_module.add(pupil_tracking)
        else:
            pupil_tracking = behavior_module.data_interfaces["PupilTracking"]

        pupil_tracking.add_timeseries(pupil_trace)

    def add_motion_SVD(self, nwbfile: NWBFile, metadata: DeepDict, mask_index: int = 0, mask_name: str = "Face"):
        """
        Add data motion SVD and motion mask for the whole video.

        Parameters
        ----------
        nwbfile : NWBFile
            NWBFile to add motion SVD components data to.
        """

        # From documentation
        # motSVD: cell array of motion SVDs [time x components] (in order: face, ROI1, ROI2, ROI3)
        # uMotMask: cell array of motion masks [pixels x components]  (in order: face, ROI1, ROI2, ROI3)
        # motion masks of face are reported as 2D-arrays npixels x
        if self.timestamps is None:
            self.timestamps = self.get_timestamps()

        motion_mask_name = metadata["Behavior"]["MotionSVDMasks"]["name"]
        motion_mask_description = metadata["Behavior"]["MotionSVDMasks"]["description"]
        motion_series_name = metadata["Behavior"]["MotionSVDSeries"]["name"]
        motion_series_description = metadata["Behavior"]["MotionSVDSeries"]["description"]

        behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")

        mask_variable_name = f"motMask_reshape_{mask_index}"
        face_motion_masks = scipy.io.loadmat(self.source_data["mat_file_path"], variable_names=[mask_variable_name])
        face_motion_masks = face_motion_masks[mask_variable_name]
        if face_motion_masks.size == 0:
            print(f"No {mask_name} motion components data available in {self.source_data['mat_file_path']}")
            return

        mask_coordinates = [0, 0, face_motion_masks.shape[1], face_motion_masks.shape[0]]

        # store face motion mask and motion series
        motion_masks_table = MotionSVDMasks(
            name=f"{motion_mask_name}{mask_name}",
            description=f"{motion_mask_description} for face components.",
            mask_coordinates=mask_coordinates,
            downsampling_factor=self._get_downsamplig_factor(),
            processed_frame_dimension=self._get_processed_frame_dimension(),
        )

        for c in range(self.first_n_components):
            component = face_motion_masks[:, :, c]
            motion_masks_table.add_row(image_mask=component.T, check_ragged=False)

        motion_masks = DynamicTableRegion(
            name="motion_masks",
            data=list(range(self.first_n_components)),
            description=f"{self.first_n_components} components of {mask_name} motion mask",
            table=motion_masks_table,
        )

        series_variable_name = f"motSVD_{mask_index}"
        face_motion_series = scipy.io.loadmat(self.source_data["mat_file_path"], variable_names=[series_variable_name])
        face_motion_series = face_motion_series[series_variable_name]

        motion_series = MotionSVDSeries(
            name=f"{motion_series_name}{mask_name}",
            description=f"{motion_series_description} for {mask_name} components.",
            data=face_motion_series[:, : self.first_n_components],
            motion_masks=motion_masks,
            unit="unknown",
            timestamps=self.timestamps,
        )
        behavior_module.add(motion_masks_table)
        behavior_module.add(motion_series)

        return

    def get_original_timestamps(self) -> np.ndarray:
        if self.original_timestamps is None:
            self.original_timestamps = get_video_timestamps(self.source_data["video_file_path"])
        return self.original_timestamps

    def get_timestamps(self) -> np.ndarray:
        if self.timestamps is None:
            return self.get_original_timestamps()
        else:
            return self.timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self.timestamps = aligned_timestamps

    def _get_downsamplig_factor(self) -> float:
        downsamplig_factor = scipy.io.loadmat(self.source_data["mat_file_path"], variable_names=["sbin"])
        return float(downsamplig_factor["sbin"][0, 0])

    def _get_processed_frame_dimension(self) -> np.ndarray:
        frame_dimension = scipy.io.loadmat(self.source_data["mat_file_path"], variable_names=["LXbin", "LYbin"])
        return [frame_dimension["LXbin"][0, 0], frame_dimension["LYbin"][0, 0]]

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: Optional[dict] = None,
        compression: Optional[str] = "gzip",
        compression_opts: Optional[int] = None,
    ):
        """
        Add facemap data to NWBFile.

        Parameters
        ----------
        nwbfile : NWBFile
            NWBFile to add facemap data to.
        metadata : dict, optional
            Metadata to add to the NWBFile.
        compression : str, optional
            Compression type.
        compression_opts : int, optional
            Compression options.
        """
        if metadata is None:
            metadata = self.get_metadata()
        self.add_eye_tracking(nwbfile=nwbfile, metadata=metadata, eye_tracking_trace_type="com")
        self.add_pupil_data(nwbfile=nwbfile, metadata=metadata, pupil_trace_type="area")
        self.add_eye_tracking(nwbfile=nwbfile, metadata=metadata, eye_tracking_trace_type="com_smooth")
        self.add_pupil_data(nwbfile=nwbfile, metadata=metadata, pupil_trace_type="area_smooth")

        if len(self.svd_mask_names) > 1:
            for mask_index, mask_name in enumerate(self.svd_mask_names):
                self.add_motion_SVD(nwbfile=nwbfile, metadata=metadata, mask_index=mask_index, mask_name=mask_name)
