from typing import List
import numpy as np
from neo import io

from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.tools import get_package
from neuroconv.utils import FilePathType
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
from spikeinterface.extractors import CedRecordingExtractor
def _test_sonpy_installation() -> None:
    get_package(
        package_name="sonpy",
        excluded_python_versions=["3.10", "3.11"],
        excluded_platforms_and_python_versions=dict(darwin=dict(arm=["3.8", "3.9", "3.10", "3.11"])),
    )
def get_stream_ids(file_path: FilePathType) -> List[str]:
    """Return a list of channel names as set in the recording extractor."""
    r = io.CedIO(filename=file_path)
    signal_streams = r.header["signal_streams"]
    stream_ids = list(signal_streams["id"])
    return stream_ids

def get_stream_names(file_path: FilePathType) -> List[str]:
    """Return a list of channel ids as set in the recording extractor."""
    r = io.CedIO(filename=file_path)
    signal_channels = r.header["signal_channels"]
    channel_names = signal_channels["name"]
    return channel_names

class Benisty2022Spike2TTLInterface(BaseRecordingExtractorInterface):
    """
    Data interface class for converting Spike2 synchronization signals from CED (Cambridge Electronic
    Design) using the :py:class:`~spikeinterface.extractors.CedRecordingExtractor`."""

    display_name = "Spike2 Recording"
    # keywords = BaseRecordingExtractorInterface.keywords + ("CED",)
    associated_suffixes = (".smr", ".smrx")
    info = "Interface for Spike2 recording synchronization signals from CED (Cambridge Electronic Design)."

    ExtractorName = "CedRecordingExtractor"

    def __init__(self, file_path: FilePathType, stream_id: str = None, stream_name: str = None , verbose: bool = True, es_key: str = "ElectricalSeries"):
        """
         Parameters
        ----------
        file_path : FilePathType
            Path to .smr or .smrx file.
        stream_id: str, default: None
            If there are several streams, specify the stream id you want to load.
        stream_name: str, default: None
            If there are several streams, specify the stream name you want to load.
        verbose : bool, default: True
        es_key : str, default: "ElectricalSeries"
        """
        _test_sonpy_installation()

        super().__init__(file_path=file_path, stream_id=stream_id, stream_name=stream_name, all_annotations=True, verbose=verbose, es_key=es_key)
    
    def get_event_times_from_ttl(self) -> np.ndarray:
        """
        Return the start of event times from the rising part of TTL pulses on one of the channels.

        Parameters
        ----------
        stream_id : str
            If there are several streams, specify the stream id you want to load.
        Returns
        -------
        rising_times : numpy.ndarray
            The times of the rising TTL pulses.
        """

        rising_frames = get_rising_frames_from_ttl(
            trace=self.recording_extractor.get_traces())

        ttl_timestamps = self.recording_extractor.get_times()
        rising_times = ttl_timestamps[rising_frames]

        return rising_times