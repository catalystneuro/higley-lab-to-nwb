from pathlib import Path

import numpy as np
from neuroconv.tools.signal_processing import get_falling_frames_from_ttl, get_rising_frames_from_ttl
from neuroconv.utils.checks import calculate_regular_series_rate
from pymatreader import read_mat
from spikeinterface.extractors.extractor_classes import CedRecordingExtractor


def get_event_times_from_spike2(file_path: str | Path, stream_id: str) -> tuple[np.ndarray, np.ndarray]:
    """Rising and falling edge times of one channel of a Spike2 file."""
    extractor = CedRecordingExtractor(file_path=str(file_path), stream_id=stream_id)
    times = extractor.get_times()
    traces = extractor.get_traces()
    return times[get_rising_frames_from_ttl(traces)], times[get_falling_frames_from_ttl(traces)]


def get_event_times_from_mat(file_path: str | Path, stream_name: str = "diode") -> tuple[np.ndarray, np.ndarray]:
    """Start and stop times of one channel of the DATA struct of the session .mat file."""
    mat = read_mat(str(file_path))
    if "DATA" not in mat:
        raise ValueError(f"'DATA' does not exist in {file_path}")
    for variable_name in ("event_times", "channel_name"):
        if variable_name not in mat["DATA"]:
            raise ValueError(f"'DATA.{variable_name}' does not exist in {file_path}")
    event_times = mat["DATA"]["event_times"][mat["DATA"]["channel_name"].index(stream_name)]
    return event_times[:, 0], event_times[:, 1]


def get_wheel_times_from_mat(file_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Times the binarized wheel signal turns on and off."""
    mat = read_mat(str(file_path))
    times, traces = mat["timestamp"], mat["wheel"]
    return times[get_rising_frames_from_ttl(traces)], times[get_falling_frames_from_ttl(traces)]


def get_wheelspeed_trace_from_mat(file_path: str | Path) -> tuple[np.ndarray, float]:
    """The wheel speed trace and its sampling frequency."""
    mat = read_mat(str(file_path))
    sampling_frequency = calculate_regular_series_rate(series=mat["timestamp"], tolerance_decimals=3)
    return mat["wheel_speed"], sampling_frequency
