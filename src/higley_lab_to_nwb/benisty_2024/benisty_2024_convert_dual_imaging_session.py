"""Convert one Benisty 2024 dual (2p and mesoscopic) imaging session to NWB."""

from pathlib import Path

from natsort import natsorted
from neuroconv.datainterfaces import FacemapInterface, ScanImageImagingInterface, Suite2pSegmentationInterface
from neuroconv.utils import dict_deep_update, load_dict_from_file

from higley_lab_to_nwb.benisty_2024 import Benisty2024NWBConverter
from higley_lab_to_nwb.benisty_2024.utils import (
    get_event_times_from_mat,
    get_wheel_times_from_mat,
    get_wheelspeed_trace_from_mat,
)
from higley_lab_to_nwb.interfaces import (
    ExternalStimuliInterface,
    FacemapPythonInterface,
    MesoscopicImagingMultiTiffStackInterface,
    ProcessedBehaviorInterface,
    ProcessedImagingInterface,
    Spike2SignalsInterface,
)
from higley_lab_to_nwb.interfaces.spike2signals_interface import get_streams

ONE_PHOTON_SAMPLING_FREQUENCY = 9.15  # frame rate of each excitation channel, in Hz


def dual_imaging_session_to_nwb(
    data_dir_path: str | Path,
    output_dir_path: str | Path,
    subject_id: str,
    session_id: str,
    stub_test: bool = False,
):
    data_dir_path = Path(data_dir_path)
    folder_path = data_dir_path / f"{subject_id}_1p"
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)
    nwbfile_path = output_dir_path / f"{session_id}_{subject_id}.nwb"

    interfaces = dict()
    conversion_options = dict()
    date, acquisition = session_id.split("_")[:2]

    # Spike2: TTL pulses and the raw wheel signal (in the .log file, the 2p acquisition is synced with "EyeCam")
    smr_file_path = next(folder_path.glob(f"{session_id}*.smr"))
    stream_ids, stream_names = get_streams(file_path=smr_file_path)
    ttl_stream_names = {
        "blue_LED": "TTLSignalBlueLED",
        "uv_LED": "TTLSignalVioletLED",
        "Galvo": "TTLSignal2PExcitation",
        "EyeCam": "TTLSignalPupilCamera",
    }
    interfaces["Spike2Signals"] = Spike2SignalsInterface(
        file_path=smr_file_path,
        ttl_stream_ids_to_names_map={
            stream_ids[stream_names == stream_name][0]: name for stream_name, name in ttl_stream_names.items()
        },
        behavioral_stream_ids_to_names_map={stream_ids[stream_names == "Wheel"][0]: "WheelSignal"},
    )
    conversion_options["Spike2Signals"] = dict(stub_test=stub_test)

    # Processed wheel signals
    wheel_speed_data, wheel_sampling_frequency = get_wheelspeed_trace_from_mat(
        file_path=folder_path / f"{session_id}_wheelspeed.mat"
    )
    wheel_on_times, wheel_off_times = get_wheel_times_from_mat(file_path=folder_path / f"{session_id}_wheelbinary.mat")
    interfaces["ProcessedWheelSignal"] = ProcessedBehaviorInterface(
        wheel_speed_data=wheel_speed_data,
        sampling_frequency=wheel_sampling_frequency,
        wheel_on_times=wheel_on_times,
        wheel_off_times=wheel_off_times,
    )
    conversion_options["ProcessedWheelSignal"] = dict(stub_test=stub_test)

    # Visual stimuli
    csv_file_path = folder_path / f"{session_id}.csv"
    if csv_file_path.is_file():
        start_times, stop_times = get_event_times_from_mat(
            file_path=folder_path / f"{session_id}.mat", stream_name="diode"
        )
        interfaces["VisualStimulus"] = ExternalStimuliInterface(
            stimulus_name="VisualStimulus", csv_file_path=csv_file_path, start_times=start_times, stop_times=stop_times
        )
        conversion_options["VisualStimulus"] = dict(stub_test=stub_test)

    # 2p imaging and its Suite2p segmentation
    imaging_path = data_dir_path / f"{subject_id}_2p"
    interfaces["TwoPhotonImaging"] = ScanImageImagingInterface(
        file_paths=natsorted(imaging_path.glob(f"{date}_2p_{acquisition}*.tif")), metadata_key="two_photon"
    )
    conversion_options["TwoPhotonImaging"] = dict(stub_test=stub_test, photon_series_type="TwoPhotonSeries")
    interfaces["Suite2pSegmentation"] = Suite2pSegmentationInterface(
        folder_path=imaging_path / f"{date}_2p_00001a" / "suite2p", metadata_key="suite2p"
    )
    conversion_options["Suite2pSegmentation"] = dict(stub_test=stub_test)

    # Mesoscopic imaging: blue and violet (isosbestic) excitation alternate frame by frame
    meso_imaging_path = data_dir_path / f"{subject_id}_1p"
    for name, first_frame_index, metadata_key in (
        ("OnePhotonImaging", 0, "raw_blue"),
        ("OnePhotonImagingIsosbestic", 1, "raw_violet"),
    ):
        interfaces[name] = MesoscopicImagingMultiTiffStackInterface(
            folder_path=meso_imaging_path,
            file_pattern=f"{date}_1p_{acquisition}*.tif",
            number_of_channels=2,
            channel_first_frame_index=first_frame_index,
            sampling_frequency=ONE_PHOTON_SAMPLING_FREQUENCY,
            metadata_key=metadata_key,
        )
        conversion_options[name] = dict(stub_test=stub_test, photon_series_type="OnePhotonSeries")

    # DF/F of each excitation, and the hemodynamic-corrected DF/F
    processed_imaging_path = meso_imaging_path / session_id
    for name, file_name, process_type, metadata_key in (
        ("DffOnePhotonImaging", "FIR_dff_blue.mat", "dff_blue", "dff_blue"),
        ("DffOnePhotonImagingIsosbestic", "FIR_dff_uv.mat", "dff_uv", "dff_violet"),
        (
            "HemodynamicCorrectedOnePhotonImaging",
            "FIR_DFF_patch11_final_dFoF.mat",
            "dff_final",
            "hemodynamic_corrected",
        ),
    ):
        interfaces[name] = ProcessedImagingInterface(
            file_path=processed_imaging_path / file_name,
            process_type=process_type,
            sampling_frequency=ONE_PHOTON_SAMPLING_FREQUENCY,
            metadata_key=metadata_key,
        )
        conversion_options[name] = dict(
            stub_test=stub_test, photon_series_type="OnePhotonSeries", parent_container="processing/ophys"
        )

    # TODO add the behavioral video once it is shared, and remove this path
    video_file_path = "G:/Higley-CN-data-share/04072021_am2psi_05_spont/04072021_am2psi_05_spont_facevideo.avi"

    # FaceMap output: from the MATLAB GUI ("inverted") and from the Python implementation
    for mat_file_path in folder_path.glob(f"{session_id}*_proc.mat"):
        if "inverted" in mat_file_path.name:
            interfaces["Facemap"] = FacemapInterface(
                file_path=mat_file_path, video_file_path=video_file_path, metadata_key="facemap"
            )
            conversion_options["Facemap"] = dict(first_n_components=10 if stub_test else 500)
        else:
            interfaces["FacemapPython"] = FacemapPythonInterface(
                mat_file_path=str(mat_file_path),
                video_file_path=str(video_file_path),
                svd_mask_names=["Face", "Whiskers", "Pupil"],  # TODO check with the lab point person
                first_n_components=10 if stub_test else None,
            )

    converter = Benisty2024NWBConverter(data_interfaces=interfaces)

    metadata = converter.get_metadata()
    metadata["Subject"]["subject_id"] = subject_id
    metadata["NWBFile"]["session_id"] = f"{session_id}-{subject_id}"
    metadata_dir_path = Path(__file__).parent
    metadata = dict_deep_update(metadata, load_dict_from_file(metadata_dir_path / "benisty_2024_metadata.yaml"))
    metadata = dict_deep_update(
        metadata, load_dict_from_file(metadata_dir_path / "metadata" / "benisty_2024_dual_ophys_metadata.yaml")
    )

    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":
    root_path = Path("G:")
    dual_imaging_session_to_nwb(
        data_dir_path=root_path / "Higley-CN-data-share/Dual 2p Meso data",
        output_dir_path=root_path / "Higley-conversion_nwb/",
        subject_id="dbvdual035",
        session_id="20201231_00001",
        stub_test=True,
    )
