# Notes concerning the benisty_2024 conversion
* dual mesoscopic and 2-photon imaging data, .tiff files with ScanImage format (custom microscope) --> only mesoscopic shared ([Raw Imaging](#raw-imaging))
* output for rigid transformation, hemodynamic corrections, and filtering 
* ROI segmentation (functional parcellation with Local Selective Spectral Clustering)

## Raw Imaging 
### Method description from [Benisty 2024](https://www.nature.com/articles/s41593-023-01498-y):
**Mesoscopic imaging**
Widefield mesoscopic calcium imaging was performed using a Zeiss Axiozoom with a 1×, 0.25 NA objective with a 56 mm working distance (Zeiss). Epifluorescent excitation was provided by an LED bank (Spectra X Light Engine, Lumencor) using two output wavelengths: 395/25 (isosbestic for GRABACh3.0) and 575/25 nm (jRCaMP1b). Emitted light passed through a dual camera image splitter (TwinCam, Cairn Research) then through either a 525/50 (GRABACh3.0) or 630/75 (jRCaMP1b) emission filter (Chroma) before it reached two sCMOS cameras (Orca-Flash V3, Hamamatsu). Images were acquired at 512×512 resolution after 4× pixel binning, and each channel was acquired at 10 Hz with 20 ms exposure using HCImage software (Hamamatsu).

**Two-photon imaging**
Two-photon imaging was performed using a MOM microscope (Sutter Instruments) coupled to a 16×, 0.8 NA objective (Nikon). Excitation was driven by a Titanium-Sapphire Laser (Mai-Tai eHP DeepSee, Spectra-Physics) tuned to 920 nm. Emitted light was collected through a 525/50 filter and a gallium arsenide phosphide photomultiplier tube (Hamamatsu). Images were acquired at 512×512 resolution at 30 Hz using a galvo-resonant scan system controlled by ScanImage software (Vidrio).

**Dual mesoscopic and two-photon imaging**
Dual imaging was carried out using a custom microscope combining a Zeiss Axiozoom (as above) and a Sutter MOM (as above), as described previously 25. To image through the implanted prism, a long-working distance objective (20×, 0.4 NA, Mitutoyo) was used. Frame acquisitions were interleaved with an overall rate of 9.15 Hz, with each cycle alternating sequentially between a 920nm two-photon acquisition (512×512 resolution), a 395/25nm widefield excitation acquisition, and a 470/20nm widefield excitation acquisition. Widefield data were collected through a 525/50nm filter into a sCMOS camera (Orca Fusion, Hamamatsu) at 576×576 resolution after 45× pixel binning with 20ms exposure.


### Data structure:
- **Each .tif is a trial of N frame of [512,512]**

- **CIDAN output**
    - parameters.json: file containing all the settings for the algorithm
    ```json
    {
    "global_params": {},
    "dataset_params": {
        "dataset_folder_path": "/home/sschickl/Downloads/animal7",
        "trials_loaded": ["file_00001_00001.tif"],
        "trials_all": ["file_00001_00001.tif"],
        "single_file_mode": true,
        "original_folder_trial_split": ["file_00001_00001.tif"],
        "slice_stack": false,
        "slice_every": 3,
        "slice_start": 0,
        "crop_stack": true,
        "crop_x": [20,490],
        "crop_y": [20,490],
        "trial_split": true,
        "trial_length": 500,
        "auto_crop": false
    },
    "filter_params": {
        "median_filter": false,
        "median_filter_size": 3,
        "z_score": false,
        "hist_eq": true,
        "localSpatialDenoising": true,
        "pca": false,
        "pca_threshold": 0.97
    },
    "box_params": {
        "total_num_time_steps": 4,
        "total_num_spatial_boxes": 1,
        "spatial_overlap": 40
    },
    "eigen_params": {
        "eigen_vectors_already_generated": false,
        "num_eig": 50,
        "normalize_w_k": 32,
        "metric": "l2",
        "knn": 50,
        "accuracy": 75,
        "eigen_accuracy": 8,
        "connections": 40
    },
    "roi_extraction_params": {
        "elbow_threshold_method": true,
        "elbow_threshold_value": 0.95,
        "eigen_threshold_method": true,
        "eigen_threshold_value": 0.5,
        "num_eigen_vector_select": 1,
        "merge_temporal_coef": 0.9,
        "roi_size_min": 30,
        "roi_size_max": 600,
        "merge": true,
        "num_rois": 150,
        "fill_holes": true,
        "refinement": true,
        "max_iter": 100,
        "roi_circ_threshold": 0,
        "roi_eccentricity_limit": 0.8,
        "local_max_method": false
    },
    "time_trace_params": {
        "min_neuropil_pixels": 25
    }
    }
    ```
    - roi_list.json: file containing the pixel_mask for each roi
    ```json
    [
        {
            "id": 0,
            "coordinates": [[286,276],[286,278],[287,274],...],
        }
        {
            "id": 1,
            "coordinates": [...],
        }
        {
            "id": 2,
            "coordinates": [...],
        }
        {
            "id": 3,
            "coordinates": [...],
        }
        ...
    ]
    ```
    - timetraces.mat: file containing df/f traces (simple rois x frames matrix)

### Imaging metadata (from Benisty paper)
- Custom miscroscope: see description in the methods
- stimulation wavelengths for the three optical channel: Imaging was performed by strobing 575 nm (jRCaMP1b), 470 nm (ACh3.0) and 395 nm (control)
excitation light
- emission filters: 525/50 or 630/75 (Chroma)
- image dimension: 512×512 
- indicators: Here, we use dual-color mesoscopic imaging of the red-fluorescent calcium indicator jRCaMP1b36 and the green-fluorescent ACh indicator ACh3.0 across the entire dorsal neocortex of the awake mouse to quantify the relationships between behavioral state, cortical activity and cholinergic signaling.

##Lab Code
* [Benisty 2024](https://github.com/cardin-higley-lab/Benisty_Higley_2023)