import numpy as np
from ndx_hed import HedTags
from neuroconv import BaseDataInterface
from pynwb import NWBFile, TimeSeries
from pynwb.epoch import TimeIntervals

from .hed import WHEEL_ACTIVATION_HED, add_hed_schema


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
        wheel_speed_unit: str = "unknown",
        wheel_speed_description: str = "Wheel speed",
        wheel_activation_description: str = "Intervals for each wheel on-off signal",
        verbose: bool = False,
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
            wheel_speed_unit: str, default: "unknown"
                Unit of the wheel speed trace.
            wheel_speed_description: str, default: "Wheel speed"
                Description of the wheel speed trace.
            wheel_activation_description: str, default: "Intervals for each wheel on-off signal"
                Description of the WheelActivation intervals table.
        """

        super().__init__(verbose=verbose)
        self.wheel_on_times = wheel_on_times
        self.wheel_off_times = wheel_off_times
        self.wheel_speed_data = wheel_speed_data
        self.sampling_frequency = sampling_frequency
        self.wheel_speed_unit = wheel_speed_unit
        self.wheel_speed_description = wheel_speed_description
        self.wheel_activation_description = wheel_activation_description

    def add_wheel_speed(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:

        if "behavior" not in nwbfile.processing:
            nwbfile.create_processing_module(name="behavior", description="behavioral data processing")

        nwbfile.processing["behavior"].add(
            TimeSeries(
                name="WheelSpeed",
                description=self.wheel_speed_description,
                data=np.asarray(self.wheel_speed_data[:100] if stub_test else self.wheel_speed_data, dtype="float32"),
                starting_time=0.0,
                rate=self.sampling_frequency if self.sampling_frequency is not None else 5000.0,
                unit=self.wheel_speed_unit,
            )
        )

    def add_wheel_activation(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        intervals_table = TimeIntervals(
            name="WheelActivation",
            description=self.wheel_activation_description,
        )
        intervals_table.add_column(name="HED", description="HED annotation of each interval.", col_cls=HedTags)
        n_frames = 100 if stub_test and len(self.wheel_on_times) > 100 else len(self.wheel_on_times)

        for frame in range(n_frames):
            intervals_table.add_row(
                start_time=self.wheel_on_times[frame],
                stop_time=self.wheel_off_times[frame],
                HED=WHEEL_ACTIVATION_HED,
                check_ragged=False,
            )

        add_hed_schema(nwbfile)
        nwbfile.add_time_intervals(intervals_table)

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:

        # Add wheel activation
        if len(self.wheel_on_times) > 0:
            self.add_wheel_activation(nwbfile=nwbfile, metadata=metadata, stub_test=stub_test)
        else:
            print("No wheel on-off signals detected")

        # Add wheel speed
        self.add_wheel_speed(nwbfile=nwbfile, metadata=metadata, stub_test=stub_test)
