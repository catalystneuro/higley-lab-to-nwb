"""Convert one Lohani 2022 session to NWB."""

from pathlib import Path

import numpy as np
from neuroconv.datainterfaces import ExternalVideoInterface, FacemapInterface
from neuroconv.tools.nwb_helpers import configure_and_write_nwbfile
from neuroconv.utils import dict_deep_update, load_dict_from_file

from higley_lab_to_nwb.interfaces import (
    AllenParcelsInterface,
    ExternalStimuliInterface,
    MesoscopicImagingMultiTiffSingleFrameInterface,
    ParcellsSegmentationInterface,
    ProcessedBehaviorInterface,
    ProcessedImagingInterface,
    Spike2SignalsInterface,
)
from higley_lab_to_nwb.interfaces.spike2signals_interface import get_streams
from higley_lab_to_nwb.lohani_2022 import Lohani2022NWBConverter
from higley_lab_to_nwb.lohani_2022.utils import (
    get_channel_trace_from_mat,
    get_event_times_from_mat,
    read_session_start_time,
)

SAMPLING_FREQUENCY = 10.0  # frame rate of each excitation channel, in Hz
# Excitation -> (camera, index of its first frame in the acquisition cycle, its channel in final_dFoF.mat)
EXCITATIONS = dict(Blue=("Green", 0, "blue"), Violet=("Green", 1, "uv"), Green=("Red", 2, "green"))
# Camera -> the half of the dual-camera frame it occupies
CAMERA_TO_FRAME_SIDE = dict(Green="right", Red="left")


