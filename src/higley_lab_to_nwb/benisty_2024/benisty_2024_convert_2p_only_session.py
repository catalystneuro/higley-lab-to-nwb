"""Convert one Benisty 2024 2p-only session to NWB."""

from pathlib import Path

from natsort import natsorted
from neuroconv.datainterfaces import (
    ExternalVideoInterface,
    FacemapInterface,
    ScanImageImagingInterface,
    Suite2pSegmentationInterface,
)
from neuroconv.utils import dict_deep_update, load_dict_from_file

from higley_lab_to_nwb.benisty_2024 import Benisty2024NWBConverter
from higley_lab_to_nwb.interfaces import CidanSegmentationInterface, ExternalStimuliInterface, Spike2SignalsInterface
from higley_lab_to_nwb.interfaces.spike2signals_interface import get_streams


def session_to_nwb(folder_path: str | Path, output_dir_path: str | Path, session_id: str, stub_test: bool = False):
    folder_path = Path(folder_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)
    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    interfaces = dict()
    conversion_options = dict()
    search_pattern = "_".join(session_id.split("_")[:2])

    # Spike2: TTL pulses and the raw wheel signal
    smrx_file_path = next(folder_path.glob(f"{search_pattern}*.smrx"))
    stream_ids, stream_names = get_streams(file_path=smrx_file_path)
    spike2 = Spike2SignalsInterface(
        file_path=smrx_file_path,
        ttl_stream_ids_to_names_map={
            stream_ids[stream_names == "galvo"][0]: "TTLSignal2PExcitation",
            stream_ids[stream_names == "pupilcam"][0]: "TTLSignalPupilCamera",
        },
        behavioral_stream_ids_to_names_map={stream_ids[stream_names == "wheel"][0]: "WheelSignal"},
    )
    interfaces["Spike2Signals"] = spike2
    conversion_options["Spike2Signals"] = dict(stub_test=stub_test)

    # Visual stimuli: on and off times from the Spike2 "Vis" channel
    if "vis_stim" in session_id:
        stimulus_stream_id = stream_ids[stream_names == "Vis"][0]
        interfaces["VisualStimulus"] = ExternalStimuliInterface(
            stimulus_name="VisualStimulus",
            csv_file_path=next(folder_path.glob(f"{search_pattern}*.csv")),
            start_times=spike2.get_event_times_from_ttl(stream_id=stimulus_stream_id, rising=True),
            stop_times=spike2.get_event_times_from_ttl(stream_id=stimulus_stream_id, rising=False),
        )
        conversion_options["VisualStimulus"] = dict(stub_test=stub_test)

    # 2p imaging
    imaging_path = folder_path / "tiff"
    two_photon_imaging = ScanImageImagingInterface(
        file_paths=natsorted(imaging_path.glob("*.tif")), metadata_key="two_photon"
    )
    interfaces["TwoPhotonImaging"] = two_photon_imaging
    conversion_options["TwoPhotonImaging"] = dict(stub_test=stub_test, photon_series_type="TwoPhotonSeries")

    # Suite2p and CIDAN segmentations
    interfaces["Suite2pSegmentation"] = Suite2pSegmentationInterface(
        folder_path=folder_path / "suite2p", metadata_key="suite2p"
    )
    conversion_options["Suite2pSegmentation"] = dict(stub_test=stub_test)
    cidan_path = folder_path / "CIDAN"
    interfaces["CIDANSegmentation"] = CidanSegmentationInterface(
        parameters_file_path=cidan_path / "parameters.json",
        roi_list_file_path=cidan_path / "roi_list.json",
        mat_file_path=cidan_path / "timetraces.mat",
        sampling_frequency=two_photon_imaging.imaging_extractor.get_sampling_frequency(),
        image_size=list(two_photon_imaging.imaging_extractor.get_image_shape()),
        metadata_key="cidan",
    )
    conversion_options["CIDANSegmentation"] = dict(stub_test=stub_test)

    # Face video and its FaceMap (MATLAB GUI) output
    video_file_path = next(folder_path.glob(f"{search_pattern}*.avi")).resolve()
    interfaces["Video"] = ExternalVideoInterface(file_paths=[video_file_path], metadata_key="face_video")
    interfaces["Facemap"] = FacemapInterface(
        file_path=next(folder_path.glob(f"{search_pattern}*_proc.mat")),
        video_file_path=video_file_path,
        metadata_key="facemap",
    )
    conversion_options["Facemap"] = dict(first_n_components=10 if stub_test else 500)

    converter = Benisty2024NWBConverter(data_interfaces=interfaces)

    metadata = converter.get_metadata()
    metadata["Subject"]["subject_id"] = session_id.split("_")[1]
    metadata["NWBFile"]["session_id"] = session_id
    metadata_dir_path = Path(__file__).parent
    metadata = dict_deep_update(metadata, load_dict_from_file(metadata_dir_path / "benisty_2024_metadata.yaml"))
    metadata = dict_deep_update(
        metadata, load_dict_from_file(metadata_dir_path / "metadata" / "benisty_2024_ophys_2p_only_metadata.yaml")
    )

    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":
    root_path = Path("G:")
    data_dir_path = root_path / "Higley-CN-data-share"
    session_id = "04072021_am2psi_05_spont"
    session_to_nwb(
        folder_path=data_dir_path / session_id,
        output_dir_path=root_path / "Higley-conversion_nwb/",
        session_id=session_id,
        stub_test=True,
    )
