import numpy as np
from hades.params import BICEP
a=BICEP()

from flipper import *

if __name__=='__main__':
	""" This is the iterator for batch processing the map creation through HTCondor. Each map is done separately, and argument is map_id."""
	import time
	start_time=time.time()
	import sys
	import pickle
	sys.path.append('/data/ohep2/')
	sys.path.append('/home/ohep2/Masters/')
	import os
	
	# First load good IDs:
	goodFile=a.root_dir+'%sdeg%sGoodIDs.npy' %(a.map_size,a.sep)
	#if not os.path.exists(goodFile):
	# load if not already created
	from hades.batch_maps import create_good_map_ids
	create_good_map_ids()
	print 'creating good IDs'
		
	goodIDs=np.load(goodFile)
	
	batch_id=int(sys.argv[1]) # batch_id number
	
	if batch_id>len(goodIDs)-1:
		print 'Process %s terminating' %batch_id
		sys.exit() # stop here
	
	map_id=goodIDs[batch_id] # this defines the tile used here
	
	print '%s starting for map_id %s' %(batch_id,map_id)
	
	# Now run the estimation
	from hades.wrapper import best_estimates
	output=best_estimates(map_id)
	
	# Save output to file
	outDir=a.root_dir+'BatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction)
	
	if not os.path.exists(outDir): # make directory
		os.makedirs(outDir)
		
	np.save(outDir+'%s.npy' %batch_id, output) # save output
	
	print "Job %s complete in %s seconds" %(batch_id,time.time()-start_time)
	
	if batch_id==len(goodIDs)-2:
		if a.send_email:
			from hades.NoiseParams import sendMail
			sendMail('Single Map')
	
	

