import numpy as np
from .params import BICEP
a=BICEP()

def fill_from_Cell(powerMap,ell,Cell,lMin=a.lMin):
	""" Function to fill a power map with a Gaussian random field implementation of an input Cell_BB spectrum.
	
	This is adapted from flipper.LiteMap.FillWithGaussianRandomField
	Input: realMap (for template)
	powerMap (for output)
	ell - rnage of ell for Cell
	Cell - spectrum (NB: not normalised to l(l+1)C_ell/2pi)
	
	Output: PowerMap with GRF
	"""
	from fftTools import fftFromLiteMap
	
	# Map templates
	pow_out=powerMap.copy()
	
	#ft=fftFromLiteMap(real_temp) # for fft frequencies
	Ny=pow_out.Ny
	Nx=pow_out.Nx
	
	#from scipy.interpolate import splrep,splev # for fitting
	
	realPart=np.zeros([Ny,Nx])
	imgPart=np.zeros([Ny,Nx])
	
	# Compute fourier freq. and mod L map
	ly=pow_out.ly#np.fft.fftfreq(Ny,d=real_temp.pixScaleY)*2.*np.pi
	lx=pow_out.lx#np.fft.fftfreq(Nx,d=real_temp.pixScaleX)*2.*np.pi
	
	modLMap=np.zeros([Ny,Nx])
	iy,ix=np.mgrid[0:Ny,0:Nx]
	modLMap[iy,ix]=np.sqrt(ly[iy]**2.+lx[ix]**2.)
	
	# Fit input Cell to spline
	from scipy.interpolate import UnivariateSpline
	spl=UnivariateSpline(ell,np.log10(Cell))
	ll=np.ravel(modLMap)
	
	kk=10.**spl(ll)
	
	# Apply filtering
	idhi=np.where(ll>max(ell))
	idlo=np.where(ll<lMin)
	idgood=np.where((ll<max(ell))&(ll>lMin))
	kk[idhi]=min(kk[idgood]) # set unwanted values to small value
	kk[idlo]=min(kk[idgood])
	
	area = Nx*Ny*pow_out.pixScaleX*pow_out.pixScaleY # map area
	p = np.reshape(kk,[Ny,Nx])/ area * (Nx*Ny)**2.
	
	# Compute real + imag parts
	realPart = np.sqrt(p)*np.random.randn(Ny,Nx)*np.sqrt(0.5)
	imgPart = np.sqrt(p)*np.random.randn(Ny,Nx)*np.sqrt(0.5)
	# NB: 0.5 factor needed to get correct output Cell
	
	# Compute power
	pMap=(realPart**2.+imgPart**2.)*area/(Nx*Ny)**2.
	
	return pMap

def fill_from_model(powerMap,model,lMin=0.9*a.lMin,lMax=1.1*a.lMax):
	""" Function to fill a power map with a Gaussian random field implementation of an input Cell_BB spectrum.
	
	This is adapted from flipper.LiteMap.FillWithGaussianRandomField
	Input: realMap (for template)
	powerMap (for output)
	model - C_l model function for input ell
	lMin/lMax - Range of ell to fill pixels (must be inside Cell_lens limits)
	
	Output: PowerMap with GRF from model
	"""
	from fftTools import fftFromLiteMap
	
	# Map templates
	pow_out=powerMap.copy()
	
	Ny=pow_out.Ny
	Nx=pow_out.Nx
	
	realPart=np.zeros([Ny,Nx])
	imgPart=np.zeros([Ny,Nx])
	
	# Compute fourier freq. and mod L map
	ly=pow_out.ly#np.fft.fftfreq(Ny,d=pow_out.pixScaleY)*2.*np.pi
	lx=pow_out.lx#np.fft.fftfreq(Nx,d=pow_out.pixScaleX)*2.*np.pi
	
	modLMap=np.zeros([Ny,Nx])
	iy,ix=np.mgrid[0:Ny,0:Nx]
	modLMap[iy,ix]=np.sqrt(ly[iy]**2.+lx[ix]**2.)
	
	ll=np.ravel(modLMap)
	kk=np.zeros_like(ll)
	
	# Only fill for correct pixels
	id_low=np.where(ll<lMin)
	id_hi=np.where(ll>lMax)
	id_good=np.where((ll>lMin)&(ll<lMax))
	
	kk[id_good]=model(ll[id_good]) # add model value
	kk[id_low]=min(kk[id_good]) # unneeded pixels
	kk[id_hi]=min(kk[id_good]) # (filled to allow for log-plotting)
	
	area = Nx*Ny*pow_out.pixScaleX*pow_out.pixScaleY # map area
	p = np.reshape(kk,[Ny,Nx])/ area * (Nx*Ny)**2.
	
	# Compute real + imag parts
	realPart = np.sqrt(p)*np.random.randn(Ny,Nx)*np.sqrt(0.5)
	imgPart = np.sqrt(p)*np.random.randn(Ny,Nx)*np.sqrt(0.5)
	# NB: 0.5 factor needed to get correct output Cell
	
	# Compute power
	pMap=(realPart**2.+imgPart**2.)*area/(Nx*Ny)**2.
	
	return pMap
	