import numpy as np
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl, get_falling_frames_from_ttl
from spikeinterface.extractors import CedRecordingExtractor
from neuroconv.tools import get_package


def process_event_times(rising_times: np.ndarray, falling_times: np.ndarray):
    # TODO define your custom function to processed event times extracted from Spike2 signal
    return rising_times, falling_times


def _test_sonpy_installation() -> None:
    get_package(
        package_name="sonpy",
        excluded_python_versions=["3.10", "3.11"],
        excluded_platforms_and_python_versions=dict(darwin=dict(arm=["3.8", "3.9", "3.10", "3.11"])),
    )


def get_event_times_from_spike2(file_path: str, stream_id: str, clean_event_times: bool = False):
    _test_sonpy_installation()
    extractor = CedRecordingExtractor(file_path=file_path, stream_id=stream_id)
    times = extractor.get_times()
    traces = extractor.get_traces()
    rising_times = get_rising_frames_from_ttl(traces)
    falling_times = get_falling_frames_from_ttl(traces)
    if clean_event_times:
        process_event_times(rising_times, falling_times)
    start_times = times[rising_times]
    stop_times = times[falling_times]
    return start_times, stop_times


def get_event_times_from_mat(file_path: str, stream_name: str = "diode"):
    from pymatreader import read_mat

    mat = read_mat(str(file_path))
    # Check if the DATA group exists
    if "DATA" in mat:
        data_group = mat["DATA"]
        # Check if the event_times dataset exists
        if "event_times" in data_group and "channel_name" in data_group:
            event_times = data_group["event_times"][data_group["channel_name"].index(stream_name)]
            start_times = event_times[:, 0]
            stop_times = event_times[:, 1]
            return start_times, stop_times
        elif "event_times" not in data_group:
            raise f"event_times dataset does not exists in {file_path}"
        elif "channel_name" not in data_group:
            raise f"channel_names dataset does not exists in {file_path}"
    else:
        raise f"DATA group does not exists in {file_path}"