def best_estimates(map_id,padding_ratio=a.padding_ratio,map_size=a.map_size,\
	sep=a.sep,N_sims=a.N_sims,noise_power=a.noise_power,FWHM=a.FWHM,\
	slope=a.slope,lMin=a.lMin,lMax=a.lMax,KKmethod=a.KKmethod,rot=a.rot,freq=a.freq,\
	delensing_fraction=a.delensing_fraction):
	""" Compute the estimated angle, amplitude and polarisation fraction with noise, using zero-padding.
	Noise model is from Hu & Okamoto 2002 and errors are estimated using MC simulations, which are all saved.
	
	Input: map_id (tile number)
	padding_ratio (ratio of real-space padded tile width to initial tile width)
	map_size (tile width in degrees)
	sep (separation of tile centres in degrees)
	N_sims (number of MC simulations)
	noise_power (noise power in microK-arcmin)
	FWHM (noise FWHM in arcmin)
	slope (fiducial slope of C_l isotropic dust dependance)
	lMin / lMax (range of ell values to apply the estimators over)
	KKmethod (Boolean, controlling which SNR to use (see KKtest.py))
	rot (angle to rotate by before applying estimators)
	freq (desired map frequency; 150 GHz for BICEP, 353 GHz for Vansyngel)
	delensing_fraction (efficiency of delensing; i.e. 0.1=90% removed)
	
	Output: First 6 values: [estimate,isotropic mean, isotropic stdev] for {A,Afs,Afc,fs,fc,str,ang}
	Final value: full data for N_sims as a sequence of 7 lists for each estimate (each of length N_sims)"""
	
	# First compute high-resolution B-mode map from padded-real space map with desired padding ratio
	from .PaddedPower import MakePaddedPower
	Bpow=MakePaddedPower(map_id,padding_ratio=padding_ratio,map_size=map_size,sep=sep,freq=freq)
	
	# Input directory:
	inDir=a.root_dir+'%sdeg%s/' %(map_size,sep)
	
	# Compute the (noise + lensing) power map using the B-mode map as a template
	# First compute the total noise (instrument+lensing)
	from .NoisePower import noise_model,lensed_Cl
	Cl_lens_func=lensed_Cl(delensing_fraction=delensing_fraction) # function for lensed Cl
	
	def total_Cl_noise(l):
		return Cl_lens_func(l)+noise_model(l,FWHM=FWHM,noise_power=noise_power)
	
	output=np.zeros([a.repeat,5])
	
	# Repeat to see variation due to noise addition
	for r in range(a.repeat):
		from .RandomField import fill_from_model
		noiselensedMap=Bpow.copy() # template
	
		noiselensedMap.powerMap=fill_from_model(Bpow,total_Cl_noise)
	
		#from .NoisePower import noise_map	
		#noiselensedMap=noise_map(powMap=Bpow.copy(),noise_power=noise_power,FWHM=FWHM,\
		#,delensing_fraction=delensing_fraction)
	
		# Compute total map
		totMap=Bpow.copy()
		totMap.powerMap=Bpow.powerMap+noiselensedMap.powerMap
		
		# Apply the KK estimators
		from .KKtest import zero_estimator
		output[r]=zero_estimator(totMap.copy(),map_id,lMin=lMin,\
			lMax=lMax,slope=slope,factor=None,FWHM=FWHM,noise_power=noise_power,\
			KKmethod=KKmethod,rot=rot,\
			delensing_fraction=delensing_fraction)
		# (Factor is expected monopole amplitude (to speed convergence))
		
		
	A_est,fs_est,fc_est,Afs_est,Afc_est=np.mean(output,axis=0)
	# Compute anisotropy fraction and angle
	ang_est=0.25*180./np.pi*(np.arctan(Afs_est/Afc_est)) # in degrees
	frac_est=np.sqrt(fs_est**2.+fc_est**2.) # already corrected for rotation
		
	## Run MC Simulations	
	
	# Compute rough semi-analytic C_ell spectrum
	def analytic_model(ell,A_est,slope):
		"""Use the estimate for A to construct analytic model.
		NB: This is just used for finding the centres of the actual binned data.
		"""
		return total_Cl_noise(ell)+A_est*ell**(-slope)
	
	# Compute 1D power spectrum by binning in annuli
	from .PowerMap import oneD_binning
	l_cen,mean_pow = oneD_binning(totMap.copy(),0.8*a.lMin,1.*a.lMax,0.8*a.l_step,binErr=False,exactCen=a.exactCen,C_ell_model=analytic_model,params=[A_est,slope]) 
	
	# gives central binning l and mean power in annulus using window function corrections (from unpaddded map)
	
	# Compute univariate spline model fit to 1D power spectrum
	#from scipy.interpolate import UnivariateSpline
	#spline_fun = UnivariateSpline(np.log10(l_cen),np.log10(mean_pow),k=4) # compute spline of log data
	
	#def model_power(ell):
	#	return 10.**spline_fun(np.log10(ell)) # this estimates 1D spectrum for any ell
	
	# Initialise arrays
	A_MC,fs_MC,fc_MC,Afs_MC,Afc_MC,epsilon_MC,ang_MC=[],[],[],[],[],[],[]
	
	#from hades.NoisePower import single_MC
	from .RandomField import fill_from_Cell
	MC_map=Bpow.copy()
	
	for n in range(N_sims): # for each MC map
		if n%10==0:
			print('MapID %s: Starting simulation %s of %s' %(map_id,n+1,N_sims))
		MC_map.powerMap=fill_from_Cell(totMap,l_cen,mean_pow)
		#MC_map=single_MC(totMap.copy(),model_power) # create random map from isotropic spectrum
		output=zero_estimator(MC_map.copy(),map_id,lMin=lMin,lMax=lMax,\
			slope=slope,factor=A_est,FWHM=FWHM,noise_power=noise_power,\
			KKmethod=KKmethod,rot=rot,\
			delensing_fraction=delensing_fraction) 
		# compute MC anisotropy parameters  
		A_MC.append(output[0])
		fs_MC.append(output[1])
		fc_MC.append(output[2])
		Afs_MC.append(output[3])
		Afc_MC.append(output[4])
		epsilon_MC.append(np.sqrt(output[1]**2.+output[2]**2.))
		ang_MC.append(0.25*180./np.pi*np.arctan(output[3]/output[4]))
		
	allMC=[A_MC,fs_MC,fc_MC,Afs_MC,Afc_MC,epsilon_MC,ang_MC]
	
	# Compute means and standard deviations
	A_mean=np.mean(A_MC)
	A_std=np.std(A_MC)
	fc_mean=np.mean(fc_MC)
	fs_mean=np.mean(fs_MC)
	fc_std=np.std(fc_MC)
	fs_std=np.std(fs_MC)
	frac_mean=np.mean(epsilon_MC)
	frac_std=np.std(epsilon_MC)
	ang_mean=np.mean(ang_MC)
	ang_std=np.std(ang_MC)
	Afs_mean=np.mean(Afs_MC)
	Afc_mean=np.mean(Afc_MC)
	Afs_std=np.std(Afs_MC)
	Afc_std=np.std(Afc_MC)
	
	# Regroup data
	Adat=[A_est,A_mean,A_std]
	fsdat=[fs_est,fs_mean,fs_std]
	fcdat=[fc_est,fc_mean,fc_std]
	Afsdat=[Afs_est,Afs_mean,Afs_std]
	Afcdat=[Afc_est,Afc_mean,Afc_std]
	fracdat=[frac_est,frac_mean,frac_std]
	angdat=[ang_est,ang_mean,ang_std]
	
	# Return all output
	return Adat,fsdat,fcdat,Afsdat,Afcdat,fracdat,angdat,allMC
	
