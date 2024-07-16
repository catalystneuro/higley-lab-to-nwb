import subprocess
import sys
from typing import Literal, Optional

import h5py
import numpy as np
from pynwb.base import TimeSeries
from pynwb.behavior import EyeTracking, PupilTracking, SpatialSeries
from pynwb.core import DynamicTableRegion
from pynwb.file import NWBFile

from neuroconv.utils.dict import DeepDict

from neuroconv import BaseTemporalAlignmentInterface
from neuroconv.tools import get_module
from neuroconv.utils import FilePathType, get_base_schema, get_schema_from_hdmf_class


def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


try:
    from ndx_facemap_motionsvd import MotionSVDMasks, MotionSVDSeries
except ImportError:
    # TODO: to be change when ndx-facemap-motionsvd version on pip
    install_package("git+https://github.com/catalystneuro/ndx-facemap-motionsvd.git@main")
    from ndx_facemap_motionsvd import MotionSVDMasks, MotionSVDSeries


class FacemapInterface(BaseTemporalAlignmentInterface):
    display_name = "Facemap"
    help = "Interface for Facemap output."

    keywords = ["eye tracking"]

    def __init__(
        self,
        mat_file_path: FilePathType,
        original_timestamps: list,
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
        super().__init__(mat_file_path=mat_file_path, verbose=verbose)
        self.first_n_components = first_n_components
        self.original_timestamps = original_timestamps
        self.timestamps = None
        self.svd_mask_names = svd_mask_names

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
                )
            ],
            PupilTracking=[
                dict(name="pupil_area", description="Area of pupil.", unit="unknown"),
                dict(name="pupil_area_raw", description="Raw unprocessed area of pupil.", unit="unknown"),
            ],
            MotionSVDMasks=dict(name="MotionSVDMasks", description="Motion masks"),
            MotionSVDSeries=dict(name="MotionSVDSeries", description="Motion SVD components"),
        )
        metadata["Behavior"] = behavior_metadata
        return metadata

    def add_eye_tracking(self, nwbfile: NWBFile, metadata: DeepDict):

        if self.timestamps is None:
            self.timestamps = self.get_timestamps()
        with h5py.File(self.source_data["mat_file_path"], "r") as file:
            data = file["proc"]["pupil"]["com"][:].T

        behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")
        eye_tracking_metadata = metadata["Behavior"]["EyeTracking"][0]

        eye_com = SpatialSeries(
            name=eye_tracking_metadata["name"],
            description=eye_tracking_metadata["description"],
            data=data,
            reference_frame=eye_tracking_metadata["reference_frame"],
            unit=eye_tracking_metadata["unit"],
            timestamps=self.timestamps,
        )

        eye_tracking = EyeTracking(name="EyeTracking", spatial_series=eye_com)

        behavior_module.add(eye_tracking)

    def add_pupil_data(
        self, nwbfile: NWBFile, metadata: DeepDict, pupil_trace_type: Literal["area_raw", "area"] = "area"
    ):

        with h5py.File(self.source_data["mat_file_path"], "r") as file:

            behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")

            pupil_area_metadata_ind = 0 if pupil_trace_type == "area" else 1
            pupil_area_metadata = metadata["Behavior"]["PupilTracking"][pupil_area_metadata_ind]

            if "EyeTracking" not in behavior_module.data_interfaces:
                self.add_eye_tracking(nwbfile=nwbfile, metadata=metadata)

            eye_tracking_name = metadata["Behavior"]["EyeTracking"][0]["name"]
            eye_com = behavior_module.data_interfaces["EyeTracking"].spatial_series[eye_tracking_name]

            pupil_trace = TimeSeries(
                name=pupil_area_metadata["name"],
                description=pupil_area_metadata["description"],
                data=file["proc"]["pupil"][pupil_trace_type][:].T,
                unit=pupil_area_metadata["unit"],
                timestamps=eye_com,
            )

            if "PupilTracking" not in behavior_module.data_interfaces:
                pupil_tracking = PupilTracking(name="PupilTracking")
                behavior_module.add(pupil_tracking)
            else:
                pupil_tracking = behavior_module.data_interfaces["PupilTracking"]

            pupil_tracking.add_timeseries(pupil_trace)

    def add_face_motion_SVD(self, nwbfile: NWBFile, metadata: DeepDict):
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

        with h5py.File(self.source_data["mat_file_path"], "r") as file:

            behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")

            # Extract mask_coordinates
            mask_coordinates = file[file[file["proc"]["ROI"][0][0]][0][0]]
            y1 = int(np.round(mask_coordinates[0][0]) - 1)  # correct matlab indexing
            x1 = int(np.round(mask_coordinates[1][0]) - 1)  # correct matlab indexing
            y2 = y1 + int(np.round(mask_coordinates[2][0]))
            x2 = x1 + int(np.round(mask_coordinates[3][0]))
            mask_coordinates = [x1, y1, x2, y2]

            # store face motion mask and motion series
            motion_masks_table = MotionSVDMasks(
                name=f"{motion_mask_name}Face",
                description=f"{motion_mask_description} for face.",
                mask_coordinates=mask_coordinates,
                downsampling_factor=self._get_downsamplig_factor(),
                processed_frame_dimension=self._get_processed_frame_dimension(),
            )

            # add face mask
            mask_ref = file["proc"]["uMotMask"][0][0]
            for c, component in enumerate(file[mask_ref]):
                if c == self.first_n_components:
                    break
                componendt_2d = component.reshape((y2 - y1, x2 - x1))
                motion_masks_table.add_row(image_mask=componendt_2d.T, check_ragged=False)

            motion_masks = DynamicTableRegion(
                name="motion_masks",
                data=list(range(len(file["proc"]["motSVD"][:]))),
                description="all the face motion mask",
                table=motion_masks_table,
            )

            series_ref = file["proc"]["motSVD"][0][0]
            data = np.array(file[series_ref])
            data = data[: self.first_n_components, :]

            motion_series = MotionSVDSeries(
                name=f"{motion_series_name}Face",
                description=f"{motion_series_description} for face.",
                data=data.T,
                motion_masks=motion_masks,
                unit="unknown",
                timestamps=self.timestamps,
            )
            behavior_module.add(motion_masks_table)
            behavior_module.add(motion_series)

        return

    def add_motion_SVD(self, nwbfile: NWBFile, metadata: DeepDict, ROI_index: int = 1, ROI_name: str = "ROI1"):
        """
        Add data motion SVD and motion mask for each ROI.

        Parameters
        ----------
        nwbfile : NWBFile
            NWBFile to add motion SVD components data to.
        """

        # From documentation
        # motSVD: cell array of motion SVDs [time x components] (in order: face, ROI1, ROI2, ROI3)
        # uMotMask: cell array of motion masks [pixels x components]  (in order: face, ROI1, ROI2, ROI3)
        # ROIs motion masks are reported as 3D-arrays x_pixels x y_pixels x components

        if self.timestamps is None:
            self.timestamps = self.get_timestamps()

        motion_mask_name = metadata["Behavior"]["MotionSVDMasks"]["name"]
        motion_mask_description = metadata["Behavior"]["MotionSVDMasks"]["description"]
        motion_series_name = metadata["Behavior"]["MotionSVDSeries"]["name"]
        motion_series_description = metadata["Behavior"]["MotionSVDSeries"]["description"]

        with h5py.File(self.source_data["mat_file_path"], "r") as file:

            behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="behavioral data")

            downsampling_factor = self._get_downsamplig_factor()
            processed_frame_dimension = self._get_processed_frame_dimension()

            # store ROIs motion mask and motion series

            series_ref = file["proc"]["motSVD"][ROI_index][0]
            mask_ref = file["proc"]["uMotMask"][ROI_index][0]

            # skipping the first ROI because it refers to "running" mask, from Facemap doc
            mask_coordinates = file[file["proc"]["locROI"][ROI_index][0]]
            y1 = int(np.round(mask_coordinates[0][0]) - 1)  # correct matlab indexing
            x1 = int(np.round(mask_coordinates[1][0]) - 1)  # correct matlab indexing
            y2 = y1 + int(np.round(mask_coordinates[2][0]))
            x2 = x1 + int(np.round(mask_coordinates[3][0]))
            mask_coordinates = [x1, y1, x2, y2]

            motion_masks_table = MotionSVDMasks(
                name=f"{motion_mask_name}{ROI_name}",
                description=f"{motion_mask_description} for {ROI_name}",
                mask_coordinates=mask_coordinates,
                downsampling_factor=downsampling_factor,
                processed_frame_dimension=processed_frame_dimension,
            )

            for c, component in enumerate(file[mask_ref]):
                if c == self.first_n_components:
                    break
                motion_masks_table.add_row(image_mask=component.T, check_ragged=False)

            motion_masks = DynamicTableRegion(
                name="motion_masks",
                data=list(range(self.first_n_components)),
                description="all the ROIs motion mask",
                table=motion_masks_table,
            )

            data = np.array(file[series_ref])
            data = data[: self.first_n_components, :]

            motion_series = MotionSVDSeries(
                name=f"{motion_series_name}{ROI_name}",
                description=f"{motion_series_description} for {ROI_name}",
                data=data.T,
                motion_masks=motion_masks,
                unit="unknown",
                timestamps=self.timestamps,
            )

            behavior_module.add(motion_masks_table)
            behavior_module.add(motion_series)

        return

    def get_original_timestamps(self) -> np.ndarray:
        return self.original_timestamps

    def get_timestamps(self) -> np.ndarray:
        if self.timestamps is None:
            return self.get_original_timestamps()
        else:
            return self.timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self.timestamps = aligned_timestamps

    def _get_downsamplig_factor(self) -> float:
        with h5py.File(self.source_data["mat_file_path"], "r") as file:
            downsamplig_factor = file["proc"]["sc"][0][0]
        return downsamplig_factor

    def _get_processed_frame_dimension(self) -> np.ndarray:
        with h5py.File(self.source_data["mat_file_path"], "r") as file:
            processed_frame_ref = file["proc"]["wpix"][0][0]
            frame = file[processed_frame_ref]
            return [frame.shape[1], frame.shape[0]]

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
        # self.add_eye_tracking(nwbfile=nwbfile, metadata=metadata)
        self.add_pupil_data(nwbfile=nwbfile, metadata=metadata, pupil_trace_type="area_raw")
        self.add_pupil_data(nwbfile=nwbfile, metadata=metadata, pupil_trace_type="area")
        self.add_face_motion_SVD(nwbfile=nwbfile, metadata=metadata)

        if len(self.svd_mask_names) > 1:
            for mask_index, mask_name in enumerate(self.svd_mask_names[1:]):
                self.add_motion_SVD(nwbfile=nwbfile, metadata=metadata, ROI_index=mask_index, ROI_name=mask_name)
