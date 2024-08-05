"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from neuroconv.utils import load_dict_from_file, dict_deep_update
from higley_lab_to_nwb.interfaces.spike2signals_interface import get_streams
from higley_lab_to_nwb.benisty_2024 import Benisty2024NWBConverter
from higley_lab_to_nwb.benisty_2024.utils import (
    get_event_times_from_mat,
    get_wheelspeed_trace_from_mat,
    get_wheel_times_from_mat,
)


def dual_imaging_session_to_nwb(
    data_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    subject_id: str,
    session_id: str,
    stub_test: bool = False,
):

    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"{session_id}_{subject_id}.nwb"

    source_data = dict()
    conversion_options = dict()

    # Add Analog signals from Spike2
    folder_path = data_dir_path / f"{subject_id}_1p"
    file_path = list(folder_path.glob(f"{session_id}*.smr"))[0]
    stream_ids, stream_names = get_streams(file_path=file_path)

    # Define each smr signal name
    # in the .log file 2p acquisition sync with "EyeCam"
    TTLsignals_name_map = {
        stream_ids[stream_names == "blue_LED"][0]: "TTLSignalBlueLED",
        stream_ids[stream_names == "uv_LED"][0]: "TTLSignalVioletLED",
        stream_ids[stream_names == "Galvo"][0]: "TTLSignal2PExcitation",
        stream_ids[stream_names == "EyeCam"][0]: "TTLSignalPupilCamera",
    }
    behavioral_name_map = {
        stream_ids[stream_names == "Wheel"][0]: "WheelSignal",
    }

    source_data.update(
        dict(
            Spike2Signals=dict(
                file_path=file_path,
                ttl_stream_ids_to_names_map=TTLsignals_name_map,
                behavioral_stream_ids_to_names_map=behavioral_name_map,
            )
        )
    )
    conversion_options.update(dict(Spike2Signals=dict(stub_test=stub_test)))

    # Add Processed Behavioral Signals
    wheel_timestamps_file_path = folder_path / f"{session_id}_wheelbinary.mat"
    wheel_speed_file_path = folder_path / f"{session_id}_wheelspeed.mat"
    wheel_speed_data, sampling_frequency = get_wheelspeed_trace_from_mat(file_path=wheel_speed_file_path)
    wheel_on_times, wheel_off_times = get_wheel_times_from_mat(file_path=wheel_timestamps_file_path)
    source_data.update(
        dict(
            ProcessedWheelSignalInterface=dict(
                wheel_speed_data=wheel_speed_data,
                sampling_frequency=sampling_frequency,
                wheel_on_times=wheel_on_times,
                wheel_off_times=wheel_off_times,
            )
        )
    )
    conversion_options.update(dict(ProcessedWheelSignalInterface=dict(stub_test=stub_test)))

    mat_file_path = folder_path / f"{session_id}.mat"
    # Add Visual Stimulus
    csv_file_path = folder_path / f"{session_id}.csv"
    if csv_file_path.is_file():
        start_times, stop_times = get_event_times_from_mat(file_path=str(mat_file_path), stream_name="diode")
        source_data.update(
            dict(
                VisualStimulusInterface=dict(
                    stimulus_name="VisualStimulus",
                    csv_file_path=csv_file_path,
                    start_times=start_times,
                    stop_times=stop_times,
                )
            )
        )
        conversion_options.update(dict(VisualStimulusInterface=dict(stub_test=stub_test)))

    # Add 2p Imaging
    imaging_path = data_dir_path / f"{subject_id}_2p"
    file_pattern = f"{session_id.split('_')[0]}_2p_{session_id.split('_')[1]}*.tif"
    source_data.update(dict(TwoPhotonImaging=dict(folder_path=str(imaging_path), file_pattern=file_pattern)))
    conversion_options.update(dict(TwoPhotonImaging=dict(stub_test=stub_test)))

    # Add Segmentation
    suite2p_path = imaging_path / f"{session_id.split('_')[0]}_2p_00001a" / "suite2p"
    source_data.update(dict(Suite2pSegmentation=dict(folder_path=suite2p_path)))
    conversion_options.update(dict(Suite2pSegmentation=dict(stub_test=stub_test)))

    # Add 1p Imaging
    meso_imaging_path = data_dir_path / f"{subject_id}_1p"
    file_pattern = f"{session_id.split('_')[0]}_1p_{session_id.split('_')[1]}*.tif"
    # # ad hoc extractor for 1p imaging to separate strobing blue vs violet excitation
    sampling_frequency = 9.15
    number_of_channels = 2

    channel_first_frame_index = 0
    source_data.update(
        dict(
            OnePhotonImaging=dict(
                folder_path=str(meso_imaging_path),
                file_pattern=file_pattern,
                number_of_channels=number_of_channels,
                channel_first_frame_index=channel_first_frame_index,
                sampling_frequency=sampling_frequency,
            )
        )
    )
    conversion_options.update(
        dict(OnePhotonImaging=dict(stub_test=stub_test, photon_series_type="OnePhotonSeries", photon_series_index=0))
    )

    channel_first_frame_index = 1
    source_data.update(
        dict(
            OnePhotonImagingIsosbestic=dict(
                folder_path=str(meso_imaging_path),
                file_pattern=file_pattern,
                number_of_channels=number_of_channels,
                channel_first_frame_index=channel_first_frame_index,
                sampling_frequency=sampling_frequency,
            )
        )
    )
    conversion_options.update(
        dict(
            OnePhotonImagingIsosbestic=dict(
                stub_test=stub_test, photon_series_type="OnePhotonSeries", photon_series_index=1
            )
        )
    )

    # Add processed imaging data
    processed_imaging_path = meso_imaging_path / f"{session_id}"
    # add Df_over_f imaging data from blue excitation
    file_path = processed_imaging_path / f"FIR_dff_blue.mat"
    source_data.update(
        dict(
            DffOnePhotonImaging=dict(
                file_path=str(file_path),
                sampling_frequency=sampling_frequency,
                process_type="dff_blue",
            )
        )
    )
    conversion_options.update(
        dict(
            DffOnePhotonImaging=dict(
                stub_test=stub_test,
                photon_series_type="OnePhotonSeries",
                photon_series_index=2,
                parent_container="processing/ophys",
            )
        )
    )
    # add Df_over_f imaging data from violet excitation (isosbestic control)
    file_path = processed_imaging_path / f"FIR_dff_uv.mat"
    source_data.update(
        dict(
            DffOnePhotonImagingIsosbestic=dict(
                file_path=str(file_path),
                sampling_frequency=sampling_frequency,
                process_type="dff_uv",
            )
        )
    )
    conversion_options.update(
        dict(
            DffOnePhotonImagingIsosbestic=dict(
                stub_test=stub_test,
                photon_series_type="OnePhotonSeries",
                photon_series_index=3,
                parent_container="processing/ophys",
            )
        )
    )
    # add hemodynamic corrected imaging data
    file_path = processed_imaging_path / f"FIR_DFF_patch11_final_dFoF.mat"
    source_data.update(
        dict(
            HemodynamicCorrectedOnePhotonImaging=dict(
                file_path=str(file_path),
                sampling_frequency=sampling_frequency,
                process_type="dff_final",
            )
        )
    )
    conversion_options.update(
        dict(
            HemodynamicCorrectedOnePhotonImaging=dict(
                stub_test=stub_test,
                photon_series_type="OnePhotonSeries",
                photon_series_index=4,
                parent_container="processing/ophys",
            )
        )
    )

    # Add ophys metadata
    ophys_metadata_path = Path(__file__).parent / "metadata" / "benisty_2024_dual_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)

    converter = Benisty2024NWBConverter(source_data=source_data, ophys_metadata=ophys_metadata)

    # Add datetime to conversion

    metadata = converter.get_metadata()
    metadata["Subject"].update(subject_id=subject_id)
    metadata["NWBFile"].update(session_id=f"{session_id}-{subject_id}")

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "benisty_2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":

    # Parameters for conversion
    root_path = Path("G:")
    data_dir_path = root_path / "Higley-CN-data-share/Dual 2p Meso data"
    output_dir_path = root_path / "Higley-conversion_nwb/"
    stub_test = True
    subject_id = "dbvdual035"
    session_id = "20201231_00002"
    dual_imaging_session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        subject_id=subject_id,
        session_id=session_id,
        stub_test=stub_test,
    )
