"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
import datetime
from zoneinfo import ZoneInfo
from neo import io

from neuroconv.utils import load_dict_from_file, dict_deep_update

from higley_lab_to_nwb.benisty_2022 import Benisty2022NWBConverter
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2events_interface import get_streams



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

    # Add Analog signals from Spike2
    file_path = str(data_dir_path / session_id / f"{session_id}_spike2.smrx")
    stream_ids, stream_names = get_streams(file_path=file_path)
    
    # Add Wheel signal
    source_data.update(dict(Wheel=dict(file_path=file_path, stream_id=stream_ids[stream_names=="wheel"][0], es_key="WheelMotionSeries")))
    conversion_options.update(dict(Wheel=dict(stub_test=stub_test)))

    # Add TTL synch signals
    TTLsignals_name_map = {
        stream_ids[stream_names=="BL_LED"][0]:"TTLSignalBlueLED",
        stream_ids[stream_names=="UV_LED"][0]:"TTLSignalVioletLED",
        stream_ids[stream_names=="Green LED"][0]:"TTLSignalGreenLED",
        stream_ids[stream_names=="MesoCam"][0]:"TTLSignalMesoscopicCamera",
        stream_ids[stream_names=="R_mesocam"][0]:"TTLSignalRedMesoscopicCamera",
        stream_ids[stream_names=="pupilcam"][0]:"TTLSignalPupilCamera",
    }
    source_data.update(dict(TTLSignals=dict(file_path=file_path, stream_ids_to_names_map=TTLsignals_name_map)))

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