def stats_and_plots(map_size=a.map_size,sep=a.sep,FWHM=a.FWHM,noise_power=a.noise_power,\
	freq=a.freq,delensing_fraction=a.delensing_fraction,makePlots=False):
	""" Function to create plots for each tile.
	MakePlots command creates plots of epsilon histogram in the Maps/HistPlots/ directory.
	Other plots are saved in the Maps/ directory """
	import warnings # catch rogue depracation warnings
	warnings.filterwarnings("ignore", category=DeprecationWarning) 
	
	import matplotlib.pyplot as plt
	from scipy.stats import percentileofscore
	import os
	
	# Import good map IDs
	goodMaps=np.load(a.root_dir+'%sdeg%sGoodIDs.npy' %(map_size,sep))
	
	# Define arrays
	A,Afs,Afc,fs,fc,ang,frac,probA,probP,logA=[np.zeros(len(goodMaps)) for _ in range(10)]
	A_err,Af_err,f_err,ang_err,frac_err,frac_mean=[np.zeros(len(goodMaps)) for _ in range(6)]
	
	# Define output directories:
	outDir=a.root_dir+'Maps/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction)
	histDir=a.root_dir+'Maps/HistPlots/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction)
	
	if not os.path.exists(histDir):
		os.makedirs(histDir)
	if not os.path.exists(outDir):
		os.makedirs(outDir)
	
	
	# Iterate over maps:
	for i in range(len(goodMaps)):
		map_id=goodMaps[i] # map id number
		
		# Load in data from tile
		data=np.load(a.root_dir+'BatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/%s.npy' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction,i))
		
		# Load in data
		A[i],fs[i],fc[i],Afs[i],Afc[i],frac[i],ang[i]=[d[0] for d in data[:7]]
		logA[i]=np.log10(A[i])
		A_err[i],fs_err,fc_err,Afs_err,Afc_err,frac_err[i]=[d[2] for d in data[:6]]
		frac_mean[i]=data[5][1]
		
		# Compute other errors
		f_err[i]=np.mean([fs_err,fc_err])
		Af_err[i]=np.mean([Afs_err,Afc_err])
		ang_err[i]=f_err[i]/(4*frac[i])*180./np.pi
		
		# Creat epsilon plot
		eps=data[7][5] # all epsilon data
		eps_est=data[5][0]
		
		percentile=percentileofscore(eps,eps_est,kind='mean') # compute percentile of estimated data
		probP[i]=percentile
		sigma_f=np.mean([data[1][2],data[2][2]]) # mean of fs,fc errors
		def eps_CDF(eps):	
			""" CDF of epsilon modified chi-squared distribution)"""
			return 1-np.exp(-eps**2./(2.*sigma_f**2.))
		def eps_PDF(eps):
			""" PDF of epsilon modified chi-squared distribution"""
			return eps/(sigma_f**2.)*np.exp(-eps**2./(2.*sigma_f**2.)) 
		# Compute analytic CDF percentile:
		probA[i]=100.*eps_CDF(eps_est)
		if makePlots:
			if i%10==0:
				print 'Creating plot %s of %s' %(i+1,len(goodMaps))
			y,x,_=plt.hist(eps,bins=30,range=[0,1],normed=True,alpha=0.5) # create histogram of random values
			ydat=np.linspace(0,max(y)*2,100)
			xdat=np.ones_like(ydat)*eps_est
			plt.plot(xdat,ydat,c='r',ls='--') # plot estimated value
			plt.ylabel('Epsilon PDF')
			plt.xlabel('Epsilon')
			plt.xlim(0,1)
			epsdat=np.linspace(0,1,100)
			plt.plot(epsdat,eps_PDF(epsdat),c='k') # predicted PDF
			plt.title('Tile %s // Percentile: %.2f // Analytic Percentile: %.2f' %(map_id,probP[i],probA[i]))
			plt.ylim(0,max(eps_PDF(epsdat)))
			# now save output
			plt.savefig(histDir+'%s.png' %map_id,bbox_inches='tight')
			plt.clf()
			plt.close()
	
	## Now compute the whole patch maps
	
	# Dataset:
	dat_set=[A,fs,fc,Afs,Afc,frac,ang,A_err,Af_err,f_err,frac_mean,frac_err,ang_err,probA,probP,logA]
	names=[r'Monopole amplitude',r'$f_s$',r'$f_c$',r'$Af_s$',r'$Af_c$',r'Anisotropy Fraction, $\epsilon$',r'Anisotropy Angle, $\alpha$',r'MC error for $A$',r'MC error for $Af$',r'MC error for $f$',r'MC mean anisotropy fraction',r'MC error for anisotropy fraction',r'MC error for angle',r'Epsilon Isotropic Percentile, $\rho$, (Analytic)',r'Epsilon Isotropic Percentile, $\rho$, (Statistical)',r'$\log_{10}(A)$']
	file_str=['A','fs','fc','Afs','Afc','epsilon','angle','A_err','Af_err','f_err',\
	'epsilon_MC_mean','epsilon_err','ang_err','prob_analyt','prob_stat','logA']
	
	# Load coordinates of map centres
	from .NoisePower import good_coords
	ra,dec=good_coords(map_size,sep,len(goodMaps))
	
	# Load in border of BICEP region if necessary:
	border=False
	if a.root_dir=='/data/ohep2/WidePatch/' or a.root_dir=='/data/ohep2/CleanWidePatch/':
		border=True # for convenience
		from hades.plotTools import BICEP_border
		temp=BICEP_border(map_size,sep)
		if temp!=None:
			edge_ra,edge_dec=temp
			# to only use cases where border is available
		else:
			border=False
	if border!=False:
		border_coords=[edge_ra,edge_dec]
	else:
		border_coords=None # for compatibility
	
	# Now plot on grid:
	import cmocean # for angle colorbar
	for j in range(len(names)):
		print 'Generating patch map %s of %s' %(j+1,len(names))
		cmap='jet'
		minMax=None
		if file_str[j]=='angle':
			cmap=cmocean.cm.phase
		if file_str[j]=='epsilon':
			vmin=min(dat_set[j])
			vmax=min([1.,np.percentile(dat_set[j],95)])
			minMax=[vmin,vmax]
		from hades.plotTools import skyMap
		# Create plot
		skyMap(dat_set[j],ra,dec,cbar_label=names[j],cmap=cmap,minMax=minMax,\
			border=border_coords,outFile=outDir+file_str[j]+'.png')
		if False: # old plotting regime depracated
			plt.figure()
			if file_str[j]=='angle':
				plt.scatter(ra,dec,c=dat_set[j],marker='o',\
				s=80,cmap=cmocean.cm.phase)
			else:
				plt.scatter(ra,dec,c=dat_set[j],marker='o',s=80)
			if border:
				plt.plot(edge_ra,edge_dec,c='k') # plot border
			plt.title(names[j])
			plt.colorbar()
			plt.savefig(outDir+file_str[j]+'.png',bbox_inches='tight')
			plt.clf()
			plt.close()
			
