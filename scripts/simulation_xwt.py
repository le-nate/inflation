import numpy as np
import matplotlib.pyplot as plt

# import pycwt as wavelet
import pycwt as wavelet

from simulation_consumption import consumption


def main() -> None:
    """Run script"""
    sample_freq = 1000
    t = np.linspace(0, 2 * np.pi, sample_freq)
    dt = t[1] - t[0]
    dj = 1 / 12
    signal1 = consumption(
        t
    )  # np.sin(2 * np.pi * 5 * t) + np.random.lognormal(1, 0.1, 1000)

    signal2 = np.sin(2 * np.pi * 7 * t)  # + np.random.lognormal(1, 0.1, 1000)

    mother = wavelet.Morlet(6)  # Morlet wavelet with :math:`\omega_0=6`.

    xwt_result, coi, freqs, signif = wavelet.xwt(
        signal1, signal2, dt=dt, dj=dj, wavelet=mother
    )

    # * The frequencies generated by xwt are normalized, so multiply by sampling
    # * frequency to get the original frequencies
    ## (see https://stackoverflow.com/questions/75376628/have-difficulty-implementing-cwt-in-python-i-created-a-simple-example-for-the-s).
    denorm_freqs = freqs * sample_freq
    period = 1 / freqs
    power = (np.abs(xwt_result)) ** 2  ## Normalize wavelet power spectrum
    n = signal1.size
    sig95 = np.ones([1, n]) * signif[:, None]
    sig95 = power / sig95  ## Want where power / sig95 > 1
    coi_plot = np.concatenate(
        [np.log2(coi), [1e-9], np.log2(period[-1:]), np.log2(period[-1:]), [1e-9]]
    )

    # * Plot results
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Plot XWT
    extent = [min(t), max(t), min(coi_plot), max(period)]

    # Plot the time series data
    ax2.set_title("b) Time series")
    ax2.set_ylabel("Amplitude")
    ax2.plot(t, signal1, "-", linewidth=1)
    ax2.plot(t, signal2, "k", linewidth=1.5)

    # Normalized cwt power spectrum, signifance levels, and cone of influence
    # Period scale is logarithmic
    levels = [0.0625, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16]
    ax1.contourf(
        t,
        np.log2(period),
        np.log2(power),
        np.log2(levels),
        extend="both",
        cmap="jet",
        extent=extent,
    )
    ax1.contour(
        t, np.log2(period), sig95, [-99, 1], colors="k", linewidths=2, extent=extent
    )
    ax1.fill(
        np.concatenate([t, t[-1:] + dt, t[-1:] + dt, t[:1] - dt, t[:1] - dt]),
        coi_plot,
        "k",
        alpha=0.3,
        hatch="x",
    )
    ax1.set_title("a) {} Cross-Wavelet Power Spectrum ({})".format("", mother.name))
    ax1.set_ylabel("Period (years)")
    #
    Yticks = 2 ** np.arange(
        np.ceil(np.log2(period.min())), np.ceil(np.log2(period.max()))
    )
    ax1.set_yticks(np.log2(Yticks))
    ax1.set_yticklabels(Yticks)

    plt.show()


if __name__ == "__main__":
    main()
