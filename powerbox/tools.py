"""
A set of tools for dealing with structured boxes, such as those output by :mod:`powerbox`. Tools include those
for averaging a field isotropically, and generating the isotropic power spectrum.
"""
from . import dft
import numpy as np

def angular_average(field,coords,bins, weights = 1, average=True):
    r"""
    Perform a radial histogram -- averaging within radial bins -- of a field.

    Parameters
    ----------
    field : array
        An array of arbitrary dimension specifying the field to be angularly averaged.

    coords : array
        The magnitude of the co-ordinates at each point of `field`. Must be the same size as field.

    bins : float or array.
        The ``bins`` argument provided to histogram. Can be an int or array specifying bin edges.

    weights : array, optional
        An array of the same shape as `field`, giving a weight for each entry.
        
    average : bool, optional
        Whether to take the (weighted) average. If False, returns the (unweighted) sum.
    Returns
    -------
    field_1d : array
        The field averaged angularly (finally 1D)

    binavg : array
        The mean co-ordinate in each radial bin.

    Examples
    --------
    Create a 3D radial function, and average over radial bins:

    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> x = np.linspace(-5,5,128)   # Setup a grid
    >>> X,Y,Z = np.meshgrid(x,x,x)  # ""
    >>> r = np.sqrt(X**2+Y**2+Z**2) # Get the radial co-ordinate of grid
    >>> field = np.exp(-r**2)       # Generate a radial field
    >>> avgfunc, bins = angular_average(field,r,bins=100)   # Call angular_average
    >>> plt.plot(bins, np.exp(-bins**2), label="Input Function")   # Plot input function versus ang. avg.
    >>> plt.plot(bins, avgfunc, label="Averaged Function")
    """
    if not np.iterable(bins):
        bins = np.linspace(coords.min(), coords.max() * 1.001, bins + 1)

    indx, binav, sumweight = _get_binweights(coords, weights, bins, average)

    if len(np.unique(indx)) != len(bins) - 1:
        print("NOT ALL BINS FILLED: ", len(np.unique(indx)), len(bins) - 1, len(sumweight))

    binav = np.bincount(indx, weights=(weights*coords).flatten())/sumweight
    res = _field_average(indx,field, weights, sumweight)

    return res, binav

def _magnitude_grid(x,dim=None):
    if dim is not None:
        return np.sqrt(np.sum(np.meshgrid(*([x ** 2]*dim)), axis=0))
    else:
        return np.sqrt(np.sum(np.meshgrid(*([x**2 for x in x])), axis=0))


def _get_binweights(coords, weights, bins, average=True):
    # Minus 1 to have first index at 0
    indx = np.digitize(coords.flatten(), bins) - 1

    if average:
        if not np.isscalar(weights):
            sumweights = np.bincount(indx, weights=weights.flatten())
        else:
            sumweights = np.bincount(indx)

        binweight = sumweights
    else:
        sumweights = 1

        if not np.isscalar(weights):
            binweight = np.bincount(indx, weights=weights.flatten())
        else:
            binweight = np.bincount(indx)

    binav = np.bincount(indx, weights=(weights*coords).flatten())/binweight

    return indx, binav, sumweights

def _field_average(indx, field,weights, sumweights):

    field = field*weights #Leave like this because field is mutable
    rl = np.bincount(indx, weights=np.real(field.flatten()))/sumweights
    if field.dtype.kind == "c":
        im = 1j*np.bincount(indx, weights=np.imag(field.flatten()))/sumweights
    else:
        im = 0

    return rl + im

