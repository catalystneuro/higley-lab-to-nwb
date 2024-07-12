"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union, Dict, Any
from neuroconv.utils import load_dict_from_file, dict_deep_update
from higley_lab_to_nwb.lohani_2022 import Lohani2022NWBConverter
from higley_lab_to_nwb.interfaces.spike2signals_interface import get_streams
from higley_lab_to_nwb.lohani_2022.utils import create_tiff_stack, read_session_start_time, get_event_times_from_mat
import os
import glob


def session_to_nwb(
    folder_path: Union[str, Path],
    parcellation_folder_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    session_id: str,
    stub_test: bool = False,
):
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    source_data = dict()
    conversion_options = dict()

    search_pattern = "_".join(session_id.split("_")[:2])

    # Add Analog signals from Spike2
    file_path = list(folder_path.glob(f"{search_pattern}*.smrx"))[0]
    stream_ids, stream_names = get_streams(file_path=file_path)

    # Define each smrx signal name
    TTLsignals_name_map = {
        stream_ids[stream_names == "BL_LED"][0]: "TTLSignalBlueLED",
        stream_ids[stream_names == "UV_LED"][0]: "TTLSignalVioletLED",
        stream_ids[stream_names == "Green LED"][0]: "TTLSignalGreenLED",
        # stream_ids[stream_names == "MesoCam"][0]: "TTLSignalMesoscopicCamera",
        # stream_ids[stream_names == "R_mesocam"][0]: "TTLSignalRedMesoscopicCamera",
        stream_ids[stream_names == "pupilcam"][0]: "TTLSignalPupilCamera",
    }
    behavioral_name_map = {
        stream_ids[stream_names == "wheel"][0]: "WheelSignal",
    }

    source_data.update(
        dict(
            Spike2Signals=dict(
                file_path=str(file_path),
                ttl_stream_ids_to_names_map=TTLsignals_name_map,
                behavioral_stream_ids_to_names_map=behavioral_name_map,
            )
        )
    )
    conversion_options.update(dict(Spike2Signals=dict(stub_test=stub_test)))

    if "vis_stim" in session_id:
        csv_file_path = list(folder_path.glob(f"{search_pattern}*.csv"))[0]
        mat_file_path = parcellation_folder_path / "smrx_signals.mat"
        start_times, stop_times = get_event_times_from_mat(file_path=str(mat_file_path))
        source_data.update(
            dict(
                VisualStimulusInterface=dict(
                    csv_file_path=csv_file_path,
                    start_times=start_times,
                    stop_times=stop_times,
                )
            )
        )
        conversion_options.update(dict(VisualStimulusInterface=dict(stub_test=stub_test)))

    # Add Imaging
    sampling_frequency = 10.0
    photon_series_index = 0

    # Define a dictionary that for each excitation type associate the starting frame index
    excitation_type_to_start_frame_index_mapping = dict(Blue=0, Violet=1, Green=2)
    # Define a dictionary that for each optical channel/filter associate the frame side
    channel_to_frame_side_mapping = dict(Green="right", Red="left")
    # Define the excitation-channel combinations
    excitation_type_channel_comb = dict(Blue="Green", Violet="Green", Green="Red")

    for excitation_type, channel in excitation_type_channel_comb.items():
        start_frame_index = excitation_type_to_start_frame_index_mapping[excitation_type]
        frame_side = channel_to_frame_side_mapping[channel]
        tif_file_path = str(folder_path) + f"/{session_id}_channel{start_frame_index}_{frame_side}.tiff"
        if not os.path.exists(tif_file_path):
            create_tiff_stack(
                folder_path=folder_path,
                output_file_path=tif_file_path,
                start_frame_index=start_frame_index,
                frame_side=frame_side,
                stub_test=stub_test,
            )

        suffix = f"{excitation_type}Excitation{channel}Channel"
        interface_name = f"Imaging{suffix}"
        source_data[interface_name] = {
            "file_path": tif_file_path,
            "sampling_frequency": sampling_frequency,
            "photon_series_type": "OnePhotonSeries",
        }
        conversion_options[interface_name] = {
            "stub_test": stub_test,
            "photon_series_index": photon_series_index,
            "photon_series_type": "OnePhotonSeries",
        }
        photon_series_index += 1

    # Add Behavioral Video Recording
    avi_files = list(folder_path.glob(f"{search_pattern}*.avi"))
    video_file_path = avi_files[0]
    source_data.update(dict(Video=dict(file_paths=[video_file_path], verbose=False)))
    conversion_options.update(dict(Video=dict(stub_test=stub_test)))

    # Add Facemap output
    mat_files = list(folder_path.glob(f"{search_pattern}*_proc.mat"))
    mat_file_path = mat_files[0]
    source_data.update(
        dict(
            FacemapInterface=dict(mat_file_path=str(mat_file_path), video_file_path=str(video_file_path), verbose=False)
        )
    )

    ophys_metadata_path = Path(__file__).parent / "metadata" / "lohani_2022_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)

    converter = Lohani2022NWBConverter(
        source_data=source_data,
        excitation_type_channel_comb=excitation_type_channel_comb,
        ophys_metadata=ophys_metadata,
    )

    # Add datetime to conversion
    metadata = converter.get_metadata()
    date = read_session_start_time(folder_path=folder_path)
    metadata["NWBFile"]["session_start_time"] = date
    subject_id = session_id.split("_")[1]
    metadata["Subject"].update(subject_id=subject_id)
    metadata["NWBFile"].update(session_id=session_id)

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "lohani_2022_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":
    # Parameters for conversion
    root_path = Path("E:/CN_data")
    data_dir_path = root_path / "Higley-CN-data-share"
    output_dir_path = root_path / "Higley-conversion_nwb"
    stub_test = True
    date = "11222019"
    animal_number = "05"
    session_id = f"{date}_grabAM{animal_number}_vis_stim"
    folder_path = data_dir_path / session_id
    parcellation_folder_path = (
        data_dir_path / "parcellation" / f"grab{animal_number}" / "imaging with 575 excitation" / session_id
    )
    session_to_nwb(
        folder_path=folder_path,
        parcellation_folder_path=parcellation_folder_path,
        output_dir_path=output_dir_path,
        session_id=session_id,
        stub_test=stub_test,
    )
