from typing import List, Optional
import numpy as np
from neo import io

from neuroconv import BaseDataInterface
from neuroconv.tools import get_package
from neuroconv.utils import FilePathType
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
from spikeinterface.extractors import CedRecordingExtractor
from spikeinterface import AppendSegmentRecording, ChannelSliceRecording
from pynwb import NWBFile

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


class Benisty2022Spike2EventsInterface(BaseDataInterface):
    # TODO find a better name for the interface. It needs to be general for all type of signals not only TTL (e.g Wheel Motion)
    """
    Data interface class for converting Spike2 synchronization signals from CED (Cambridge Electronic
    Design) using the :py:class:`~spikeinterface.extractors.CedRecordingExtractor`."""

    display_name = "Spike2 Recording"
    associated_suffixes = (".smr", ".smrx")
    info = "Interface for Spike2 recording synchronization signals from CED (Cambridge Electronic Design)."

    def __init__(
        self,
        file_path: FilePathType,
        stream_ids_to_names_map: dict,
        verbose: bool = True,
    ):
        """
         Parameters
        ----------
        file_path : FilePathType
            Path to .smr or .smrx file.
        stream_ids_to_names_map: dict
            If there are several streams, specify the stream id and associated name.
        verbose : bool, default: True
        """
        _test_sonpy_installation()

        super().__init__(
            file_path=file_path,
            verbose=verbose,
        )

        self.stream_ids_to_names_map = stream_ids_to_names_map

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Events"] = dict(
            name="Spike2TTLSignals",
            description="Contains the onset times of binary signals from the Spike2 output.",
        )

        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict) -> None:
        from ndx_events import AnnotatedEventsTable

        events_metadata = metadata["Events"]
        events_table_name = events_metadata["name"]
        assert events_table_name not in nwbfile.acquisition, f"The {events_metadata['name']} is already in nwbfile."

        events = AnnotatedEventsTable(
            name=events_table_name,
            description=events_metadata["description"],
        )

        for stream_id,stream_name in self.stream_ids_to_names_map.items():
            extractor =  CedRecordingExtractor(file_path=str(self.source_data["file_path"]), stream_id=stream_id)
            times = extractor.get_times()
            traces = extractor.get_traces()
            event_times = get_rising_frames_from_ttl(traces)

            if len(event_times):
                events.add_event_type(
                    label=stream_name,
                    event_description=f"The onset times of the {stream_name} event.",
                    event_times=times[event_times],
                )

        nwbfile.add_acquisition(events)