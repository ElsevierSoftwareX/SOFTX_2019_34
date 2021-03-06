##########################################################################################
# import packages
##########################################################################################
import glob
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops, marching_cubes_lewiner   
import pyvista
##########################################################################################
# function to read tiff files 
##########################################################################################
def tif_reader(path,input_file,color_idx):
	fnames = glob.glob(path + '/*.tif')
	num_images = len(fnames)
	sample_img = plt.imread(input_file%('0000'))
	size_x = sample_img.shape[0]
	size_y = sample_img.shape[1] 
	
	all_array = np.zeros((size_x,size_y,num_images))
	for kk in range(0,num_images):
		if kk < 10:
			num = '000%i'%(kk)
		elif kk < 100:
			num = '00%i'%(kk)
		else:
			num = '0%i'%(kk)
		
		fname =  input_file%(num)
		img = plt.imread(fname)
		all_array[:,:,kk] = img[:,:,color_idx]
	
	return all_array 

##########################################################################################
# functions to pre-process cell images
#	OUTPUTS:
#		- marching cubes cell surface mesh
#		- volume per cell 
#		- cell center 
##########################################################################################
def get_cell_surface(path,input_file,save_file,color_idx, X_DIM, Y_DIM, Z_DIM, cell_threshold):
	# import the image file and apply a gaussian filter 
	all_array = tif_reader(path,input_file,color_idx)
	all_array = ndimage.gaussian_filter(all_array,2)
	
	# threshold the image based on a set threshold
	bw = all_array > cell_threshold
	
	# find connected volumes
	label_img = label(bw, connectivity=bw.ndim)
	props = regionprops(label_img)
	centroids = np.zeros((len(props),3))
	areas = np.zeros((len(props)))
	for kk in range(len(props)):
		centroids[kk] = props[kk].centroid
		areas[kk] = props[kk].area
	
	# assume cell is the largest connected volume
	arg = np.argmax(areas)
	
	# save the cell volume
	vox_size = X_DIM / bw.shape[1] * Y_DIM / bw.shape[0] * Z_DIM / bw.shape[2]
	vol = areas[arg] * vox_size
	np.savetxt( save_file + 'volume.txt' , np.asarray([vol]))
	
	# save the cell center
	cell_center = np.asarray([ centroids[arg,1] * X_DIM / bw.shape[1] , centroids[arg,0] * Y_DIM / bw.shape[0] , centroids[arg,2] * Z_DIM / bw.shape[2] ])
	np.savetxt( save_file + 'center.txt', cell_center)
	
	# isolate the cell 
	bw_cell = np.zeros(bw.shape)
	for ii in range(0,bw.shape[0]):
		for jj in range(0,bw.shape[1]):
			for kk in range(0,bw.shape[2]):
				if label_img[ii,jj,kk] == int(arg+1):
					bw_cell[ii,jj,kk] = 1.0
	
	# flip the ii and jj dimensions to be compatible with the marching cubes algorithm
	bw_cell = np.swapaxes(bw_cell,0,1)
	
	# get the cell surface mesh from the marching cubes algorithm and the isolated cell image
	# https://scikit-image.org/docs/dev/api/skimage.measure.html#skimage.measure.marching_cubes_lewiner
	verts,faces, normals,_ = marching_cubes_lewiner(bw_cell,spacing=(X_DIM/bw_cell.shape[0], Y_DIM/bw_cell.shape[1], Z_DIM/bw_cell.shape[2]))
	
	# save surface mesh info
	np.savetxt(save_file + 'mesh.txt',verts)
	np.savetxt(save_file + 'normals.txt',normals)
	np.savetxt(save_file + 'faces.txt',faces)	

	output_paraview_file(verts,faces,save_file + 'paraview.vtk')
	return 

def output_paraview_file(verts,faces,filename):
	threes = np.ones((faces.shape[0],1))*3
	faces = np.hstack((threes,faces))

	surf = pyvista.PolyData(verts, faces)
	surf.save(filename)

	#meshio.Mesh(points, cells={'tetra':faces})


##########################################################################################
# functions to pre-process bead images
#	OUTPUTS:
#		- x, y, z position of each bead based on the input images 
##########################################################################################
def get_bead_centers(path,input_file,save_file,color_idx, X_DIM, Y_DIM, Z_DIM):
	# import the image file and apply a gaussian filter 
	all_array = tif_reader(path,input_file,color_idx)
	all_array = ndimage.gaussian_filter(all_array,1)
	
	# apply an otsu filter, specify the filter at each z slice 
	# otsu filter https://en.wikipedia.org/wiki/Otsu%27s_method 
	num_slice = all_array.shape[2]
	bw = np.zeros((all_array.shape))
	for kk in range(0,num_slice):
		thresh = threshold_otsu(all_array[:,:,kk])
		bw[:,:,kk] = all_array[:,:,kk] > thresh
	
	# find connected volumes within the image, assume each connected volume is a bead 
	# record the centroid of each connected volume as the location of the beads
	# relies on https://scikit-image.org/docs/dev/api/skimage.measure.html#skimage.measure.regionprops
	label_img = label(bw, connectivity=bw.ndim)
	props = regionprops(label_img)
	centroids = np.zeros((len(props),3))
	for kk in range(len(props)):
		centroids[kk]=props[kk].centroid
	
	centroids_order = np.zeros(centroids.shape)
	centroids_order[:,0] = centroids[:,1] * X_DIM / bw.shape[1] 
	centroids_order[:,1] = centroids[:,0] * Y_DIM / bw.shape[0]
	centroids_order[:,2] = centroids[:,2] * Z_DIM / bw.shape[2] 

	np.savetxt(save_file,centroids_order)
	return 

