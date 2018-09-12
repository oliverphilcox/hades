from hades.params import BICEP
a=BICEP()

# Default parameters
nmin = 0
nmax = 1e5#1399#3484
cores = 42

if __name__=='__main__':
     """ Batch process to use all available cores to compute the KK estimators and Gaussian errors using the est_and_err function im MCerror
    Inputs are min and max file numbers. Output is saved as npy file"""

     import tqdm
     import sys
     import numpy as np
     import multiprocessing as mp
     	
     # Parameters if input from the command line
     if len(sys.argv)>=2:
         nmin = int(sys.argv[1])
     if len(sys.argv)>=3:
         nmax = int(sys.argv[2])
     if len(sys.argv)==4:
         cores = int(sys.argv[3])
     
     # Compute map IDs with non-trivial data
     all_file_ids=np.arange(nmin,nmax+1)
     import pickle
     goodMaps=pickle.load(open(a.root_dir+str(a.map_size)+'deg'+str(a.sep)+'/fvsgoodMap.pkl','rb'))
     
     file_ids=[int(all_file_ids[i]) for i in range(len(all_file_ids)) if goodMaps[i]!=False] # just for correct maps
     
     # Start the multiprocessing
     p = mp.Pool(processes=cores)
     
     # Define iteration function
     from hades.NoiseBatch import noisy_iterator
     
     # Display progress bar with tqdm
     r = list(tqdm.tqdm(p.imap(noisy_iterator,file_ids),total=len(file_ids)))
     
     if not a.NoiseAnalysis:
     	# Save output
     	np.save(a.root_dir+'%sdeg%s/NoisyMCestimates%sdeg%s.npy' %(a.map_size,a.sep,a.map_size,a.sep),np.array(r))
     if a.NoiseAnalysis:
     	import os
     	outDir=a.root_dir+'%sdeg%s/NoiseAnalysis/' %(a.map_size,a.sep)
     	if not os.path.exists(outDir):
     		os.mkdir(outDir)
     	if a.ComparisonSetting=='FWHM':
     		np.save(outDir+'FWHM%.2f.npy' %a.FWHM,np.array(r))
     	else:
     		np.save(outDir+'NoisePower%.2f.npy' %a.noise_power,np.array(r))


def noisy_iterator(map_id):
	""" To run the iterations"""
	from hades.NoisePower import est_and_err
	out = est_and_err(int(map_id))
	print('%s map complete' %map_id)
	return out
	