def angular_average_nd(field, coords, bins, n=None, weights=1, average=True):
    """
    Take an ND box, and perform a radial average over the first n dimensions.

    Parameters
    ----------
    field : array
        An array of arbitrary dimension specifying the field to be angularly averaged.

    coords : list of arrays
        A list with length equal to the number of dimensions of `field`. Each entry should be an
        array specifying the co-ordinates in the corresponding dimension of `field`. Note this 
        is different from :func:`angular_average`.

    bins : float or array.
        Specifies the bins for the averaged dimensions. Can be an int or array specifying bin edges.

    n : int, optional
        The number of dimensions to be averaged. By default, all dimensions are averaged. Always uses
        the first `n` dimensions.
        
    weights : array, optional
        An array of the same shape as the first n dimensions of `field`, giving a weight for each entry.
        
    average : bool, optional
        Whether to take the (weighted) average. If False, returns the (unweighted) sum.
    Returns
    -------
    field_1d : array
        The field averaged angularly (finally 1D)

    binavg : array
        The mean co-ordinate in each radial bin.
        
    coords : list of arrays
        A list of co-ordinates of non-averaged dimensions.

    linear_bins : array
        The linearly-space radial bin edges.

    Examples
    --------
    Create a 3D radial function, and average over radial bins. Equivalent to calling :func:`angular_average`:

    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> x = np.linspace(-5,5,128)   # Setup a grid
    >>> X,Y,Z = np.meshgrid(x,x,x)  # ""
    >>> r = np.sqrt(X**2+Y**2+Z**2) # Get the radial co-ordinate of grid
    >>> field = np.exp(-r**2)       # Generate a radial field
    >>> avgfunc, bins, _ = angular_average_nd(field,[x,x,x],bins=100)   # Call angular_average
    >>> plt.plot(bins, np.exp(-bins**2), label="Input Function")   # Plot input function versus ang. avg.
    >>> plt.plot(bins, avgfunc, label="Averaged Function")

    Create a 2D radial function, extended to 3D, and average over first 2 dimensions:
    
    >>> r = np.sqrt(X**2+Y**2)
    >>> field = np.exp(-r**2)    # 2D field
    >>> field = np.repeat(field,len(x)).reshape((len(x),)*3)   # Extended to 3D
    >>> avgfunc, avbins, coords = angular_average_nd(field, [x,x,x], bins=50, n=2)
    >>> plt.plot(avbins, np.exp(-avbins**2), label="Input Function")
    >>> plt.plot(avbins, avgfunc[:,0], label="Averaged Function")
    """
    if n is None:
        n = len(coords)

    if len(coords) != len(field.shape):
        raise ValueError("coords should be a list of arrays, one for each dimension.")

    av_coords = _magnitude_grid([c for i, c in enumerate(coords) if i < n])

    if not np.iterable(bins):
        bins = np.linspace(av_coords.min(), av_coords.max() *1.001, bins + 1)

    if n == len(coords):
        av, binav = angular_average(field, av_coords, bins, weights, average)
        return av,binav, []

    indx, binav, sumweights = _get_binweights(av_coords, weights, bins, average)

    n1 = np.product(field.shape[:n])
    n2 = np.product(field.shape[n:])

    res = np.zeros((len(binav), n2),dtype=field.dtype)
    for i, fld in enumerate(field.reshape((n1, n2)).T):
        try:
            w = weights.flatten()
        except AttributeError:
            w = weights

        res[:,i] = _field_average(indx, fld, w, sumweights)

    return res.reshape((len(binav),) + field.shape[n:]), binav, coords[n:], bins


