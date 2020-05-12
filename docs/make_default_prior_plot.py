"""
Make a plot of the default prior's mass ranges.
"""
import glob
import logging
import os
import re
from typing import List

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch
from tqdm import tqdm

import bilby_pipe
from bilby.core.prior import PriorDict
from bilby.gw.conversion import (
    chirp_mass_and_mass_ratio_to_total_mass,
    component_masses_to_chirp_mass,
    component_masses_to_mass_ratio,
    total_mass_and_mass_ratio_to_component_masses,
)

# fmt: off
import matplotlib  # isort:skip noqa


matplotlib.use("agg")  # noqa
import matplotlib.pyplot as plt  # noqa isort:skip

# fmt: on

logging.basicConfig(level=logging.INFO)

MASS_1 = "mass_1"
MASS_2 = "mass_2"
CHIRP_MASS = "chirp_mass"
MASS_RATIO = "mass_ratio"
RESOLUTION = 1000
TRANSPARENT = (1, 1, 1, 0)


def adjust_matplotlib_settings():
    """Wraps matplotlib settings in a function."""
    font = {"weight": "bold", "size": 22, "family": "sans-serif"}
    matplotlib.rc("font", **font)
    matplotlib.rc("text", usetex=True)
    matplotlib.rcParams["mathtext.fontset"] = "dejavusans"


@np.vectorize
def correct_ordering_of_component_masses(mass_1, mass_2):
    """Ensure mass 1 always greater than mass 2."""
    if mass_1 > mass_2:
        return mass_1, mass_2
    else:
        return mass_2, mass_1


def get_masses_sample_from_prior(prior, num_samples):
    """Sample chirp mass and q from the prior space and returns all mass parameters.

    Parameters
    ----------
    prior: prior dictionary with `chirp_mass' and `mass_ratio'.
    num_samples: number of samples to be taken from the prior file.

    Returns
    -------
    Pandas dataframe with the samples.

    """
    # vectorize some conversion functions
    total_mass_conversion = np.vectorize(chirp_mass_and_mass_ratio_to_total_mass)
    component_mass_conversion = np.vectorize(
        total_mass_and_mass_ratio_to_component_masses
    )

    # sample prior space and convert to all mass params
    samples = pd.DataFrame(prior.sample(size=num_samples))
    chirp_mass = samples[CHIRP_MASS].values
    mass_ratio = samples[MASS_RATIO].values
    total_mass = total_mass_conversion(chirp_mass=chirp_mass, mass_ratio=mass_ratio)
    mass_1, mass_2 = component_mass_conversion(
        total_mass=total_mass, mass_ratio=mass_ratio
    )
    mass_1, mass_2 = correct_ordering_of_component_masses(mass_1, mass_2)

    mass_dataframe = pd.DataFrame(
        {MASS_1: mass_1, MASS_2: mass_2, CHIRP_MASS: chirp_mass, MASS_RATIO: mass_ratio}
    )
    return mass_dataframe


def get_prior_files() -> List[str]:
    """Return a list of paths to prior files in bilby_pipe's data files."""
    module_root, _ = os.path.split(bilby_pipe.__file__)
    prior_path = os.path.join(module_root, r"data_files/*[0-9]s.prior")
    paths = glob.glob(prior_path)
    paths.sort(key=lambda f: int(re.sub(r"\D", "", f)))
    return paths


def load_priors(prior_files):
    """Return a dict of the {prior_file_name: PriorDict}."""
    loaded_priors = dict()
    for prior_file in prior_files:
        prior_file_basename = os.path.basename(prior_file)
        prior = PriorDict(filename=prior_file)
        loaded_priors.update({prior_file_basename: prior})
    return loaded_priors


def get_m1m2_grid(m1_range, m2_range, prior, resolution):
    """Generate a grid of m1 and m2 and mark point if in prior space."""
    xs = np.linspace(m1_range[0], m1_range[1], resolution)
    ys = np.linspace(m2_range[0], m2_range[1], resolution)[::-1]
    m1, m2 = np.meshgrid(xs, ys)
    in_prior = np.zeros(shape=(len(xs), len(ys)))
    for nrx, loop_m1 in enumerate(tqdm(xs)):
        for nry, loop_m2 in enumerate(ys):
            if loop_m2 > loop_m1:
                pass  # by definition, we choose only m2 smaller than m1
            if loop_m2 < loop_m1:
                mc = component_masses_to_chirp_mass(loop_m1, loop_m2)
                q = component_masses_to_mass_ratio(loop_m1, loop_m2)
                in_prior[nry][nrx] = prior.prob(
                    dict(chirp_mass=mc, mass_ratio=q, mass_2=loop_m2)
                )
    return m1, m2, in_prior


