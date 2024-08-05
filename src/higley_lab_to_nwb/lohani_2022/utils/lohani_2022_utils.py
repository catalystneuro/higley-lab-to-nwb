import tifffile
from natsort import natsorted
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl, get_falling_frames_from_ttl
from spikeinterface.extractors import CedRecordingExtractor
from neuroconv.tools import get_package
from typing import Union
from pathlib import Path


def read_session_start_time(folder_path: Union[str, Path]):
    tiff_file_paths = natsorted(folder_path.glob("*.tif"))
    with tifffile.TiffFile(tiff_file_paths[0]) as tif:
        metadata = tif.pages[0].tags["ImageDescription"].value

    lines = metadata.split("\r\n")
    date_time_str = lines[1]
    # Assuming the timezone is always 'Eastern Standard Time'
    date_time_obj = datetime.strptime(date_time_str[: -len(" Eastern Standard Time")], "%a, %d %b %Y %H:%M:%S")
    date_time_obj = date_time_obj.replace(tzinfo=ZoneInfo("US/Eastern"))

    return date_time_obj


def get_tiff_file_paths_sorted_by_channel(
    folder_path: Union[str, Path], start_frame_index: int = 0, stub_test: bool = False
):
    tiff_file_paths = natsorted(folder_path.glob("*.tif"))
    if stub_test:
        tiff_file_paths = tiff_file_paths[:100]  # for testing
    selected_tiff_file_paths = tiff_file_paths[start_frame_index::3]

    return selected_tiff_file_paths


def create_tiff_stack(
    folder_path: Union[str, Path],
    output_file_path: Union[str, Path],
    start_frame_index: int = 0,
    frame_side: str = "left",
    stub_test: bool = False,
):
    selected_tiff_file_paths = get_tiff_file_paths_sorted_by_channel(
        folder_path=folder_path, start_frame_index=start_frame_index, stub_test=stub_test
    )
    frames = [tifffile.imread(file_path) for file_path in selected_tiff_file_paths]

    if frame_side == "left":
        stack = np.stack([frame[:, :512].transpose(1, 0) for frame in frames], axis=0)
    elif frame_side == "right":
        stack = np.stack([frame[:, 512:].transpose(1, 0) for frame in frames], axis=0)
    else:
        raise ValueError("frame_side must be either 'right' or 'left'")

    tifffile.imwrite(output_file_path, stack)

    return


def process_event_times(rising_times: np.ndarray, falling_times: np.ndarray):
    # TODO define your custom function to processed event times extracted from Spike2 signal
    return rising_times, falling_times


def _test_sonpy_installation() -> None:
    get_package(
        package_name="sonpy",
        excluded_python_versions=["3.10", "3.11"],
        excluded_platforms_and_python_versions=dict(darwin=dict(arm=["3.8", "3.9", "3.10", "3.11"])),
    )


def get_event_times_from_spike2(file_path: Union[str, Path], stream_id: str, clean_event_times: bool = False):
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


def get_event_times_from_mat(file_path: Union[str, Path], start_time_variable_name: str, end_time_variable_name: str):
    from pymatreader import read_mat

    mat = read_mat(str(file_path))

    if "timing" in mat:
        timing_group = mat["timing"]
        # Check if dataset exists
        if start_time_variable_name in timing_group and end_time_variable_name in timing_group:
            start_times_data = timing_group[start_time_variable_name]
            start_times = start_times_data[:]
            stop_times_data = timing_group[end_time_variable_name]
            stop_times = stop_times_data[:]
            return start_times, stop_times
        elif start_time_variable_name not in timing_group:
            raise f"{start_time_variable_name} dataset does not exists in {file_path}"
        elif end_time_variable_name not in timing_group:
            raise f"{end_time_variable_name} dataset does not exists in {file_path}"
    else:
        raise f"timing group does not exists in {file_path}"


def get_channel_trace_from_mat(file_path: Union[str, Path], variable_name: str):
    from pymatreader import read_mat

    mat = read_mat(str(file_path))

    if "params" in mat:
        sampling_frequency = mat["params"]["fsspike2"]
    else:
        sampling_frequency = None
    if "channels_data" in mat:
        channel_group = mat["channels_data"]
        # Check if the variable_name exists
        if variable_name in channel_group:
            channel_data = channel_group[variable_name]
            channel_data = channel_data[:]
            return channel_data, float(sampling_frequency)
        elif variable_name not in channel_group:
            raise f"{variable_name} dataset does not exists in {file_path}"
    else:
        raise f"'channels_data' does not exists in {file_path}"
