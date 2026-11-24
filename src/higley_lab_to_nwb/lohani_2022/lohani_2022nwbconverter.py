"""Converter for the Lohani 2022 sessions."""

import warnings

import numpy as np
from neuroconv import ConverterPipe

# The lab's detrending (detrend_all_pixels.m, filter length 1000) removes the first 499 frames of each excitation
# channel, so DF/F frame 0 is raw frame 499 (0-based), as in the lab's smrxExtractionPreProcessing.m.
FIRST_DFF_FRAME_INDEX = 499
# The parcellation traces have 300 frames fewer than the DF/F; their frame 0 is DF/F frame 150.
FIRST_PARCELLATED_FRAME_INDEX = FIRST_DFF_FRAME_INDEX + 150

# Excitation -> the name of its LED channel in Spike2SignalsInterface and its channel in final_dFoF_parcels.mat
EXCITATIONS = dict(
    Blue=("TTLSignalBlueLED", "blue"),
    Violet=("TTLSignalVioletLED", "uv"),
    Green=("TTLSignalGreenLED", "green"),
)


def _set_frame_times(interface, pulse_times: np.ndarray, first_pulse_index: int, name: str) -> None:
    """Time frame i of an imaging or segmentation interface at LED pulse first_pulse_index + i.

    When the channel has fewer pulses than frames, which should not happen, only the first frame is placed on its
    pulse, the rest follow at the nominal rate, and a warning says so.
    """
    alignment = interface.temporal_alignment
    key = alignment.keys()[0]
    num_frames = len(alignment[key].get_times())
    frame_pulse_times = pulse_times[first_pulse_index : first_pulse_index + num_frames]
    if len(frame_pulse_times) == num_frames:
        alignment[key].set_times(frame_pulse_times)
    else:
        warnings.warn(
            f"{name}: {num_frames} frames but only {len(frame_pulse_times)} LED pulses from pulse "
            f"{first_pulse_index}; writing the first frame at its pulse and the rest at the nominal rate."
        )
        alignment[key].move_earliest_observation_to(pulse_times[first_pulse_index])


class Lohani2022NWBConverter(ConverterPipe):
    """The interfaces of one Lohani 2022 session, aligned to the Spike2 clock.

    The interfaces are named: "Spike2Signals", "Imaging{Excitation}" and "DFFImaging{Excitation}" for each
    excitation in EXCITATIONS, "ParcellsSegmentation", "AllenParcels", "Video", "Facemap", "ProcessedWheelSignal",
    "VisualStimulus" and "Airpuff". All but "Spike2Signals" are optional.
    """

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        interfaces = self.data_interface_objects
        spike2 = interfaces["Spike2Signals"]

        for excitation, (ttl_channel_name, parcels_channel) in EXCITATIONS.items():
            led_times = spike2.get_event_times_from_ttl_channel_name(channel_name=ttl_channel_name)

            if f"Imaging{excitation}" in interfaces:
                _set_frame_times(interfaces[f"Imaging{excitation}"], led_times, 0, name=f"Imaging{excitation}")
            if f"DFFImaging{excitation}" in interfaces:
                _set_frame_times(
                    interfaces[f"DFFImaging{excitation}"],
                    led_times,
                    FIRST_DFF_FRAME_INDEX,
                    name=f"DFFImaging{excitation}",
                )
            # The Allen parcel traces are averages of the DF/F frames, so they start with them
            if "AllenParcels" in interfaces:
                interfaces["AllenParcels"].set_aligned_starting_time(
                    channel=parcels_channel, starting_time=led_times[FIRST_DFF_FRAME_INDEX]
                )
            # The functional parcellation is computed on the Green excitation (calcium) DF/F
            if excitation == "Green" and "ParcellsSegmentation" in interfaces:
                _set_frame_times(
                    interfaces["ParcellsSegmentation"],
                    led_times,
                    FIRST_PARCELLATED_FRAME_INDEX,
                    name="ParcellsSegmentation",
                )

        # Video frame i is at pupil camera pulse i, as in the lab's analysis code
        pupil_camera_times = spike2.get_event_times_from_ttl_channel_name(channel_name="TTLSignalPupilCamera")
        for name in ("Video", "Facemap"):
            if name not in interfaces:
                continue
            alignment = interfaces[name].temporal_alignment
            key = alignment.keys()[0]
            num_frames = len(alignment[key].get_times())
            if len(pupil_camera_times) < num_frames:
                raise ValueError(
                    f"Fewer pupil camera pulses ({len(pupil_camera_times)}) than {name} frames ({num_frames})."
                )
            alignment[key].set_times(pupil_camera_times[:num_frames])