def get_qmc_grid(q_range, mc_range, prior, resolution):
    """Generate a grid of q and mc and mark point if in prior space."""
    xs = np.linspace(q_range[0], q_range[1], resolution)
    ys = np.linspace(mc_range[0], mc_range[1], resolution)[::-1]
    q, mc = np.meshgrid(xs, ys)
    z = np.zeros(shape=(len(xs), len(ys)))
    for nrx, loop_q in enumerate(tqdm(xs)):
        for nry, loop_mc in enumerate(ys):
            z[nry][nrx] = prior.prob(dict(chirp_mass=loop_mc, mass_ratio=loop_q))
    return q, mc, z


def get_colors(num_colors, alpha):
    """Get a list of colorblind colors."""
    cs = sns.color_palette(palette="colorblind", n_colors=num_colors)
    cs = [list(c) for c in cs]
    for i in range(len(cs)):
        cs[i].append(alpha)
    return cs


def make_prior_plot(prior_files_dict, x_key, y_key, get_grid, resolution):
    """Generate prior plot with x and y axis being some combination of mass params."""
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    cs = get_colors(len(prior_files_dict), alpha=0.8)
    legend_elements = []
    for i, (file, pri) in enumerate(prior_files_dict.items()):
        logging.info(f"Creating bounds for {file}")
        mass_data = get_masses_sample_from_prior(pri, 1000)
        x_vals = mass_data[x_key].values
        y_vals = mass_data[y_key].values
        x_range = [min(0.8 * x_vals), max(x_vals * 1.2)]
        y_range = [min(0.8 * y_vals), max(y_vals * 1.2)]
        x, y, z = get_grid(x_range, y_range, pri, resolution)
        assert np.count_nonzero(z) > 0, f"None of the sampled values are in {file}"
        label = file.replace(".prior", "")
        if i % 2 != 0:
            ax.contour(
                x,
                y,
                z,
                levels=1,
                colors="k",
                linewidths=1,
                linestyles="solid",
                alpha=0.4,
            )
            ax.contourf(x, y, z, levels=1, colors=[TRANSPARENT, cs[i]])
            legend_elements.append(Patch(facecolor=cs[i], edgecolor="k", label=label))
        else:
            ax.contourf(x, y, z, levels=1, colors=[TRANSPARENT, cs[i]])
            legend_elements.append(Patch(facecolor=cs[i], label=label))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.tick_params(which="both", width=1)
    ax.tick_params(which="major", length=8)
    ax.tick_params(which="minor", length=5)

    ax.legend(
        handles=legend_elements, loc="upper left", prop={"size": 12, "weight": "normal"}
    )
    return fig


def make_q_mc_plot(filename, resolution):
    logging.info(f"Creating prior-plot for {MASS_RATIO} and {CHIRP_MASS}")
    priors = load_priors(get_prior_files())
    fig = make_prior_plot(
        priors, MASS_RATIO, CHIRP_MASS, get_grid=get_qmc_grid, resolution=resolution
    )
    ax = fig.axes[0]
    ax.set_ylabel(r"$q^{lab}$")
    ax.set_xlabel(r"$\mathcal{M}^{lab}\ [M_{\odot}]$")
    ax.set_xlim(0.125, 1)
    ax.set_xscale("linear")
    fig.savefig(filename)


def make_m1m2_plot(filename, resolution):
    logging.info(f"Creating prior-plot for {MASS_1} and {MASS_2}")
    priors = load_priors(get_prior_files())
    fig = make_prior_plot(
        priors, MASS_1, MASS_2, get_grid=get_m1m2_grid, resolution=resolution
    )
    ax = fig.axes[0]
    ax.set_ylabel(r"$m_2^{lab}\ [M_{\odot}]$")
    ax.set_xlabel(r"$m_1^{lab}\ [M_{\odot}]$")
    fig.savefig(filename)


def main():
    make_m1m2_plot("component_mass_distribution_of_priors.png", resolution=RESOLUTION)
    make_q_mc_plot("chirp_mass_distribution_of_priors.png", resolution=RESOLUTION)


if __name__ == "__main__":
    main()
