from typing import List
import numpy as np
from neo import io

from neuroconv import BaseDataInterface
from neuroconv.tools import get_package
from neuroconv.utils import FilePathType
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl, get_falling_frames_from_ttl
from spikeinterface.extractors import CedRecordingExtractor
from pynwb import NWBFile, TimeSeries
from pynwb.epoch import TimeIntervals
from ndx_events import TtlsTable, TtlTypesTable


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


def _get_stream_gain_offset(file_path: FilePathType, stream_id: str) -> List[str]:
    """Return a list of channel names as set in the recording extractor."""
    r = io.CedIO(filename=file_path)
    signal_channels = r.header["signal_channels"]
    gain = signal_channels["gain"][signal_channels["id"] == stream_id][0]
    offset = signal_channels["offset"][signal_channels["id"] == stream_id][0]
    return gain, offset


class Spike2SignalsInterface(BaseDataInterface):
    """
    Data interface class for converting Spike2 analogue signals from CED (Cambridge Electronic
    Design) using the :py:class:`~spikeinterface.extractors.CedRecordingExtractor`."""

    display_name = "Spike2 Recording"
    associated_suffixes = (".smr", ".smrx")
    info = "Interface for Spike2 analogue signals from CED (Cambridge Electronic Design)."

    def __init__(
        self,
        file_path: FilePathType,
        ttl_stream_ids_to_names_map: dict,
        behavioral_stream_ids_to_names_map: dict,
        verbose: bool = True,
    ):
        """
         Parameters
        ----------
        file_path : FilePathType
            Path to .smr or .smrx file.
        ttl_stream_ids_to_names_map: dict
            If there are several streams for ttl signals, specify the stream id and associated name.
        behavioral_stream_ids_to_names_map: dict
            If there are several streams for behavioural signals, specify the stream id and associated name.
        verbose : bool, default: True
        """
        _test_sonpy_installation()

        super().__init__(
            file_path=file_path,
            verbose=verbose,
        )

        self.ttl_stream_ids_to_names_map = ttl_stream_ids_to_names_map
        self.behavioral_stream_ids_to_names_map = behavioral_stream_ids_to_names_map

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Events"] = dict(
            TTLTypesTable=dict(
                name="TTLTypesTable",
                description="Contains the type of TTL signals from Spike2 output.",
            ),
            TTLsTable=dict(
                name="TTLsTable",
                description="Contains the TTL signals onset times.",
            ),
        )

        return metadata

    def get_event_times_from_ttl(self, stream_id, rising: bool = True):
        extractor = CedRecordingExtractor(file_path=str(self.source_data["file_path"]), stream_id=stream_id)
        times = extractor.get_times()
        traces = extractor.get_traces()
        if rising:
            event_times = get_rising_frames_from_ttl(traces)
        else:
            event_times = get_falling_frames_from_ttl(traces)

        return times[event_times]

    def get_event_times_from_ttl_channel_name(self, channel_name: str) -> int:

        stream_id = next(
            (
                stream_id
                for stream_id, stream_name in self.ttl_stream_ids_to_names_map.items()
                if stream_name == channel_name
            ),
            None,
        )
        times = self.get_event_times_from_ttl(stream_id=stream_id)

        return times

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        end_frame = 100 if stub_test else None

        events_metadata = metadata["Events"]
        ttl_types_table = TtlTypesTable(**events_metadata["TTLTypesTable"])
        ttls_table = TtlsTable(**events_metadata["TTLsTable"], target_tables={"ttl_type": ttl_types_table})

        for ttl_type, (stream_id, stream_name) in enumerate(self.ttl_stream_ids_to_names_map.items()):
            timestamps = self.get_event_times_from_ttl(stream_id=stream_id)
            ttl_types_table.add_row(
                event_name=stream_name,
                event_type_description=f"The onset times of the {stream_name} event.",
                pulse_value=1,
            )
            if len(timestamps):
                for timestamp in timestamps[:end_frame]:
                    ttls_table.add_row(
                        ttl_type=ttl_type,
                        timestamp=timestamp,
                    )

        nwbfile.add_acquisition(ttl_types_table)
        nwbfile.add_acquisition(ttls_table)

        for stream_id, stream_name in self.behavioral_stream_ids_to_names_map.items():
            extractor = CedRecordingExtractor(file_path=str(self.source_data["file_path"]), stream_id=stream_id)
            gain, offset = _get_stream_gain_offset(file_path=str(self.source_data["file_path"]), stream_id=stream_id)
            behavioral_time_series = TimeSeries(
                name=stream_name,
                data=extractor.get_traces(end_frame=end_frame).reshape(-1),
                rate=extractor.get_sampling_frequency(),
                description=f"The {stream_name} measured over time.",
                unit="Volts",
                conversion=gain,
                offset=offset,
            )

            nwbfile.add_acquisition(behavioral_time_series)
