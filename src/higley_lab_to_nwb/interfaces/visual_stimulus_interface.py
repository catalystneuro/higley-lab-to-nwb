import pandas as pd
import numpy as np
from neuroconv import BaseDataInterface
from neuroconv.utils import FilePathType
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals


class VisualStimulusInterface(BaseDataInterface):
    """
    Data interface class for converting visual stimulus signals from csv file, given start times and stop times of
    each stimulus.
    """

    associated_suffixes = ".csv"
    display_name = "Visual Stimulus"

    def __init__(
        self,
        csv_file_path: FilePathType,
        start_times: list,
        stop_times: list,
        verbose: bool = True,
    ):
        """
         Parameters
        ----------
        csv_file_path : FilePathType
            Path to .csv file for visual stimulus characterization.
        start_times : list
            List of the visual stimulus start times in seconds.
        stop_times : list
            List of the visual stimulus stop times in seconds.
        verbose : bool, default: True
        """
        super().__init__(
            csv_file_path=csv_file_path,
            start_times=start_times,
            stop_times=stop_times,
            verbose=verbose,
        )

    def get_stimulus_feature(self, column_index):
        feature = pd.read_csv(self.source_data["csv_file_path"], usecols=column_index)
        return feature.to_numpy()

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:

        intervals_table = TimeIntervals(
            name="VisualStimulus",
            description=f"Intervals for each visual stimulus presentation",
        )

        intervals_table.add_column(name="contrast", description="Contrast of the visual stimulus image.")
        contrasts = self.get_stimulus_feature(column_index=[0])
        intervals_table.add_column(
            name="orientation", description="Orientation of the visual stimulus image, in degree."
        )
        orientations = self.get_stimulus_feature(column_index=[1])
        intervals_table.add_column(name="stimulus_frequency", description="Temporal frequency of the stimulus, in Hz.")
        stimulus_frequencies = self.get_stimulus_feature(column_index=[2])
        intervals_table.add_column(
            name="spatial_frequency", description="Spatial frequency of the stimulus, in cycles per degrees."
        )
        spatial_frequencies = self.get_stimulus_feature(column_index=[3])
        intervals_table.add_column(name="stimulus_size", description="Size of the visual stimulus, in degrees.")
        sizes = self.get_stimulus_feature(column_index=[4])
        intervals_table.add_column(
            name="screen_coordinates",
            description="Screen coordinates that define the position of the stimulus on the monitor, i.e. [x1,y1,x2,"
            "y2]."
            "Left (x1): The x-coordinate of the left edge of the rectangle."
            "Top (y1): The y-coordinate of the top edge of the rectangle."
            "Right (x2): The x-coordinate of the right edge of the rectangle."
            "Bottom (y2): The y-coordinate of the bottom edge of the rectangle.",
        )
        screen_coordinates = self.get_stimulus_feature(column_index=[5, 6, 7, 8])

        start_times = self.source_data["start_times"]
        stop_times = self.source_data["stop_times"]

        n_frames = 100 if stub_test else len(start_times)

        for frame in range(n_frames - 1):
            intervals_table.add_row(
                start_time=start_times[frame],
                stop_time=stop_times[frame],
                contrast=contrasts[frame][0],
                orientation=orientations[frame][0],
                stimulus_frequency=stimulus_frequencies[frame][0],
                spatial_frequency=spatial_frequencies[frame][0],
                stimulus_size=sizes[frame][0],
                screen_coordinates=screen_coordinates[frame][:],
                check_ragged=False,
            )

        nwbfile.add_time_intervals(intervals_table)
