import numpy as np
from hades.params import BICEP
a=BICEP()

from flipper import *

def padded_estimates(map_id,padding_ratio=a.padding_ratio,map_size=a.map_size,\
	sep=a.sep,N_sims=a.N_sims,noise_power=a.noise_power,FWHM=a.FWHM,slope=a.slope):
	""" Compute the estimated angle, amplitude and polarisation fraction with noise, using zero-padding.
	Noise model is from Hu & Okamoto 2002 and errors are estimated using MC simulations.
	
	Input: map_id (tile number)
	padding_ratio (ratio of real-space padded tile width to initial tile width)
	map_size (tile width in degrees)
	sep (separation of tile centres in degrees)
	N_sims (number of MC simulations)
	noise_power (noise power in microK-arcmin)
	FWHM (noise FWHM in arcmin)
	slope (fiducial slope of C_l isotropic dust dependance)
	
	Output: Estimated data for A, fs, fc and errors."""
	
	# First compute padded B-mode map with desired padding ratio
	from .PaddedPower import MakePaddedPower
	Bpow=MakePaddedPower(map_id,padding_ratio=padding_ratio,map_size=map_size,sep=sep)


def est_and_err(map_id,map_size=a.map_size,sep=a.sep,N_sims=a.N_sims,noise_power=a.noise_power,FWHM=a.FWHM,slope=a.slope):
	""" Compute the estimated angle, amplitude and polarisation strength in the presence of noise, following Hu & Okamoto 2002 noise model. Error is from MC simulations.
	Output: list of data for A, fs, fc (i.e. output[0]-> A etc.), with structure [map estimate, MC_standard_deviation, MC_mean]
	"""
	# First calculate the B-mode map (noiseless)
	from .PowerMap import MakePower
	Bpow=MakePower(map_id,map_size=map_size,map_type='B')
	
	# Load the relevant window function
	inDir=a.root_dir+'%sdeg%s/' %(map_size,sep)
	mask=liteMap.liteMapFromFits(inDir+'fvsmapMaskSmoothed_'+str(map_id).zfill(5)+'.fits')
	
	# Compute mean square window function
	windowFactor=np.mean(mask.data**2.)
	
	# Now compute the noise power-map
	from .NoisePower import noise_map
	noiseMap=noise_map(powMap=Bpow.copy(),noise_power=a.noise_power,FWHM=a.FWHM,windowFactor=windowFactor)
	
	# Compute total map
	totMap=Bpow.copy()
	totMap.powerMap=Bpow.powerMap+noiseMap.powerMap
	
	# Initially using NOISELESS estimators
	from .KKtest import noisy_estimator
	est_data=noisy_estimator(totMap.copy(),slope=slope) # compute anisotropy parameters
		
	## Run MC Simulations	
	# First compute 1D power spectrum by binning in annuli
	from hades.PowerMap import oneD_binning
	l_cen,mean_pow = oneD_binning(totMap.copy(),0.8*a.lMin,1.*a.lMax,0.8*a.l_step,binErr=False,windowFactor=windowFactor) # gives central binning l and mean power in annulus using window function corrections
	
	# Compute univariate spline model fit to 1D power spectrum
	from scipy.interpolate import UnivariateSpline
	spline_fun = UnivariateSpline(np.log10(l_cen),np.log10(mean_pow),k=4) # compute spline of log data
	
	def model_power(ell):
		return 10.**spline_fun(np.log10(ell)) # this estimates 1D spectrum for any ell
	
	if False: # testing
		import matplotlib.pyplot as plt
		plt.plot(l_cen,np.log10(mean_pow))
		plt.plot(l_cen,np.log10(model_power(l_cen)))
		plt.show()
	
	# Now run MC simulation N_sims times
	MC_data = np.zeros((N_sims,len(est_data)))
	
	for n in range(N_sims): # for each MC map
		MC_map=single_MC(totMap.copy(),model_power,windowFactor=windowFactor) # create random map from isotropic spectrum
		MC_data[n]=noisy_estimator(MC_map.copy(),slope=slope) # compute MC anisotropy parameters  
	
	# Compute mean and standard deviation of MC statistics
	MC_means=np.mean(MC_data,axis=0)
	MC_std=np.std(MC_data,axis=0)	

	# Regroup output (as described above)
	output = [[est_data[i],MC_std[i],MC_means[i]] for i in range(len(MC_means))]		
	
	return output
	

