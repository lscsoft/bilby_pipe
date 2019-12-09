"""Plotting helper functions."""
import os
from typing import Optional

from gwpy.signal import filter_design
from gwpy.timeseries import TimeSeries

from bilby_pipe.utils import logger

# fmt: off
import matplotlib  # isort:skip
matplotlib.use("agg")
# fmt: on


def safe_run(func):
    """Try-catch gwpy_func_wrapper."""

    def gwpy_func_wrapper(*args, **kwargs):
        """Gwpy funct wrapper."""
        try:
            return func(*args, **kwargs)

        except UnboundLocalError:
            # Issue raised: https://github.com/gwpy/gwpy/issues/1144
            logger.warning(
                "Error with gwpy_plot of time and spectogram data. "
                "Skipping plotting. "
            )

    return gwpy_func_wrapper


@safe_run
def strain_spectogram_plot(
    det: str,
    data: TimeSeries,
    data_directory: str,
    label: Optional[str] = "spectogram",
    extra_label: Optional[str] = "",
    trigger_time: Optional[int] = None,
    duration: Optional[int] = None,
    post_trigger_duration: Optional[int] = None,
):
    """Save a timeseries and Q-transform spectrogram plot of the detector's data.

    Parameters
    ----------
    det: str
            The detector name corresponding to the key in data-dict
    data: gwpy.TimeSeries
        the timeseries strain data of a detector
    trigger_time: None or int
        The trigger time to where the plot is zoomed.
        If none, then will not zoom plot.
    duration: None or int
        The data duration to help zoom the plot to the trigger time
        If none, then will not zoom plot.
    post_trigger_duration: None or int
        The post_trigger_duration time to help zoom the plot to the trigger time.
        If none, then will not zoom plot.
    data_directory: str
            The data dir where the plot is stored.
    label: str
    extra_label: str
        A string identifier added to the name of the file

    Returns
    -------
    None

    File by the name `<outdir>/data/<Detector>_<Label>_<ExtraLabel>_data.png`
    is saved

    """
    # clean data
    filt_data = _filter_strain_data(data)

    # plot data
    det_color = {
        "H1": "gwpy:ligo-hanford",
        "L1": "gwpy:ligo-livingston",
        "V1": "gwpy:virgo",
        "K1": "gwpy:kagra",
    }
    plot, axes = matplotlib.pyplot.subplots(nrows=2, sharex=True, figsize=(8, 6))
    tax, qax = axes  # timeseries axis, q-transform spectogram axis
    tax.plot(filt_data, color=det_color[det])  # note: len(filt_data) < len(data)
    tax.set_xlabel("")
    tax.set_xscale("auto-gps")
    tax.set_ylabel("Strain amplitude")
    qax.imshow(data.q_transform())
    qax.set_yscale("log")
    qax.set_ylabel("Frequency [Hz]")
    qax.colorbar(label="Normalised energy")

    # zoom into trigger and plot line if the data contains trigger
    if (trigger_time and duration and post_trigger_duration is not None) and (
        data.t0.value < trigger_time < (data.t0.value + data.duration.value)
    ):
        tax.axvline(x=trigger_time, linewidth=2, color="k", linestyle="--")
        qax.axvline(x=trigger_time, linewidth=2, color="w", linestyle="--")
        offset = duration - post_trigger_duration
        xmin = trigger_time - (offset * 0.2)
        xmax = trigger_time + (offset * 0.1)
        tax.set_xlim(xmin, xmax)

    plot.savefig(
        os.path.join(data_directory, "_".join([det, label, extra_label, "data.png"]))
    )


def _filter_strain_data(data):
    """Apply general filtering techniques to clean strain data.

    Methods adapted from
    https://gwpy.github.io/docs/stable/examples/signal/gw150914.html

    Parameters
    ----------
    data: gwpy.timeseries.TimeSeries
        Strain data to be filtered

    Returns
    -------
    filtered_data: gwpy.timeseries.TimeSeries
        The filtered strain data.

    """
    sample_rate = data.sample_rate

    # remove low and high freq
    bp = filter_design.bandpass(50, 250, sample_rate)

    # notches for harmonics of the 60 Hz AC mains power
    notches = [filter_design.notch(line, sample_rate) for line in (60, 120, 180)]
    # combine filters
    zpk = filter_design.concatenate_zpks(bp, *notches)

    # apply filters
    filtered_data = data.filter(zpk, filtfilt=True)

    # crop corrupted data from filtering
    filtered_data = filtered_data.crop(*filtered_data.span.contract(1))

    return filtered_data