def patch_anisotropy(map_size=a.map_size,sep=a.sep,FWHM=a.FWHM,noise_power=a.noise_power,
	freq=a.freq,delensing_fraction=a.delensing_fraction,N_sims=a.N_sims):
	"""Compute the global anisotropy over the patch, summing the epsilon values weighted by the S/N.
	The estimate is assumed Gaussian by Central Limit Theorem.
	Errors are obtained by computing estimate for many MC sims
	"""
	# Load array of map ids
	goodMaps=np.load(a.root_dir+'%sdeg%sGoodIDs.npy' %(map_size,sep))
	
	# Initialize variables
	epsilon_patch_num=0.
	norm=0. # normalisation
	epsilon_patch_MC_num=np.zeros(N_sims)
	
	for i in range(len(goodMaps)):
		# Load dataset
		datPath=a.root_dir+'BatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/%s.npy' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction,i)
		data=np.load(datPath)		
		eps_est=data[5][0]
		eps_MC=data[7][5]
		sigma_eps=data[5][2]
		
		# Compute contribution to mean epsilon
		SNR=1./(sigma_eps**2.)
		epsilon_patch_num+=SNR*eps_est
		norm+=SNR
		for j in range(N_sims):
			epsilon_patch_MC_num[j]+=SNR*eps_MC[j]
			
	# Compute mean epsilon + MC values
	epsilon_patch=epsilon_patch_num/norm
	epsilon_patch_MC=epsilon_patch_MC_num/norm
	
	# Compute mean and standard deviation
	MC_mean=np.mean(epsilon_patch_MC)
	MC_std=np.std(epsilon_patch_MC)
	
	# Compute significance of detection
	sigmas=(epsilon_patch-MC_mean)/MC_std
	
	# Now plot
	import matplotlib.pyplot as plt
	y,x,_=plt.hist(epsilon_patch_MC,bins=20,normed=True)
	plt.ylabel('PDF')
	plt.xlabel('Patch Averaged Epsilon')
	plt.title('%.2f Sigma // BICEP Averaged Epsilon// %s patches & %s sims' %(sigmas,len(goodMaps),N_sims))
	xpl=np.ones(100)*epsilon_patch
	ypl=np.linspace(0,max(y),100)
	plt.plot(xpl,ypl,ls='--',c='r')
	plt.ylim(0,max(y))
	outDir=a.root_dir+'PatchEpsilon/'
	import os
	if not os.path.exists(outDir):
		os.makedirs(outDir)
	plt.savefig(outDir+'hist_f%s_ms%s_s%s_fw%s_np%s_d%s.png' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction),bbox_inches='tight')
	plt.clf()
	plt.close()
		
def map_plot(data,map_size=a.map_size,sep=a.sep):
	""" Simple wrapper to plot a patch map for input data array"""
	# Load array of map ids
	goodMaps=np.load(a.root_dir+'%sdeg%sGoodIDs.npy' %(map_size,sep))

	# Load coordinates of map centres
	from .NoisePower import good_coords
	ra,dec=good_coords(map_size,sep,len(goodMaps))
	
	# Now plot
	import matplotlib.pyplot as plt
	plt.figure()
	plt.scatter(ra,dec,c=data,marker='o',s=80)
	plt.colorbar()
	plt.show()
	