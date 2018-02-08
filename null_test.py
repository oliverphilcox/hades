import numpy as np
from hades.params import BICEP
a=BICEP()	

if __name__=='__main__':
	""" This is the iterator for batch processing the map creation through HTCondor. Each map is done separately, and argument is map_id."""
	import time
	start_time=time.time()
	import sys
	import pickle
	sys.path.append('/data/ohep2/')
	sys.path.append('/home/ohep2/Masters/')
	import os
	
	all_id=int(sys.argv[1]) # batch_id number
	
	# First load good IDs:
	goodFile=a.root_dir+'%sdeg%sGoodIDs.npy' %(a.map_size,a.sep)
	
	outDir=a.root_dir+'NullTestBatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction)
	
	if all_id<110: # create first time
		from hades.batch_maps import create_good_map_ids
		create_good_map_ids()
		print 'creating good IDs'
		
	goodIDs=np.load(goodFile)
	
	batch_id=all_id%len(goodIDs)
	param_id=all_id//len(goodIDs)
	
	if param_id>len(a.f_dust_all)-1:
		print 'Process %s terminating' %batch_id
		sys.exit() # stop here
	
	f_dust=a.f_dust_all[param_id]
	err_repeats=a.err_repeats # repeat for errors
	
	if a.remakeErrors:
		counter=0
		for j in range(err_repeats):
			if os.path.exists(outDir+'%s_%s_%s.npy' %(batch_id,param_id,j)):
				counter+=1
		if counter==err_repeats:
			print 'done'
			sys.exit() # only exit if all data are created
	
	map_id=goodIDs[batch_id] # this defines the tile used here
	
	
	# Now run the estimation
	from hades.debiased_wrapper import tile_wrap
	def runner(map_id):
		return tile_wrap(map_id,f_dust=f_dust)
	
	# Save output to file
	if not os.path.exists(outDir): # make directory
		os.makedirs(outDir)
		
	for j in range(err_repeats): # repeat for MC errors
		print 'f_dust %s tile %s run %s starting for map_id %s' %(f_dust,batch_id,j,map_id)		
		output=runner(map_id)		
		np.save(outDir+'%s_%s_%s.npy' %(batch_id,param_id,j), output) # save output
	
	print "Task %s tile %s complete in %s seconds" %(param_id,batch_id,time.time()-start_time)
	
	if batch_id==len(a.f_dust_all)*len(goodIDs)-2:
		if a.send_email:
			from hades.NoiseParams import sendMail
			sendMail('Single Map Null Test')
			
def create_significances(map_size=a.map_size,sep=a.sep,FWHM=a.FWHM,noise_power=a.noise_power,delensing_fraction=a.delensing_fraction,freq=a.freq,root_dir=a.root_dir):
	""" Recreate + plot significances from parameters."""
	from hades.hex_wrap import patch_hexadecapole
	mean,err=[np.zeros(len(a.f_dust_all)) for _ in range(2)]
	for i in range(len(a.f_dust_all)):
		sigs=[]
		for j in range(a.err_repeats):
			suffix='_'+str(i)+'_'+str(j)
			outs=patch_hexadecapole(suffix=suffix,map_size=map_size,sep=sep,FWHM=FWHM,noise_power=noise_power,\
				delensing_fraction=delensing_fraction,freq=freq,folder='NullTestBatchData',plot=False)
			sigs.append(outs[0])
		mean[i]=np.mean(sigs)
		err[i]=np.std(sigs)
		print 'f_dust: %s mean: %s std: %s' %(a.f_dust_all[i],mean[i],err[i])
	 
	# Now plot
	import matplotlib.pyplot as plt
	plt.figure()
	plt.errorbar(a.f_dust_all,mean,yerr=err,fmt='x')
	plt.rc('text', usetex=True)
	plt.rc('font', family='serif')
	plt.xlabel(r'$f_\mathrm{dust}$')
	plt.ylabel(r'Detection Significance')
	plt.title(r'Null Test Significances')
	plt.savefig(root_dir+'NullTestPlotCorrected_f%s_ms%s_s%s_fw%s_np%s_d%s.png' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction),bbox_inches='tight')
	plt.close()
	
	print 'Plotting complete'
		
def plot_hexadecapole(map_size=a.map_size,sep=a.sep,FWHM=a.FWHM,noise_power=a.noise_power,delensing_fraction=a.delensing_fraction,freq=a.freq,root_dir=a.root_dir):
	""" Recreate + plot hexadecapoles from parameters."""
	from hades.hex_wrap import patch_hexadecapole
	h2_mean,h2_est,h2_eps,bias=[],[],[],[]
	for i in range(len(a.f_dust_all)):
		suffix='_'+str(i)+'_0'#+str(0)
		outs=patch_hexadecapole(suffix=suffix,map_size=map_size,sep=sep,FWHM=FWHM,noise_power=noise_power,\
				delensing_fraction=delensing_fraction,freq=freq,folder='NullTestBatchData',returnAll=True)
		h2_mean.append(outs[0])
		h2_eps.append(outs[1])
		h2_est.append(outs[2])
		bias.append(outs[5])
		#print 'f_dust: %s mean: %s std: %s' %(a.f_dust_all[i],mean[i],err[i])
	 
	# Now plot
	import matplotlib.pyplot as plt
	plt.figure()
	#np.savez('/data/ohep2/testDat.npz',f_dust=a.f_dust_all,h2mean=h2_mean,h2eps=h2_eps,h2est=h2_est)
	yerr=(np.array(h2_eps))/(np.log(10)*(np.array(h2_mean)+np.array(bias)))
	plt.rc('text', usetex=True)
	plt.rc('font', family='serif')
	plt.errorbar(np.array(a.f_dust_all),np.log10(np.array(bias)+np.array(h2_mean)),yerr=yerr,fmt='x',label='Biased MC prediction')
	plt.scatter(a.f_dust_all,np.log10(np.array(bias)),marker='x',c='g',label='Bias')
	plt.scatter(a.f_dust_all,np.log10(np.array(bias)+np.array(h2_est)),marker='x',c='r',label='Biased Estimate')
	plt.xlabel(r'$f_\mathrm{dust}$')
	plt.ylabel(r'$\log_{10}{H^2}$')
	#plt.yscale('log')
	plt.legend()
	plt.title(r'Null Test Hexadecapole Strength')
	plt.savefig(root_dir+'NullTestH2Plot_f%s_ms%s_s%s_fw%s_np%s_d%s.png' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction),bbox_inches='tight')
	plt.close()
	
	print 'Plotting complete'
		