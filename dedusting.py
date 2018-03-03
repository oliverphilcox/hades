from hades.params import BICEP
a=BICEP()
import numpy as np
from flipper import *
import flipperPol as fp

if __name__=='__main__':
	""" This is the iterator for batch processing the map creation through HTCondor. Each map is done separately, and argument is map_id."""
	import time
	start_time=time.time()
	import sys
	import pickle
	sys.path.append('/data/ohep2/')
	sys.path.append('/home/ohep2/Masters/')
	import os
	
	batch_id=int(sys.argv[1]) # batch_id number
	
	# First load good IDs:
	goodFile=a.root_dir+'%sdeg%sGoodIDs.npy' %(a.map_size,a.sep)
	
	outDir=a.root_dir+'DedustingI/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction)
	
	if a.remakeErrors:
		if os.path.exists(outDir+'%s.npy' %batch_id):
			print 'output exists; exiting'
			sys.exit()
	
	if batch_id<110: # create first time
		from hades.batch_maps import create_good_map_ids
		create_good_map_ids()
		print 'creating good IDs'
		
	goodIDs=np.load(goodFile)
	
	
	if batch_id>len(goodIDs)-1:
		print 'Process %s terminating' %batch_id
		sys.exit() # stop here
	
	map_id=goodIDs[batch_id] # this defines the tile used here
	
	print '%s starting for map_id %s' %(batch_id,map_id)

		
	from hades.dedusting import compute_angle
	output=compute_angle(map_id)
		
	# Save output to file
	if not os.path.exists(outDir): # make directory
		os.makedirs(outDir)
		
	np.save(outDir+'%s.npy' %batch_id, output) # save output
	
	print "Job %s complete in %s seconds" %(batch_id,time.time()-start_time)
	
	if batch_id==len(goodIDs)-2:
		if a.send_email:
			from hades.NoiseParams import sendMail
			sendMail('Angle Maps')




def compute_angle(map_id,padding_ratio=a.padding_ratio,map_size=a.map_size,sep=a.sep,freq=a.freq,\
                  f_dust=a.f_dust,lMax=a.lMax,lMin=a.lMin,l_step=a.l_step,FWHM=a.FWHM,noise_power=a.noise_power,\
                  slope=a.slope,delensing_fraction=a.delensing_fraction,useQU=a.useQU):
    """Compute the polarisation angle for a specific tile, creating a model B-power spectrum + cross-spectra
    in order to find the angle including the ambiguity in sin(2alpha), cos(2alpha) due to initial computation
    of sin(4alpha), cos(4alpha).
    
    Returns angle in degrees.
    """

    # Step 1, create actual B-mode map
    lCut=int(1.35*lMax) # maximum ell for Fourier space maps

    # First compute B-mode map from padded-real space map with desired padding ratio. Also compute the padded window function for later use
    from hades.PaddedPower import MakePowerAndFourierMaps,DegradeMap,DegradeFourier
    fBdust,padded_window,unpadded_window=MakePowerAndFourierMaps(map_id,padding_ratio=padding_ratio,map_size=map_size,sep=sep,freq=freq,fourier=True,power=False,returnMasks=True)

    # Also compute unpadded map to give binning values without bias
    unpadded_fBdust=MakePowerAndFourierMaps(map_id,padding_ratio=1.,map_size=map_size,freq=freq,fourier=True,power=False,returnMasks=False)
    unpadded_fBdust=DegradeFourier(unpadded_fBdust,lCut) # remove high ell pixels

    fBdust=DegradeFourier(fBdust,lCut) # discard high-ell pixels
    padded_window=DegradeMap(padded_window.copy(),lCut) # remove high-ell data
    unpadded_window=DegradeMap(unpadded_window.copy(),lCut)

    unpadded_fBdust.kMap*=f_dust
    fBdust.kMap*=f_dust

    wCorrection = np.mean(padded_window.data**2.)**2./np.mean(padded_window.data**4.)

    from hades.NoisePower import noise_model,lensed_Cl,r_Cl
    Cl_lens_func=lensed_Cl(delensing_fraction=delensing_fraction) # function for lensed Cl

    def total_Cl_noise(l):
        return Cl_lens_func(l)+noise_model(l,FWHM=FWHM,noise_power=noise_power)

    from hades.PaddedPower import fourier_noise_map
    ellNoise=np.arange(5,lCut) # ell range for noise spectrum

    from hades.RandomField import fill_from_model
    #fourierNoise=fourier_noise_map

    from hades.PaddedPower import fourier_noise_test
    fourierNoise,unpadded_noise=fourier_noise_test(padded_window,unpadded_window,ellNoise,total_Cl_noise(ellNoise),padding_ratio=padding_ratio,unpadded=False,log=True)

    totFmap=fBdust.copy()
    totFmap.kMap+=fourierNoise.kMap# for total B modes
    unpadded_totFmap=unpadded_fBdust.copy()
    unpadded_totFmap.kMap+=unpadded_noise.kMap

    fBtrue=totFmap.copy()

    # Step 2: Compute the I map
    inDir=a.root_dir+'%sdeg%s/' %(map_size,sep)
    Tmap=liteMap.liteMapFromFits(inDir+'fvsmapT_'+str(map_id).zfill(5)+'.fits')
    Qmap=liteMap.liteMapFromFits(inDir+'fvsmapQ_'+str(map_id).zfill(5)+'.fits')
    Umap=liteMap.liteMapFromFits(inDir+'fvsmapU_'+str(map_id).zfill(5)+'.fits')
    QUmap=Qmap.copy()
    QUmap.data=np.sqrt(Qmap.data**2.+Umap.data**2.)
    maskMap=liteMap.liteMapFromFits(inDir+'fvsmapMaskSmoothed_'+str(map_id).zfill(5)+'.fits')
    from hades.PaddedPower import zero_padding
    zTmap=zero_padding(Tmap,padding_ratio)
    zQUmap=zero_padding(QUmap,padding_ratio)
    zWindow=zero_padding(maskMap,padding_ratio)
    # Compute window factor <W^2> for padded window (since this is only region with data)
    windowFactor=np.mean(zWindow.data**2.)

    # Define mod(l) and ang(l) maps needed for fourier transforms
    modL,angL=fp.fftPol.makeEllandAngCoordinate(zTmap) # choice of map is arbitary
    # Create pure T,E,B maps using 'hybrid' method to minimize E->B leakage
    zTmap.data*=zWindow.data
    zQUmap.data*=zWindow.data
    fT=fftTools.fftFromLiteMap(zTmap)
    fQU=fftTools.fftFromLiteMap(zQUmap)

    # Rescale to correct amplitude using dust SED
    from hades.PowerMap import dust_emission_ratio
    dust_intensity_ratio=dust_emission_ratio(freq)

    fT.kMap*=dust_intensity_ratio # apply dust-reduction factor 
    fT.kMap/=np.sqrt(windowFactor)
    fQU.kMap*=dust_intensity_ratio
    fQU.kMap/=np.sqrt(windowFactor)
    fImap=DegradeFourier(fT,lCut)
    fQUmap=DegradeFourier(fQU,lCut)

    # Step 3: Compute angle estimate
    powBtrue=fftTools.powerFromFFT(fBtrue)
    from hades.KKdebiased import derotated_estimator
    output=derotated_estimator(powBtrue,map_id,lMin=lMin,lMax=lMax,FWHM=FWHM,noise_power=noise_power,delensing_fraction=delensing_fraction,slope=slope)
    A,Afs,Afc,fs,fc,_=output
    norm=np.sqrt(Afs**2.+Afc**2.)
    fsbar,fcbar=Afs/norm,Afc/norm

    sin2a=fsbar/np.sqrt(2.*(fcbar+1.))
    cos2a=np.sqrt((1.+fcbar)/2.)

    # Step 4: Compute B estimate
    angleMap=fImap.thetaMap*np.pi/180.
    fB_est=fImap.copy()
    if useQU:
    	baseMap=fQUmap.copy()
    else:
    	baseMap=fImap.copy()
    fB_est.kMap=baseMap.kMap*(sin2a*np.cos(2.*angleMap)-cos2a*np.sin(2.*angleMap))

    # Step 5: Now compute cross coefficient
    crossPow=fftTools.powerFromFFT(fB_est,fBtrue)
    estPow=fftTools.powerFromFFT(fB_est,fB_est)

    from hades.PowerMap import oneD_binning
    lC,pC=oneD_binning(crossPow,lMin,lMax/2.,l_step,exactCen=False)
    lE,pE=oneD_binning(estPow,lMin,lMax/2.,l_step,exactCen=False)
    lB,pB=oneD_binning(powBtrue,lMin,lMax/2.,l_step,exactCen=False)
    #rho=np.array(pC)/np.sqrt(np.array(pB)*np.array(pE))
    ratio=np.array(pC)/np.array(pE)
    sign=np.sign(np.mean(ratio))

    # Step 6: Now compute the actual angle
    alpha0=0.25*np.arctan2(fsbar,fcbar) # range is [-pi/4,pi/4]
    if sign==-1.0:
        alpha0+=np.pi/2.
       
    alpha_deg=alpha0*180./np.pi
    print 'MapID: %s Angle: %.2f' %(map_id,alpha_deg)
    return alpha_deg