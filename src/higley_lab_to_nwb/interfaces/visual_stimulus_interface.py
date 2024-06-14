from typing import List, Literal
import pandas as pd
from neo import io

from neuroconv import BaseDataInterface
from neuroconv.tools import get_package
from neuroconv.utils import FilePathType
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl, get_falling_frames_from_ttl
from spikeinterface.extractors import CedRecordingExtractor
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals


def _test_sonpy_installation() -> None:
    get_package(
        package_name="sonpy",
        excluded_python_versions=["3.10", "3.11"],
        excluded_platforms_and_python_versions=dict(darwin=dict(arm=["3.8", "3.9", "3.10", "3.11"])),
    )


def get_streams(file_path: FilePathType) -> List[str]:
    """Return a list of channel names as set in the recording extractor."""
    r = io.CedIO(filename=file_path)
    signal_channels = r.header["signal_channels"]
    stream_ids = signal_channels["id"]
    stream_names = signal_channels["name"]
    return stream_ids, stream_names


class VisualStimulusInterface(BaseDataInterface):
    """
    Data interface class for converting Spike2 visual stimulus signals from CED (Cambridge Electronic
    Design) using the :py:class:`~spikeinterface.extractors.CedRecordingExtractor`."""

    display_name = "Spike2 Recording"
    associated_suffixes = (".smr", ".smrx")
    info = "Interface for Spike2 analogue signals from CED (Cambridge Electronic Design)."

    def __init__(
        self,
        csv_file_path: FilePathType,
        stream_id: str,
        spike2_file_path: FilePathType = None,
        mat_file_path: FilePathType = None,
        verbose: bool = True,
    ):
        """
         Parameters
        ----------
        spike2_file_path : FilePathType
            Path to .smr or .smrx file.
        csv_file_path : FilePathType
            Path to .csv file for visual stimulus characterization.
        verbose : bool, default: True
        """
        _test_sonpy_installation()

        if spike2_file_path is None and mat_file_path is None:
            raise ValueError(
                "Define either spike2_file_path or mat_file_path to extract the visual stimulus event times."
            )

        elif spike2_file_path is not None and mat_file_path is not None:
            raise ValueError(
                "Both spike2_file_path and mat_file_path have been defined. Define either spike2_file_path or mat_file_path to extract the visual stimulus event times."
            )
        
        elif spike2_file_path is not None: 
            super().__init__(
                spike2_file_path=spike2_file_path,
                csv_file_path=csv_file_path,
                stream_id=stream_id,
                verbose=verbose,
            )
            self._event_times_from_ttl = True

        elif mat_file_path is not None: 
            super().__init__(
                mat_file_path=mat_file_path,
                csv_file_path=csv_file_path,
                stream_id=stream_id,
                verbose=verbose,
            )
            self._event_times_from_ttl = False

    def get_event_times_from_ttl(self, rising: bool = True):
        extractor = CedRecordingExtractor(
            file_path=str(self.source_data["spike2_file_path"]), stream_id=self.source_data["stream_id"]
        )
        times = extractor.get_times()
        traces = extractor.get_traces()
        if rising:
            event_times = get_rising_frames_from_ttl(traces)
        else:
            event_times = get_falling_frames_from_ttl(traces)

        return times[event_times]
    
    def get_event_times_from_table(self, event_type: Literal["start", "stop"]):
        import h5py 
        with h5py.File(self.source_data["mat_file_path"], "r") as file:
            # Check if the DATA group exists
            if 'DATA' in file:
                data_group = file['DATA']                
                # Check if the event_times dataset exists
                if 'event_times' in data_group:
                    event_times_data = data_group['event_times']
                    event_time_ref = event_times_data[int(self.source_data["stream_id"]), 0]  # Assuming (8, 1) shape
                    event_time_dataset = file[event_time_ref]
                    times = event_time_dataset[:] 
                    if event_type == "start":
                        return times[0]
                    if event_type == "stop":
                        return times[1]
                else:
                    raise f"event_times dataset does not exists in {self.source_data['mat_file_path']}"
            else:
                raise f"DATA group does not exists in {self.source_data['mat_file_path']}"
            
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
        # TODO add a more descriptive text as description for "screen_coordinates" column
        intervals_table.add_column(name="screen_coordinates", description="Visual stimulus coordinates on the screen.")
        screen_coordinates = self.get_stimulus_feature(column_index=[5, 6, 7, 8])

        if self._event_times_from_ttl:
            start_times = self.get_event_times_from_ttl()
            stop_times = self.get_event_times_from_ttl(rising=False)
        else:
            start_times = self.get_event_times_from_table(event_type="start")
            stop_times = self.get_event_times_from_table(event_type="stop")


        n_frames = 100 if stub_test else len(start_times)

        for frame in range(n_frames):
            intervals_table.add_row(
                start_time=start_times[frame],
                stop_time=stop_times[frame],
                contrast=contrasts[frame][0],
                orientation=orientations[frame][0],
                stimulus_frequency=stimulus_frequencies[frame][0],
                spatial_frequency=spatial_frequencies[frame][0],
                stimulus_size=sizes[frame][0],
                screen_coordinates=screen_coordinates[frame][:],
                check_ragged = False,
            )

        nwbfile.add_time_intervals(intervals_table)
