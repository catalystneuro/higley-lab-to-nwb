import pandas as pd
from typing import Optional, Literal
from neuroconv import BaseDataInterface
from neuroconv.utils import FilePathType
from pynwb import NWBFile, TimeSeries
from pynwb.epoch import TimeIntervals


class ProcessedBehaviorInterface(BaseDataInterface):
    """
    Data interface class for converting processed behavioral signals.
    """

    associated_suffixes = ".mat"
    display_name = "Processed Behavioral Signal"

    def __init__(
        self,
        wheel_on_times: list,
        wheel_off_times: list,
        wheel_speed_data: list,
        sampling_frequency: float = None,
        verbose: bool = True,
    ):
        """
         Parameters
        ----------
            wheel_on_times: list,
                List of timestamps when the wheel start spinning.
            wheel_off_times: list,
                List of timestamps when the wheel stop spinning.
            wheel_speed_data: list,
                Wheel speed trace.
            sampling_frequency: float = None,
                Sampling frequency of the wheel speed trace.
        """

        super().__init__(verbose=verbose)
        self.wheel_on_times = wheel_on_times
        self.wheel_off_times = wheel_off_times
        self.wheel_speed_data = wheel_speed_data
        self.sampling_frequency = sampling_frequency

    def add_wheel_speed(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:

        if "behavior" not in nwbfile.processing:
            nwbfile.create_processing_module(name="behavior", description="behavioral data processing")

        nwbfile.processing["behavior"].add(
            TimeSeries(
                name="WheelSpeed",
                description="Wheel speed",
                data=self.wheel_speed_data[:100] if stub_test else self.wheel_speed_data,
                starting_time=0.0,
                rate=self.sampling_frequency if self.sampling_frequency is not None else 5000.0,
                unit="unknown",
            )
        )

    def add_wheel_activation(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        intervals_table = TimeIntervals(
            name="WheelActivation",
            description="Intervals for each wheel on-off signal",
        )
        n_frames = 100 if stub_test and len(self.wheel_on_times) > 100 else len(self.wheel_on_times)

        for frame in range(n_frames):
            intervals_table.add_row(
                start_time=self.wheel_on_times[frame],
                stop_time=self.wheel_off_times[frame],
                check_ragged=False,
            )

        nwbfile.add_time_intervals(intervals_table)

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:

        # Add wheel activation
        if len(self.wheel_on_times) > 0:
            self.add_wheel_activation(nwbfile=nwbfile, metadata=metadata, stub_test=stub_test)
        else:
            print("No wheel on-off signals detected")

        # Add wheel speed
        self.add_wheel_speed(nwbfile=nwbfile, metadata=metadata, stub_test=stub_test)