def MakePaddedPower(map_id,padding_ratio=a.padding_ratio,map_size=a.map_size,sep=a.sep):
    """ Function to create 2D B-mode power map from real space map padded with zeros.
    Input: map_id (tile number)
    map_size (in degrees)
    sep (separation of map centres)
    padding_ratio (ratio of padded map width to original (real-space) map width)
   
    Output: B-mode map in power-space   
    """
    import flipperPol as fp
    
    inDir=a.root_dir+'%sdeg%s/' %(map_size,a.sep)
    
    # Read in original maps from file
    Tmap=liteMap.liteMapFromFits(inDir+'fvsmapT_'+str(map_id).zfill(5)+'.fits')
    Qmap=liteMap.liteMapFromFits(inDir+'fvsmapQ_'+str(map_id).zfill(5)+'.fits')
    Umap=liteMap.liteMapFromFits(inDir+'fvsmapU_'+str(map_id).zfill(5)+'.fits')
    maskMap=liteMap.liteMapFromFits(inDir+'fvsmapMaskSmoothed_'+str(map_id).zfill(5)+'.fits')
    
    # Compute window factor <W^2> for UNPADDED window (since this is only region with data)
    windowFactor=np.mean(maskMap.data**2.)
    
    # Compute zero-padded maps (including mask map)
    from .PaddedPower import zero_padding
    zTmap=zero_padding(Tmap,padding_ratio)
    zQmap=zero_padding(Qmap,padding_ratio)
    zUmap=zero_padding(Umap,padding_ratio)
    zWindow=zero_padding(maskMap,padding_ratio)

    # Define mod(l) and ang(l) maps needed for fourier transforms
    modL,angL=fp.fftPol.makeEllandAngCoordinate(zTmap) # choice of map is arbitary

    # Create pure T,E,B maps using 'hybrid' method to minimize E->B leakage
    fT,fE,fB=fp.fftPol.TQUtoPureTEB(zTmap,zQmap,zUmap,zWindow,modL,angL,method='hybrid')

    # Transform into power space
    _,_,_,_,_,_,_,_,BB=fp.fftPol.fourierTEBtoPowerTEB(fT,fE,fB,fT,fE,fB)
    
    # Now account for power loss due to padding:
    BB.powerMap*=zTmap.powerFactor
    
    # Store window factor
    BB.windowFactor=windowFactor
    
    return BB
    
	

def zero_padding(tempMap,padding_factor):
	""" Pad the real-space map with zeros.
	Padding_factor is ratio of padded map width to original map width.
	NB: WCS data is NOT changed by the zero-padding, so will be inaccurate if used.
	(this doesn't affect any later processes)"""
	
	zeroMap=tempMap.copy() # padded map template
	oldNx=tempMap.Nx
	oldNy=tempMap.Ny # old Map dimensions
	
	# Apply padding
	paddingY=int(oldNy*(padding_factor-1.)/2.)
	paddingX=int(oldNx*(padding_factor-1.)/2.) # no. zeros to add to each edge of map
	zeroMap.data=np.lib.pad(tempMap.data,((paddingY,paddingY),(paddingX,paddingX)),'constant') # pads with zeros by default
	
	# Reconfigure other parameters
	zeroMap.Ny=len(zeroMap.data)
	zeroMap.Nx=len(zeroMap.data[0]) # map dimensions
	zeroMap.area*=(zeroMap.Ny/oldNy)*(zeroMap.Nx/oldNx) # rescale area
	zeroMap.x1-=oldNx*zeroMap.pixScaleX*180./np.pi # change width in degrees
	zeroMap.x0+=oldNx*zeroMap.pixScaleX*180./np.pi
	zeroMap.y0-=oldNy*zeroMap.pixScaleY*180./np.pi
	zeroMap.y1+=oldNy*zeroMap.pixScaleY*180./np.pi # signs to fit with flipper conventions
	
	# Define 'power factor'
	# Power-space maps must be multiplied by this factor to have correct power
	zeroMap.powerFactor=zeroMap.area/tempMap.area
	
	return zeroMap

