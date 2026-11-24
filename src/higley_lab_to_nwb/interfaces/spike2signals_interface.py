from pathlib import Path

import numpy as np
from neo import io
from neuroconv import BaseDataInterface
from neuroconv.tools.signal_processing import get_falling_frames_from_ttl, get_rising_frames_from_ttl
from pynwb import NWBFile, TimeSeries
from pynwb.event import EventsTable, TimestampVectorData
from spikeinterface.extractors.extractor_classes import CedRecordingExtractor


def get_streams(file_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Return the ids and names of the signal channels of a Spike2 file."""
    signal_channels = io.CedIO(filename=str(file_path)).header["signal_channels"]
    return signal_channels["id"], signal_channels["name"]


def _get_stream_gain_offset(file_path: str | Path, stream_id: str) -> tuple[float, float]:
    """Return the gain and offset of one signal channel of a Spike2 file."""
    signal_channels = io.CedIO(filename=str(file_path)).header["signal_channels"]
    is_stream = signal_channels["id"] == stream_id
    return signal_channels["gain"][is_stream][0], signal_channels["offset"][is_stream][0]


class Spike2SignalsInterface(BaseDataInterface):
    """TTL pulse times and behavioral analog signals from a Spike2 (CED) file.

    Each TTL channel is written as an EventsTable of its rising-edge times, and each behavioral channel as a
    TimeSeries in acquisition.
    """

    display_name = "Spike2 Recording"
    associated_suffixes = (".smr", ".smrx")
    info = "Interface for Spike2 analogue signals from CED (Cambridge Electronic Design)."

    def __init__(
        self,
        file_path: str | Path,
        ttl_stream_ids_to_names_map: dict,
        behavioral_stream_ids_to_names_map: dict,
        verbose: bool = False,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to the .smr or .smrx file.
        ttl_stream_ids_to_names_map : dict
            Stream id of each TTL channel to write, and the name of its EventsTable.
        behavioral_stream_ids_to_names_map : dict
            Stream id of each behavioral channel to write, and the name of its TimeSeries.
        """
        super().__init__(file_path=file_path, verbose=verbose)
        self.ttl_stream_ids_to_names_map = ttl_stream_ids_to_names_map
        self.behavioral_stream_ids_to_names_map = behavioral_stream_ids_to_names_map

    def get_event_times_from_ttl(self, stream_id: str, rising: bool = True) -> np.ndarray:
        extractor = CedRecordingExtractor(file_path=str(self.source_data["file_path"]), stream_id=stream_id)
        times = extractor.get_times()
        traces = extractor.get_traces()
        if rising:
            event_frames = get_rising_frames_from_ttl(traces)
        else:
            event_frames = get_falling_frames_from_ttl(traces)
        return times[event_frames]

    def get_event_times_from_ttl_channel_name(self, channel_name: str) -> np.ndarray:
        stream_ids = [
            stream_id
            for stream_id, stream_name in self.ttl_stream_ids_to_names_map.items()
            if stream_name == channel_name
        ]
        if not stream_ids:
            raise ValueError(f"No TTL channel named '{channel_name}' in {self.ttl_stream_ids_to_names_map}.")
        return self.get_event_times_from_ttl(stream_id=stream_ids[0])

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        end_frame = 100 if stub_test else None
        file_name = Path(self.source_data["file_path"]).name

        for stream_id, stream_name in self.ttl_stream_ids_to_names_map.items():
            timestamps = self.get_event_times_from_ttl(stream_id=stream_id)[:end_frame]
            nwbfile.add_events_table(
                EventsTable(
                    name=stream_name,
                    description=f"Onset times of the {stream_name} TTL pulses.",
                    source_description=f"Rising edges of Spike2 channel {stream_id} in {file_name}.",
                    columns=[
                        TimestampVectorData(
                            name="timestamp", description="Onset time of each pulse, in seconds.", data=timestamps
                        )
                    ],
                )
            )

        for stream_id, stream_name in self.behavioral_stream_ids_to_names_map.items():
            extractor = CedRecordingExtractor(file_path=str(self.source_data["file_path"]), stream_id=stream_id)
            gain, offset = _get_stream_gain_offset(file_path=self.source_data["file_path"], stream_id=stream_id)
            nwbfile.add_acquisition(
                TimeSeries(
                    name=stream_name,
                    data=extractor.get_traces(end_frame=end_frame).reshape(-1),
                    starting_time=float(extractor.get_times()[0]),
                    rate=extractor.get_sampling_frequency(),
                    description=f"The {stream_name} measured over time.",
                    unit="Volts",
                    conversion=gain,
                    offset=offset,
                )
            )
