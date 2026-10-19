"""The DF/F of the Allen CCFv3 parcels, as the lab's pipeline computes them.

The lab's RegressionProcessing.m averages each channel's DF/F over the pixels of each of 56 Allen CCFv3 parcels
(pixels2rois.m) and saves the result as `dFoF_parcells` in final_dFoF_parcels.mat. The parcels themselves are
`parcells_new` in parcells_updated121519.mat, in the lab's code at
https://github.com/cardin-higley-lab/Lohani_Moberly_et_al_2022 (commit c337686,
Figure3ExtractStatesCorrelation/Functions/parcells_updated121519.mat). That repository has no license, so the file
is not copied here; pass its path.
"""

from typing import Optional

import h5py
import numpy as np
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import FilePathType
from pynwb import NWBFile
from pynwb.ophys import DfOverF, ImageSegmentation, RoiResponseSeries
from scipy.io import loadmat

from ..extractors.parcells_segmentation_extractor import _get_pixel_coordinate

# Parcels the paper leaves out of its analyses: "Some medial Allen parcels (PL, ACA, RSPv) were masked out because of
# prominent vasculature along the midline. Colliculus regions (SC, IC) were also removed, resulting in final 23 Allen
# CCFv3 parcels per hemisphere."
EXCLUDED_AREAS = {"PL", "ACA", "RSPv", "SC", "IC"}

# Channel of final_dFoF_parcels.mat -> the imaging plane of its DF/F, and what it measures.
CHANNELS = {
    "blue": ("ImagingPlaneBlueExcitationGreenChannel", "ACh3.0 (470 nm excitation)"),
    "uv": ("ImagingPlaneVioletExcitationGreenChannel", "the 395 nm control channel"),
    "green": ("ImagingPlaneGreenExcitationRedChannel", "jRCaMP1b (575 nm excitation)"),
}


class AllenParcelsInterface(BaseDataInterface):
    """The Allen CCFv3 parcels as one plane segmentation, with the DF/F of each channel averaged over each parcel."""

    def __init__(
        self,
        file_path: FilePathType,
        parcels_file_path: FilePathType,
        sampling_frequency: float,
        image_size: list = [256, 256],
        verbose: bool = True,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            The session's final_dFoF_parcels.mat.
        parcels_file_path : str or Path
            parcells_updated121519.mat from the lab's code (see the module docstring).
        sampling_frequency : float
            The frame rate of each channel's DF/F.
        image_size : list
            The frame dimension, [n_rows, n_cols], of the DF/F the parcels were drawn on.
        """
        super().__init__(
            file_path=file_path,
            parcels_file_path=parcels_file_path,
            sampling_frequency=sampling_frequency,
            image_size=image_size,
            verbose=verbose,
        )
        self.starting_times = {channel: None for channel in CHANNELS}

    def set_aligned_starting_time(self, channel: str, starting_time: float) -> None:
        """Set when the first DF/F frame of one channel ('blue', 'uv' or 'green') was acquired."""
        self.starting_times[channel] = starting_time

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        n_rows, n_cols = self.source_data["image_size"]
        parcels = loadmat(self.source_data["parcels_file_path"], squeeze_me=True, struct_as_record=False)
        parcels = parcels["parcells_new"]

        # The plane segmentation belongs to one imaging plane; the three channels are co-registered to the same
        # Allen-aligned frame, so the masks apply to each of them.
        imaging_plane = nwbfile.imaging_planes[CHANNELS["green"][0]]
        ophys = get_module(nwbfile, name="ophys", description="Processed optical physiology data.")
        if "ImageSegmentation" not in ophys.data_interfaces:
            ophys.add(ImageSegmentation(name="ImageSegmentation"))
        plane_segmentation = ophys["ImageSegmentation"].create_plane_segmentation(
            name="AllenParcelsPlaneSegmentation",
            description=(
                "The 56 Allen CCFv3 parcels (28 per hemisphere) the lab's code averages the DF/F over "
                "(parcells_updated121519.mat, pixels2rois.m). The images of the three channels were co-registered and "
                "registered to CCFv3 with manually selected control points, so the masks apply to all of them; the "
                "plane segmentation is attached to the jRCaMP1b imaging plane only because NWB needs one."
            ),
            imaging_plane=imaging_plane,
        )
        plane_segmentation.add_column(name="area", description="The parcel's label in the lab's parcellation.")
        plane_segmentation.add_column(name="area_description", description="The parcel's area.")
        plane_segmentation.add_column(name="hemisphere", description="'left' or 'right', from the label's prefix.")
        plane_segmentation.add_column(
            name="excluded_in_paper",
            description=(
                "True for the parcels the paper leaves out of its analyses (PL, ACA and RSPv for midline vasculature, "
                "SC and IC as colliculus), which leaves the 23 parcels per hemisphere it reports."
            ),
        )
        for index, (label, description) in enumerate(zip(parcels.names, parcels.description)):
            hemisphere, area = label.split("-", 1)
            hemisphere = {"L": "left", "R": "right"}[hemisphere]
            # The lab's descriptions of L-AUD and L-SSp-un say "Right"; the label decides the hemisphere.
            area_description = " ".join(description.split()).split(" ", 1)[1]
            rows, cols = np.nonzero(parcels.indicators[:, :, index] > 0)
            pixel_numbers = rows + cols * n_rows + 1  # MATLAB's 1-based column-major index, as in pixels2rois.m
            pixel_mask = [
                _get_pixel_coordinate(pixel_num=np.array([number]), n_cols=n_cols, n_rows=n_rows)
                for number in pixel_numbers
            ]
            plane_segmentation.add_roi(
                pixel_mask=pixel_mask,
                area=label,
                area_description=f"{hemisphere.capitalize()} {area_description}",
                hemisphere=hemisphere,
                excluded_in_paper=area.upper() in {name.upper() for name in EXCLUDED_AREAS},
            )

        if "DfOverF" not in ophys.data_interfaces:
            ophys.add(DfOverF(name="DfOverF"))
        rois = plane_segmentation.create_roi_table_region(
            region=list(range(len(parcels.names))), description="All 56 Allen CCFv3 parcels."
        )
        with h5py.File(self.source_data["file_path"], "r") as file:
            for channel, (_, measure) in CHANNELS.items():
                if self.starting_times[channel] is None:
                    raise ValueError(f"Set the starting time of the '{channel}' channel before adding it.")
                data = file["dFoF_parcells"][channel]
                data = data[:100] if stub_test else data[()]
                ophys["DfOverF"].add_roi_response_series(
                    RoiResponseSeries(
                        name=f"AllenParcelsDfOverF{channel.capitalize()}",
                        description=(
                            f"DF/F of {measure}, averaged over the active pixels of each Allen parcel (pixels2rois.m). "
                            "A parcel is NaN throughout when fewer than 25% of its pixels are active, as for parcels "
                            "at the edge of the window."
                        ),
                        data=data,
                        rois=rois,
                        unit="n.a.",
                        starting_time=self.starting_times[channel],
                        rate=self.source_data["sampling_frequency"],
                    )
                )
