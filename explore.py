#%% 
channel_name_id_mapping = dict(Blue=0, UV=1, Green=2)
photon_series_index = 0
for excitation_type in ["Blue", "UV", "Green"]:
    for channel in ["Green", "Red"]:
        suffix = f"{excitation_type}Excitation{channel}Channel"
        interface_name = f"Imaging{suffix}" 
        print(interface_name+"=Benisty2022ImagingInterface,")
#%% import
import matplotlib.pyplot as plt
from natsort import natsorted
from pathlib import Path
session_id = '11222019'
subject_id = 'grabAM05'
behaviour = 'vis_stim' # 'vis_stim' 'spont'
folder_path = Path(f"/media/amtra/Samsung_T5/CN_data/Higley-CN-data-share/{session_id}_{subject_id}_{behaviour}")
path_to_save_nwbfile = Path("/media/amtra/Samsung_T5/CN_data/Higley-conversion_nwb")
assert folder_path.is_dir()
#%% Explore .tif
import tifffile
tif_files = natsorted(folder_path.glob("*.tif")) 
with tifffile.TiffFile(tif_files[0]) as tif:
    image = tif.asarray()
    # If the TIFF file contains metadata:
    metadata = tif.pages[0].tags['ImageDescription'].value
# %% Explore .tif
from ScanImageTiffReader import ScanImageTiffReader
# Show ScanImage metadata and plot first n frames
n_frames = 4
tif_files = natsorted(folder_path.glob("*.tif")) 
for i in range(n_frames):
    with ScanImageTiffReader(tif_files[i]) as reader:
        print("metadata: \n",reader.metadata())
        print("description: \n",reader.description(0))
        print(reader.shape())
        frame = reader.data()
        plt.imshow(frame)
        plt.title(f"frame {i}")
        plt.show()

#%% Explore .smrx file Spike2 data with neo
from neo import io
file_path = folder_path / f"{session_id}_{subject_id}_{behaviour}_spike2.smrx"
r = io.CedIO(filename=file_path)
signal_streams = r.header["signal_streams"]
stream_ids = list(signal_streams["id"])
signal_channels = r.header["signal_channels"]
channel_names = signal_channels["name"]
print(signal_streams)
print(signal_channels)
# %% Explore .smrx file Spike2 data not working because Spike2RecordingInterface does not take stream_id as argument
from pathlib import Path
from higley_lab_to_nwb.benisty_2022.benisty_2022_spike2ttleventsinterface import Benisty2022Spike2EventsInterface
file_path = folder_path / f"{session_id}_{subject_id}_{behaviour}_spike2.smrx"
interface = Benisty2022Spike2EventsInterface(file_path=file_path, stream_id='0')
# %% Explore .smrx file Spike2 with CedRecordingExtractor
from spikeinterface.extractors.neoextractors.ced import CedRecordingExtractor
file_path = folder_path / f"{session_id}_{subject_id}_{behaviour}_spike2.smrx"
behavioral_stream = [3,4,5]
for i in behavioral_stream:
    extractor = CedRecordingExtractor(file_path=file_path, stream_id=str(i))
    trace = extractor.get_traces(segment_index=0,start_frame=967160,end_frame=1017540)
    plt.plot(trace*signal_channels["gain"][i], label=signal_channels["name"][i])
plt.title("Wheel")
plt.legend()
plt.show()
# %% Explore .smrx file Spike2 with CedRecordingExtractor
imaging_stream = [0,1,8,2,6,7]
colors = ["blue", "purple", "green", "black", "red", "grey"]
for i,c in zip(imaging_stream,colors):
    extractor = CedRecordingExtractor(file_path=file_path, stream_id=str(i))
    trace = extractor.get_traces(segment_index=0,start_frame=49000,end_frame=51000)
    plt.plot(trace, label=signal_channels["name"][i], color=c)
plt.title("TTL signals for calcium imaging and behavioral cameras")
plt.legend()
plt.show()
# %% extract rising times
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
extractor = CedRecordingExtractor(file_path=file_path, stream_id=str(0))
rising_frames = get_rising_frames_from_ttl(
    trace=extractor.get_traces()
)
spike2_timestamps = extractor.get_times()
rising_times = spike2_timestamps[rising_frames]

# %% sync imaging and TTL signals
from spikeinterface.extractors.neoextractors.ced import CedRecordingExtractor
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
extractor = CedRecordingExtractor(file_path=file_path, stream_id=str(2)) #from mesocam 
rising_frames = get_rising_frames_from_ttl(
    trace=extractor.get_traces()
)
spike2_timestamps = extractor.get_times()
rising_times = spike2_timestamps[rising_frames]

from roiextractors.extractors.tiffimagingextractors.scanimagetiff_utils import extract_extra_metadata
from datetime import datetime
metadata = extract_extra_metadata(tif_files[0])
time_object = datetime.strptime(metadata['Time_From_Start'],  "%H:%M:%S.%f")
seconds_from_start_SI = (time_object.hour * 3600) + (time_object.minute * 60) + time_object.second + (time_object.microsecond / 1e6)
seconds_from_start_TTL_spike2 = rising_times[0]
timestamps = []
for tif_file in tif_files[:20]:
    metadata = extract_extra_metadata(tif_file)
    time_object = datetime.strptime(metadata['Time_From_Start'],  "%H:%M:%S.%f")
    timestamp = (time_object.hour * 3600) + (time_object.minute * 60) + time_object.second + (time_object.microsecond / 1e6)
    timestamp = timestamp
    timestamps.append(timestamp)

print(timestamps)
print(rising_times[:20])
# %% Explore visual stimulus .csv
import pandas as pd
csv_file_path = folder_path / f"{session_id}_{subject_id}_vis_stimulation1.csv"

df = pd.read_csv(csv_file_path)
print(df)
# %% Explore pupile tracking .mat
mat_file_path = folder_path / f"{session_id}_{subject_id}_visual_stim_proc.mat"
import h5py
mat_file =  h5py.File(mat_file_path, 'r') 
data_variable = mat_file['proc']


# %% TEST EXTRACTORS nwb file----------------------------------------------------------------------- 
from src.higley_lab_to_nwb.benisty_2022.benisty_2022_imagingextractor import Benisty2022ImagingExtractor
extractor = Benisty2022ImagingExtractor(folder_path=folder_path)
# %% READ nwb file----------------------------------------------------------------------- 
from pynwb import NWBHDF5IO
file_path = path_to_save_nwbfile / "11222019_grabAM05_spont.nwb"
io = NWBHDF5IO(str(file_path), mode='r')
nwbfile = io.read()
# nwbfile

# %%