def session_to_nwb(
    folder_path: str | Path,
    parcellation_folder_path: str | Path,
    output_dir_path: str | Path,
    session_id: str,
    allen_parcels_file_path: str | Path,
    stub_test: bool = False,
    verbose: bool = False,
):
    """Convert one session.

    Parameters
    ----------
    folder_path : str or Path
        The session folder of the raw data (TIFF, .smrx, .avi, FaceMap _proc.mat, visual stimulus .csv).
    parcellation_folder_path : str or Path
        The session folder of the lab's processed data (smrx_signals.mat, final_dFoF.mat, final_dFoF_parcels.mat
        and the parcellation .mat).
    output_dir_path : str or Path
        Where to write the NWB file.
    session_id : str
        "{date}_{subject_id}_{session_type}", for example "11232019_grabAM07_spont".
    allen_parcels_file_path : str or Path
        parcells_updated121519.mat from the lab's code (cardin-higley-lab/Lohani_Moberly_et_al_2022 at commit
        c337686, Figure3ExtractStatesCorrelation/Functions/), the Allen CCFv3 parcels that final_dFoF_parcels.mat is
        averaged over.
    stub_test : bool, default: False
        Write only the first 100 samples of each series, for testing.
    """
    folder_path = Path(folder_path)
    parcellation_folder_path = Path(parcellation_folder_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)
    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    date, subject_id, session_type = session_id.split("_", 2)
    search_pattern = f"{date}_{subject_id}"
    interfaces = dict()
    conversion_options = dict()

    # Spike2: TTL pulses and the raw wheel signal
    smrx_file_path = next(folder_path.glob(f"{search_pattern}*.smrx"))
    stream_ids, stream_names = get_streams(file_path=smrx_file_path)
    ttl_stream_names = {
        "BL_LED": "TTLSignalBlueLED",
        "UV_LED": "TTLSignalVioletLED",
        "Green LED": "TTLSignalGreenLED",
        "pupilcam": "TTLSignalPupilCamera",
    }
    interfaces["Spike2Signals"] = Spike2SignalsInterface(
        file_path=smrx_file_path,
        ttl_stream_ids_to_names_map={
            stream_ids[stream_names == stream_name][0]: name for stream_name, name in ttl_stream_names.items()
        },
        behavioral_stream_ids_to_names_map={stream_ids[stream_names == "wheel"][0]: "WheelSignal"},
    )
    conversion_options["Spike2Signals"] = dict(stub_test=stub_test)

    # Processed wheel signals
    signals_file_path = parcellation_folder_path / "smrx_signals.mat"
    wheel_speed_data, wheel_sampling_frequency = get_channel_trace_from_mat(
        file_path=signals_file_path, variable_name="wheelspeed"
    )
    wheel_on_times, wheel_off_times = get_event_times_from_mat(
        file_path=signals_file_path, start_time_variable_name="wheelOn", end_time_variable_name="wheelOff"
    )
    interfaces["ProcessedWheelSignal"] = ProcessedBehaviorInterface(
        wheel_speed_data=wheel_speed_data,
        sampling_frequency=wheel_sampling_frequency,
        wheel_on_times=wheel_on_times,
        wheel_off_times=wheel_off_times,
        wheel_speed_unit="m/s",
        wheel_speed_description="Wheel speed, computed by the lab's preprocessing code (wheel_changepoints.m) "
        "as the differential of the unwrapped wheel distance, smoothed with a Gaussian window 0.5 s long. "
        "The speed is signed: negative values are backward turns of the wheel. The wheel position was read by a "
        "magnetic angle sensor (Digikey). The paper reports speed in cm/s; the lab's code computes it in m/s.",
        wheel_activation_description="Locomotion epochs (wheelOn and wheelOff in the lab's smrx_signals.mat). The "
        "Methods detect locomotion as change points of the wheel speed, from a moving standard deviation in 2 s "
        "windows with a threshold of 0.005, and remove epochs shorter than 1 s or with a mean speed below 2 cm/s.",
    )
    conversion_options["ProcessedWheelSignal"] = dict(stub_test=stub_test)

    # Visual stimuli
    if session_type == "vis_stim":
        start_times, stop_times = get_event_times_from_mat(
            file_path=signals_file_path, start_time_variable_name="stimstart", end_time_variable_name="stimend"
        )
        interfaces["VisualStimulus"] = ExternalStimuliInterface(
            stimulus_name="VisualStimulus",
            csv_file_path=next(folder_path.glob(f"{search_pattern}*.csv")),
            start_times=start_times,
            stop_times=stop_times,
        )
        conversion_options["VisualStimulus"] = dict(stub_test=stub_test)

    # Air puffs: all of them; "airpuffstart" holds only those without a locomotion onset from 2 s before to 5 s after
    if session_type == "airpuffs":
        start_times, stop_times = get_event_times_from_mat(
            file_path=signals_file_path,
            start_time_variable_name="allairpuffstart",
            end_time_variable_name="allairpuffend",
        )
        start_times_without_locomotion, _ = get_event_times_from_mat(
            file_path=signals_file_path, start_time_variable_name="airpuffstart", end_time_variable_name="airpuffend"
        )
        without_locomotion = np.isin(np.atleast_1d(start_times), np.atleast_1d(start_times_without_locomotion))
        interfaces["Airpuff"] = ExternalStimuliInterface(
            stimulus_name="Airpuff",
            start_times=np.atleast_1d(start_times),
            stop_times=np.atleast_1d(stop_times),
            without_locomotion=without_locomotion.tolist(),
        )
        conversion_options["Airpuff"] = dict(stub_test=stub_test)

    # Raw imaging, then the DF/F, of each excitation channel
    for excitation, (camera, first_frame_index, _) in EXCITATIONS.items():
        interfaces[f"Imaging{excitation}"] = MesoscopicImagingMultiTiffSingleFrameInterface(
            folder_path=folder_path,
            file_pattern=session_id,
            frame_side=CAMERA_TO_FRAME_SIDE[camera],
            number_of_channels=len(EXCITATIONS),
            channel_first_frame_index=first_frame_index,
            sampling_frequency=SAMPLING_FREQUENCY,
            metadata_key=f"raw_{excitation.lower()}",
        )
        conversion_options[f"Imaging{excitation}"] = dict(stub_test=stub_test, photon_series_type="OnePhotonSeries")
    for excitation, (_, _, dff_channel) in EXCITATIONS.items():
        interfaces[f"DFFImaging{excitation}"] = ProcessedImagingInterface(
            file_path=parcellation_folder_path / "final_dFoF.mat",
            process_type=dff_channel,
            sampling_frequency=SAMPLING_FREQUENCY,
            metadata_key=f"dff_{excitation.lower()}",
        )
        conversion_options[f"DFFImaging{excitation}"] = dict(
            stub_test=stub_test, photon_series_type="OnePhotonSeries", parent_container="processing/ophys"
        )

    # The functional parcellation of the calcium DF/F, then the Allen CCFv3 parcels (after the imaging planes exist)
    interfaces["ParcellsSegmentation"] = ParcellsSegmentationInterface(
        file_path=next(parcellation_folder_path.glob(f"green_{session_id}*.mat")),
        sampling_frequency=SAMPLING_FREQUENCY,
        image_size=[256, 256],
        metadata_key="parcellation",
    )
    conversion_options["ParcellsSegmentation"] = dict(stub_test=stub_test)
    interfaces["AllenParcels"] = AllenParcelsInterface(
        file_path=parcellation_folder_path / "final_dFoF_parcels.mat",
        parcels_file_path=allen_parcels_file_path,
        sampling_frequency=SAMPLING_FREQUENCY,
        image_size=[256, 256],
    )
    conversion_options["AllenParcels"] = dict(stub_test=stub_test)

    # Face video and its FaceMap output
    video_file_path = next(folder_path.glob(f"{search_pattern}*.avi")).resolve()
    interfaces["Video"] = ExternalVideoInterface(file_paths=[video_file_path], metadata_key="face_video")
    interfaces["Facemap"] = FacemapInterface(
        file_path=next(folder_path.glob(f"{search_pattern}*_proc.mat")),
        video_file_path=video_file_path,
        metadata_key="facemap",
    )
    conversion_options["Facemap"] = dict(first_n_components=10 if stub_test else 500)

    converter = Lohani2022NWBConverter(data_interfaces=interfaces, verbose=verbose)

    metadata = converter.get_metadata()
    metadata["NWBFile"]["session_start_time"] = read_session_start_time(folder_path=folder_path)
    metadata["NWBFile"]["session_id"] = f"{date}_{session_type}"
    metadata["Subject"]["subject_id"] = subject_id
    metadata_dir_path = Path(__file__).parent
    editable_metadata = load_dict_from_file(metadata_dir_path / "lohani_2022_metadata.yaml")
    session_descriptions = editable_metadata.pop("SessionDescriptions")
    metadata["NWBFile"]["session_description"] = session_descriptions[session_type]
    metadata = dict_deep_update(metadata, editable_metadata)
    metadata = dict_deep_update(
        metadata, load_dict_from_file(metadata_dir_path / "metadata" / "lohani_2022_ophys_metadata.yaml")
    )
    metadata["Behavior"]["ExternalVideos"]["face_video"].update(
        name="FaceVideo",
        description="Video of the face, pupil and whiskers, taken with a CMOS camera (Blackfly S USB3, FLIR) at 10 Hz "
        "under infrared illumination. FaceMap computed the pupil and motion signals from it.",
    )
    facemap_metadata = metadata["Behavior"]["Facemap"]
    for region_metadata_key, region_name in (("facemap_multivideo", "Face"), ("facemap_roi1", "Whiskers")):
        if region_metadata_key in facemap_metadata["MotionSVDMasks"]:
            facemap_metadata["MotionSVDMasks"][region_metadata_key].update(
                name=f"MotionSVDMasks{region_name}",
                description=f"Motion SVD masks of the {region_name.lower()} region.",
                source_video_metadata_key="face_video",
            )
            facemap_metadata["MotionSVDSeries"][region_metadata_key].update(
                name=f"MotionSVDSeries{region_name}",
                description=f"Motion SVD components of the {region_name.lower()} region.",
            )

    converter.validate_metadata(metadata=metadata)
    converter.validate_conversion_options(conversion_options=conversion_options)
    converter.temporally_align_data_interfaces(metadata=metadata, conversion_options=conversion_options)
    nwbfile = converter.create_nwbfile(metadata=metadata, conversion_options=conversion_options)
    nwbfile.processing["ophys"].description = (
        "Processed optical physiology: DF/F images, and the parcellations of them."
    )

    # Shuffle before gzip for the raw (uint16) and DF/F (float32) images
    backend_configuration = converter.get_default_backend_configuration(nwbfile=nwbfile, backend="hdf5")
    for location, dataset_configuration in backend_configuration.dataset_configurations.items():
        if "OnePhotonSeries" in location and location.endswith("/data"):
            dataset_configuration.compressors = ["shuffle", "gzip"]
    configure_and_write_nwbfile(
        nwbfile=nwbfile, nwbfile_path=nwbfile_path, backend_configuration=backend_configuration, metadata=metadata
    )
    return nwbfile_path


if __name__ == "__main__":
    root_path = Path("F:")
    data_dir_path = root_path / "Higley-CN-data-share"
    output_dir_path = root_path / "Higley-conversion_nwb"
    session_id = "11232019_grabAM05_airpuffs"
    date, subject_id, _ = session_id.split("_", 2)
    session_to_nwb(
        folder_path=data_dir_path / "Lohani22 Meso Data" / session_id,
        parcellation_folder_path=data_dir_path
        / "Lohani22 Parcellated data"
        / subject_id.replace("AM", "")
        / "imaging with 575 excitation"
        / session_id,
        output_dir_path=output_dir_path,
        session_id=session_id,
        allen_parcels_file_path=data_dir_path / "parcells_updated121519.mat",
        stub_test=True,
        verbose=True,
    )