def get_power(deltax,boxlength,deltax2=None,N=None, a=1.,b=1., remove_shotnoise=True,
              vol_normalised_power=True, bins=None, res_ndim=None, weights=None, weights2=None,
              dimensionless=True):
    r"""
    Calculate the isotropic power spectrum of a given field.

    Parameters
    ----------
    deltax : array-like
        The field to calculate the power spectrum of. Can either be arbitrarily n-dimensional, or 2-dimensional with the 
        first being the number of spatial dimensions, and the second the positions of discrete particles in the field. 
        The former should represent a density field, while the latter
        is a discrete sampling of a field. This function chooses which to use by checking the value of `N` (see below).
        Note that if a discrete sampling is used, the power spectrum calculated is the
        "overdensity" power spectrum, i.e. the field re-centered about zero and rescaled by the mean.

    boxlength : float or list of floats
        The length of the box side(s) in real-space.

    deltax2 : array-like
        If given, a box of the same shape as deltax, against which deltax will be cross correlated.

    N : int, optional
        The number of grid cells per side in the box. Only required if deltax is a discrete sample. If given,
        the function will assume a discrete sample.

    a,b : float, optional
        These define the Fourier convention used. See :mod:`powerbox.dft` for details. The defaults define the standard
        usage in *cosmology* (for example, as defined in Cosmological Physics, Peacock, 1999, pg. 496.). Standard
        numerical usage (eg. numpy) is (a,b) = (0,2pi).

    remove_shotnoise : bool, optional
        Whether to subtract a shot-noise term after determining the isotropic power. This only affects discrete samples.

    vol_weighted_power : bool, optional
        Whether the input power spectrum, ``pk``, is volume-weighted. Default True because of standard cosmological
        usage.

    bins : int or array, optional
        Defines the final k-bins output. If None, chooses a number based on the input resolution of the box. Otherwise,
        if int, this defines the number of kbins, or if an array, it defines the exact bin edges.
        
    res_ndim : int, optional
        Only perform angular averaging over first `res_ndim` dimensions. By default, uses all dimensions. 

    weights, weights2 : array-like, optional
        If deltax is a discrete sample, these are weights for each point.

    dimensionless: bool, optional
        Whether to normalise the cube by its mean prior to taking the power.

    Returns
    -------
    p_k : array
        The power spectrum averaged over bins of equal ``|k|``.

    meank : array
        The bin-centres for the p_k array (in k). This is the mean k-value for cells in that bin.

    Examples
    --------
    One can use this function to check whether a box created with :class:`PowerBox` has the correct
    power spectrum:

    >>> from powerbox import PowerBox
    >>> import matplotlib.pyplot as plt
    >>> pb = PowerBox(250,lambda k : k**-2.)
    >>> p,k = get_power(pb.delta_x,pb.boxlength)
    >>> plt.plot(k,p)
    >>> plt.plot(k,k**-2.)
    >>> plt.xscale('log')
    >>> plt.yscale('log')
    """

    # Check if the input data is in sampled particle format
    if N is not None:


        if deltax.shape[1]>deltax.shape[0]:
            raise ValueError("It seems that there are more dimensions than particles! Try transposing deltax.")

        if deltax2 is not None and deltax2.shape[1]>deltax2.shape[0]:
            raise ValueError("It seems that there are more dimensions than particles! Try transposing deltax2.")

        dim = deltax.shape[1]
        if deltax2 is not None and dim != deltax2.shape[1]:
            raise ValueError("deltax and deltax2 must have the same number of dimensions!")


        if not np.iterable(N):
            N = [N]*dim

        if not np.iterable(boxlength):
            boxlength = [boxlength]*dim

        Npart1 = deltax.shape[0]

        if deltax2 is not None:
            Npart2 = deltax2.shape[0]
        else:
            Npart2 = Npart1

        # Generate a histogram of the data, with appropriate number of bins.
        edges = [np.linspace(0,L, n+1) for L,n in zip(boxlength,N)]

        deltax = np.histogramdd(deltax%boxlength, bins=edges, weights=weights)[0].astype("float")

        if deltax2 is not None:
            deltax2 = np.histogramdd(deltax2%boxlength,bins=edges, weights=weights2)[0].astype("float")


        # Convert sampled data to mean-zero data
        if dimensionless:
            deltax = deltax / np.mean(deltax) - 1
            if deltax2 is not None:
                deltax2 = deltax2 / np.mean(deltax2) - 1
        else:
            deltax -= np.mean(deltax)
            if deltax2 is not None:
                deltax2 -= np.mean(deltax2)
    else:
        # If input data is already a density field, just get the dimensions.
        dim = len(deltax.shape)

        if not np.iterable(boxlength):
            boxlength = [boxlength]*dim

        if deltax2 is not None and deltax.shape != len(deltax2.shape):
            raise ValueError("deltax and deltax2 must have the same shape!")

        N = deltax.shape
        Npart1 = None




    V = np.product(boxlength)

    # Calculate the n-D power spectrum and align it with the k from powerbox.
    FT, freq, k = dft.fft(deltax, L=boxlength, a=a, b=b, ret_cubegrid=True)

    if deltax2 is not None:
        FT2 = dft.fft(deltax2, L=boxlength, a=a, b=b)[0]
    else:
        FT2 = FT


    P = np.real(FT*np.conj(FT2)/V**2)


    if vol_normalised_power:
        P *= V

    if res_ndim is None:
        res_ndim = dim

    # Generate the bin edges
    if bins is None:
        bins = int(np.product(N[:res_ndim])**(1./res_ndim)/2.2)

    p_k, k_av_bins, other_k = angular_average_nd(P, freq, bins, n=res_ndim)

    # Remove shot-noise
    if remove_shotnoise and Npart1:
        p_k -= np.sqrt( V**2 / Npart1/Npart2)

    if res_ndim == dim:
        return p_k, k_av_bins
    else:
        return p_k, k_av_bins, other_k