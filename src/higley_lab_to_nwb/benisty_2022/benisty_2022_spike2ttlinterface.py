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
def get_stream_ids_and_names(file_path: FilePathType) -> List[str]:
    """Return a list of channel names as set in the recording extractor."""
    r = io.CedIO(filename=file_path)
    signal_channels = r.header["signal_channels"]
    stream_ids = signal_channels["id"]
    stream_names = signal_channels["name"]
    return stream_ids, stream_names

class Benisty2022Spike2TTLInterface(BaseRecordingExtractorInterface):
    #TODO find a better name for the interface. It needs to be general for all type of signals not only TTL (e.g Wheel Motion) 
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
        self.stream_ids, self.stream_names = get_stream_ids_and_names(file_path=file_path)
    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        # Device metadata
        # TODO store the correct metadata
        device = dict(name="AcuisitionBoard", description="Spike2 recording signals from CED (Cambridge Electronic Design)", manufacturer="Cambridge Electronic Design")

        # Add groups metadata
        metadata["Ecephys"]["Device"] = [device]

        metadata["Ecephys"]["ElectrodeGroup"][0].update(
            name="Spike2ChannelGroup", description="A group representing the Spike2 channels.", device=device["name"]
        )
        metadata["Ecephys"]["Electrodes"] = [
            dict(name="group_name", description="Name of the ElectrodeGroup this electrode is a part of."),
        ]

        return metadata
    
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