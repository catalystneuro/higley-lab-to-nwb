"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
import datetime
from zoneinfo import ZoneInfo

from neuroconv.utils import load_dict_from_file, dict_deep_update

from higley_lab_to_nwb.benisty_2022 import Benisty2022NWBConverter
from higley_lab_to_nwb.benisty_2022.imaging_utils import create_tiff_stack


def session_to_nwb(data_dir_path: Union[str, Path], output_dir_path: Union[str, Path], stub_test: bool = False):

    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    session_id = "11222019_grabAM05_spont"
    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    source_data = dict()
    conversion_options = dict()

    # Add Imaging
    folder_path = data_dir_path / session_id
    sampling_frequency = 10.0
    photon_series_index = 0

    excitation_type_to_start_frame_index_mapping = dict(Blue=0, UV=1, Green=2)
    channel_to_frame_side_mapping = dict(Green="left", Red="right")

    for excitation_type in excitation_type_to_start_frame_index_mapping:
        for channel in channel_to_frame_side_mapping:
            start_frame_index = excitation_type_to_start_frame_index_mapping[excitation_type]
            frame_side = channel_to_frame_side_mapping[channel]

            file_path = create_tiff_stack(
            folder_path=folder_path, start_frame_index=start_frame_index, frame_side=frame_side
            )

            suffix = f"{excitation_type}Excitation{channel}Channel"
            interface_name = f"Imaging{suffix}"
            source_data[interface_name] = {
                "file_path": file_path,
                "sampling_frequency": sampling_frequency,
                "channel": channel,
                "excitation_type": excitation_type,
            }
            conversion_options[interface_name] = {
                "stub_test": stub_test,
                "photon_series_index": photon_series_index,
                "photon_series_type": "OnePhotonSeries",
            }
            photon_series_index += 1

    converter = Benisty2022NWBConverter(source_data=source_data)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    datetime.datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("US/Eastern"))
    date = datetime.datetime.today()  # TO-DO: Get this from author
    metadata["NWBFile"]["session_start_time"] = date
    subject_id = session_id.split("_")[1]
    metadata["Subject"].update(subject_id=subject_id)
    metadata["NWBFile"].update(session_id=session_id)
    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "benisty_2022_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)


if __name__ == "__main__":

    # Parameters for conversion
    root_path = Path("/media/amtra/Samsung_T5/CN_data")
    data_dir_path = root_path / "Higley-CN-data-share"
    output_dir_path = root_path / "Higley-conversion_nwb/"
    stub_test = True

    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )
