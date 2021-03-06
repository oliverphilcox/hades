from hades.params import BICEP
import warnings # catch rogue depracation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 	
import numpy as np
import matplotlib
import matplotlib.pylab as pyl
a=BICEP()

def BICEP_border(map_size,sep):
    """ Compute RA/dec coordinates of edge of BICEP region.
    Output is RA,dec in degrees. 
     """
    import pickle
    
    map_dir='BICEP2/'+'%sdeg%s/' %(map_size,sep)
    import os
    if not os.path.exists(map_dir+'fvsmapRas.pkl'):
    	print 'no border'
    	return None
    
    full_ras=pickle.load(open(map_dir+'fvsmapRas.pkl','rb'))
    full_decs=pickle.load(open(map_dir+'fvsmapDecs.pkl','rb'))
    goodMap=pickle.load(open(map_dir+'fvsgoodMap.pkl','rb'))
    ra=[full_ras[i] for i in range(len(full_ras)) if goodMap[i]!=False]
    dec=[full_decs[i] for i in range(len(full_decs)) if goodMap[i]!=False]
    for i in range(len(ra)):
        if ra[i]>180.:
            ra[i]-=360.
    
    DECs=np.unique(dec)
    N=2*len(DECs)
    edge_ra,edge_dec=[np.zeros(N+1) for _ in range(2)]
    for j,D in enumerate(DECs):
        RAs=[ra[i] for i in range(len(ra)) if dec[i]==D]
        edge_ra[j]=min(RAs)
        edge_ra[N-1-j]=max(RAs)
        edge_dec[j]=D
        edge_dec[N-1-j]=D
    edge_ra[N]=edge_ra[0]
    edge_dec[N]=edge_dec[0]
    
    return edge_ra,edge_dec
    
def skyMap(dat,ra,dec,cbar_label=None,cmap='jet',decLims=[-90,-40,5],raLims=[-180,30,10],minMax=None,border=None,outFile=None,show=False,sym_log=False):
    """Plot in Albers Equal Area Projection conic grid using the skymapper package.
    Inputs:
    data -> values to plot
    ra,dec -> coordinates
    cbar_label -> label for colorbar
    cmap -> colormap (e.g. 'jet)
    minMax -> [min,max] for colorbar
    decLims/raLims -> give min/max/step for RA and dec lines
    border -> [ra,dec] of border of BICEP region
    outFile -> location to save plot in
    sym_log -> whether to use symmetric log colorbar
    show -> boolean whether to show plot
    
    Output: image saved in outFile directory.
    """
    # load projection and helper functions
    import skymapper as skm
    matplotlib.rcParams.update({'font.size': 36,'text.usetex': True,'font.family': 'serif'})

    # setup figure
    fig = pyl.figure(figsize=(14,14))
    ax = fig.add_subplot(111, aspect='equal')
    
    if sym_log:
    	import matplotlib.colors as colors
    	logthresh=int(-1*np.ceil(np.log10(np.percentile(np.abs(dat),10))))
    	buffer=1
    	maxlog=int(np.ceil(np.log10(max(dat))))
	minlog=int(np.ceil(np.log10(-1*min(dat))))

	tick_locations=([-(10**x) for x in xrange(-logthresh,maxlog,buffer)]
                    +[0.0]
                    +[(10**x) for x in xrange(-logthresh,maxlog,buffer)] )

    # setup map: define AEA map optimal for given RA/Dec
    proj = skm.createConicMap(ax, ra.value, dec.value, proj_class=skm.AlbersEqualAreaProjection)
    # add lines and labels for meridians/parallels (separation 5 deg)
    meridians = np.arange(decLims[0],decLims[1],decLims[2])
    parallels = np.arange(raLims[0],raLims[1],raLims[2])
    skm.setMeridianPatches(ax, proj, meridians, linestyle=':', lw=1., zorder=2)
    skm.setParallelPatches(ax, proj, parallels, linestyle=':', lw=1., zorder=2)
    skm.setMeridianLabels(ax, proj, meridians, loc="left", fmt=skm.pmDegFormatter)
    skm.setParallelLabels(ax, proj, parallels, loc="top", fmt=skm.degFormatter)

    # convert to map coordinates and plot a marker for each point
    x,y = proj(ra.value, dec.value)
    marker = 's'
    markersize = skm.getMarkerSizeToFill(fig, ax, x, y)
    if minMax==None:
    	vmin,vmax=np.percentile(dat,[0,100])
    else:
    	vmin,vmax=minMax
    if not sym_log:
    	sc = ax.scatter(x,y, c=dat, edgecolors='None', marker=marker, s=markersize, cmap=cmap, vmin=vmin, vmax=vmax, rasterized=True, zorder=1)
    else:
    	sc = ax.scatter(x,y, c=dat, edgecolors='None', norm=colors.SymLogNorm(linthresh=10**-logthresh, linscale=1),\
    	    	marker=marker, s=markersize, cmap=cmap, vmin=vmin, vmax=vmax, rasterized=True, zorder=1)
    
    
    # add border of BICEP region
    if border !=None:
    	xB,yB=proj(border[0],border[1]) # read in border coordinates
    	bor = ax.plot(xB,yB,c='k',lw=3,ls='--') # plot border
    
    # add colorbar
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("bottom", size="3%", pad=0.0)
    if not sym_log:
    	cb = fig.colorbar(sc, cax=cax,orientation='horizontal')
    else:
    	cb = fig.colorbar(sc,cax=cax,orientation='horizontal',ticks=tick_locations)
    #cb.set_label(cbar_label,fontsize=26)
 
    # show (and save) ...
    fig.tight_layout()
    if outFile!=None:
        fig.savefig(outFile,bbox_inches='tight')
    if show:
        fig.show()
    else:
        fig.clf()
	fig.clear()


def mollweide_map(dat,ra,dec,cbar_label=None,cmap='jet',decLims=[-90,-40,5],raLims=[-180,30,10],minMax=None,border=None,outFile=None,show=False):
    """Plot in Mollweide Projection.
    Inputs:
    data -> values to plot
    ra,dec -> coordinates
    cbar_label -> label for colorbar
    cmap -> colormap (e.g. 'jet)
    minMax -> [min,max] for colorbar
    decLims/raLims -> give min/max/step for RA and dec lines
    border -> [ra,dec] of border of BICEP region
    outFile -> location to save plot in
    show -> boolean whether to show plot
    
    Output: image saved in outFile directory.
    """
    # load projection and helper functions
    matplotlib.rcParams.update({'font.size': 22,'text.usetex': True,'font.family': 'serif'})

    # setup figure
    fig = pyl.figure(figsize=(25,15))
    ax = fig.add_subplot(111, projection='mollweide')

    # setup map: define AEA map optimal for given RA/Dec
    #proj = skm.createConicMap(ax, ra.value, dec.value, proj_class=skm.AlbersEqualAreaProjection)
    # add lines and labels for meridians/parallels (separation 5 deg)
    #meridians = np.arange(decLims[0],decLims[1],decLims[2])
    #parallels = np.arange(raLims[0],raLims[1],raLims[2])
    #skm.setMeridianPatches(ax, proj, meridians, linestyle=':', lw=0.5, zorder=2)
    #skm.setParallelPatches(ax, proj, parallels, linestyle=':', lw=0.5, zorder=2)
    #skm.setMeridianLabels(ax, proj, meridians, loc="left", fmt=skm.pmDegFormatter)
    #skm.setParallelLabels(ax, proj, parallels, loc="top", fmt=skm.degFormatter)

    # convert to map coordinates and plot a marker for each point
    x,y = ra.value*np.pi/180., dec.value*np.pi/180.
    marker = 's'
    markersize=50
    #markersize = skm.getMarkerSizeToFill(fig, ax, x, y)
    if minMax==None:
    	vmin,vmax=np.percentile(dat,[0,100])
    else:
    	vmin,vmax=minMax
    sc = ax.scatter(x,y, c=dat, edgecolors='None', marker=marker, s=markersize, cmap=cmap, vmin=vmin, vmax=vmax)#, rasterized=True, zorder=1)
    
    # add border of BICEP region
    if border !=None:
    	xB,yB=border[0],border[1] # read in border coordinates
    	bor = ax.plot(xB,yB,c='k',lw=2,ls='--') # plot border
    
    # add colorbar
    #from mpl_toolkits.axes_grid1 import make_axes_locatable
    #divider = make_axes_locatable(ax)
    #cax = divider.append_axes("right", size="3%", pad=0.0)
    cb = fig.colorbar(sc)#, cax=cax)
    cb.set_label(cbar_label,fontsize=20)
 
    # show (and save) ...
    fig.tight_layout()
    if outFile!=None:
        fig.savefig(outFile,bbox_inches='tight')
    if show:
        fig.show()
    else:
        fig.clf()
	fig.clear()


def hexadecapole_plots(map_size=a.map_size,sep=a.sep,FWHM=a.FWHM,noise_power=a.noise_power,\
	freq=a.freq,delensing_fraction=a.delensing_fraction,root_dir=a.root_dir,border=False):
	""" Function to create plots for each tile.
	Other plots are saved in the Maps/ directory """
	import warnings # catch rogue depracation warnings
	warnings.filterwarnings("ignore", category=DeprecationWarning) 
	
	import matplotlib.pyplot as plt
	from scipy.stats import percentileofscore
	import os
	
	# Import good map IDs
	goodMaps=np.load(root_dir+'%sdeg%sGoodIDs.npy' %(map_size,sep))
	
	# Define arrays
	A,Afs,Afc,fs,fc,ang,frac,probA,probP,logA,H2Pow,H2PowErr,H2PowSig,logH2Pow=[np.zeros(len(goodMaps)) for _ in range(14)]
	A_err,Af_err,f_err,ang_err,frac_err,frac_mean,biasedH2Pow,biasedEps=[np.zeros(len(goodMaps)) for _ in range(8)]
	norm_prob,debiasedH2=[np.zeros(len(goodMaps)) for _ in range(2)]
	
	# Define output directories:
	outDir=root_dir+'PaddedLensedMaps/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction)
	
	if not os.path.exists(outDir):
		os.makedirs(outDir)
	
	# Iterate over maps:
	for i in range(len(goodMaps)):
		map_id=goodMaps[i] # map id number
		if i%100==0:
			print 'loading %s of %s' %(i+1,len(goodMaps))
		# Load in data from tile
		data=np.load(root_dir+'LensedPaddedBatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/%s.npy' %(freq,map_size,sep,FWHM,noise_power,delensing_fraction,i))
		
		# Load in data
		A[i],fs[i],fc[i],Afs[i],Afc[i],frac[i],ang[i]=[d[0] for d in data[:7]]
		H2Pow[i]=data[9][0]
		debiasedH2[i]=data[9][0]
		biasedEps[i]=frac[i]
		biasedH2Pow[i]=np.log10((biasedEps[i]*A[i])**2.)
		H2PowErr[i]=data[9][2]
		H2PowSig[i]=H2Pow[i]/H2PowErr[i]
		if H2Pow[i]>=0.:
			frac[i]=np.sqrt(H2Pow[i])/A[i]
		else:
			frac[i]=0.
		wCorrection=data[12]
		isoBias=data[13]
		if data[9][0]>0.:
			logH2Pow[i]=np.log10(data[9][0])
		else:
			logH2Pow[i]=-100.#logH2Pow[i-1] # avoid errors
		#logH2Pow[i]=np.log10(np.abs(data[9][0]))
		if A[i]>0:
			logA[i]=np.log10(A[i])
		else:
			logA[i]=-100.#logA[i-1] # to avoid errors
		A_err[i],fs_err,fc_err,Afs_err,Afc_err,frac_err[i]=[d[2] for d in data[:6]]
		#frac_mean[i]=data[5][1]
		
		# Compute other errors
		f_err[i]=np.mean([fs_err,fc_err])
		Af_err[i]=np.mean([Afs_err,Afc_err])
		if H2Pow[i]>0.:
			ang_err[i]=Af_err[i]/(4*np.sqrt(H2Pow[i]))*180./np.pi
		else:
			ang_err[i]=100. # to avoid errors
		
		# Creat epsilon plot
		H2_all=data[7][7] # all H2 data (debiased)
						
		percentile=percentileofscore(H2_all,H2Pow[i],kind='mean') # compute percentile of estimated data
		probP[i]=percentile
		from scipy.stats import norm
		
		#if H2Pow[i]>0:
		#	sigmaAf=H2PowErr[i]/(2.*np.sqrt(H2Pow[i]))
		#else:
		#	sigmaAf=1.0e10 # to ensure CDF=0
		sigmaAf=Af_err[i]
		def H2_CDF(H2):	
			""" CDF of H2 chi-squared distribution)"""
			return 1-np.exp(-(H2+isoBias)/(2.*wCorrection*sigmaAf**2.))
		def H2_PDF(H2):
			""" PDF of H2 modified chi-squared distribution"""
			return 1./(2.*wCorrection*sigmaAf**2.)*np.exp(-(H2+isoBias)/(2.*wCorrection*sigmaAf**2.)) 
		# Compute analytic CDF percentile:
		temp=H2_CDF(H2Pow[i])
		if temp>0.:
			probA[i]=100.*H2_CDF(H2Pow[i])
		else:
			probA[i]=0.
			
		if probA[i]>100.:
			norm_prob[i]=30.
		elif probA[i]<0.:
			norm_prob[i]=-30.
		else:
			norm_prob[i]=norm.ppf(probA[i]/100.)
		
	np.savez('TestData.npz',norm=norm_prob,probA=probA,probP=probP)
		
	## Now compute the whole patch maps
	# Dataset:
	dat_set=[norm_prob,debiasedH2,A,fs,fc,Afs,Afc,frac,ang,A_err,Af_err,f_err,frac_err,ang_err,probA,probP,logA,H2Pow,H2PowErr,logH2Pow,\
		H2PowSig,biasedH2Pow,biasedEps]
	names=[r'$\tilde{p}$',r'$\mathcal{H}^2',r'Monopole amplitude',r'$f_s$',r'$f_c$',r'$Af_s$',r'$Af_c$',r'Anisotropy Fraction, $\epsilon$',r'Anisotropy Angle, $\alpha$',r'MC error for $A$',r'MC error for $Af$',r'MC error for $f$',r'MC error for anisotropy fraction',r'MC error for angle',r'$\mathcal{H}^2$ Isotropic Percentile, $p$, (Analytic)',r'$\mathcal{H}^2$ Isotropic Percentile, $p$, (Statistical)',r'$\log_{10}(A)$',r'$\mathcal{H}^2$',r'$\mathcal{H}^2$ Error',r'$\log_{10}\mathcal{H}^2$','r$\mathcal{H}^2$ quasi-significance',r'$\log_{10}H^2$',r'$\epsilon$']
	file_str=['norm_prob','debiased_H2','A','fs','fc','Afs','Afc','epsilon','angle','A_err','Af_err','f_err',\
	'epsilon_err','ang_err','prob_analyt','prob_stat','logA','Hex2Pow','Hex2PowErr','logHex2Pow','Hex2PowSig','biasedH2',\
	'biased_epsilon']
	
	# Load coordinates of map centres
	from .NoisePower import good_coords
	ra,dec=good_coords(map_size,sep,len(goodMaps),root_dir=root_dir)
	# Load in border of BICEP region if necessary:
	if border:
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
		sym_log=False
		if file_str[j]=='angle':
			cmap=cmocean.cm.phase
		if file_str[j]=='epsilon':
			vmin,vmax=np.percentile(dat_set[j],[3,97])
			minMax=[vmin,vmax]
		if file_str[j]=='debiased_H2':
			sym_log=True
			cmap='bwr'
			vmax=np.percentile(dat_set[j],98)
			vmin=-vmax
			#vmin,vmax=np.percentile(dat_set[j],[5,100])
			minMax=[vmin,vmax]
		if file_str[j]=='norm_prob':
			data=dat_set[j]
			filt=np.where((data<30.)&(data>-30.))
			vmax=np.percentile(data[filt],95)
			minMax=[-vmax,vmax]
			cmap='bwr'
		if file_str[j]=='biasedH2':
			vmin,vmax=np.percentile(dat_set[j],[3,97])
			minMax=[vmin,vmax]
		if file_str[j]=='biased_epsilon':
			vmin,vmax=np.percentile(dat_set[j],[3,97])
			minMax=[vmin,vmax]
		if file_str[j]=='ang_err':
			vmin,vmax=np.percentile(dat_set[j],[5,95])
			minMax=[vmin,vmax]
		if file_str[j]=='logHex2Pow':
			cut_dat=dat_set[j]
			cut_dat=cut_dat[cut_dat>-99]
			minMax=[min(cut_dat),max(cut_dat)]
		if file_str[j]=='logA':
			vmin,vmax=np.percentile(dat_set[j],[3,97])
			minMax=[vmin,vmax]
		if file_str[j]=='epsilon_err':
			vmin,vmax=np.percentile(dat_set[j],[0,95])
			minMax=[vmin,vmax]
		if file_str[j]=='Hex2PowSig':
			vmin,vmax=np.percentile(dat_set[j],[0,95])
			minMax=[vmin,vmax]
		from hades.plotTools import skyMap
		# Create plot
		skyMap(dat_set[j],ra,dec,cbar_label=names[j],cmap=cmap,minMax=minMax,sym_log=sym_log,\
			border=border_coords,outFile=outDir+file_str[j]+'.png')

