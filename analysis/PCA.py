import logging
import numpy as np
import pylab as plt
import scipy.stats as st
from colour import Color
from matplotlib import gridspec
import matplotlib.ticker as ticker
from scipy.spatial import ConvexHull
from sklearn.decomposition import PCA
from scipy.signal import argrelextrema
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import proj3d
from matplotlib.patches import FancyArrowPatch

logging.basicConfig(format='[%(funcName)s]: %(message)s', level=logging.INFO)
log = logging.getLogger()


class Arrow3D(FancyArrowPatch):
	def __init__(self, xs, ys, zs, *args, **kwargs):
		FancyArrowPatch.__init__(self, (0, 0), (0, 0), *args, **kwargs)
		self._verts3d = xs, ys, zs

	def draw(self, renderer):
		xs3d, ys3d, zs3d = self._verts3d
		xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
		self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
		FancyArrowPatch.draw(self, renderer)


def form_ellipse(P):
	""" Form the ellipsoid based on all points
	Here, P is a numpy array of points:
	P = [[x1,y1,z1],
		 . . .
		 [xn,yn,zn]]
	Returns:
		np.ndarray: radii values
		np.ndarray: rotation matrix
	"""
	# get P shape information
	points_number, dimension = P.shape
	# auxiliary matrix
	u = (1 / points_number) * np.ones(points_number)
	# vector containing the center of the ellipsoid
	center = P.T @ u
	# this matrix contains all the information regarding the shape of the ellipsoid
	matrixA = np.linalg.inv(P.T @ (np.diag(u) @ P) - np.outer(center, center)) / dimension
	# to get the radii and orientation of the ellipsoid take the SVD of the output matrix A
	_, size, rotation = np.linalg.svd(matrixA)
	# the radii are given by
	radiuses = 1 / np.sqrt(size)
	# rotation matrix gives the orientation of the ellipsoid
	return radiuses, rotation, matrixA


def plot_ellipsoid(center, radii, rotation, plot_axes=False, color='b'):
	"""
	Plot an ellipsoid
	Args:
		center (np.ndarray): center of the ellipsoid
		radii (np.ndarray): radius per axis
		rotation (np.ndarray): rotation matrix
		plot_axes (bool): plot the axis of ellipsoid if need
		color (str): color in matlab forms (hex, name of color, first char of color)
	"""
	# (for plotting) set the number of grid for plotting surface
	stride = 4
	#
	phi = np.linspace(0, np.pi, 100)
	theta = np.linspace(0, 2 * np.pi, 100)
	# cartesian coordinates that correspond to the spherical angles
	x = radii[0] * np.outer(np.cos(theta), np.sin(phi))
	y = radii[1] * np.outer(np.sin(theta), np.sin(phi))
	z = radii[2] * np.outer(np.ones_like(theta), np.cos(phi))
	# rotate accordingly
	for i in range(len(x)):
		for j in range(len(x)):
			x[i, j], y[i, j], z[i, j] = np.dot([x[i, j], y[i, j], z[i, j]], rotation) + center

	ax = plt.gca()
	# additional visualization for debugging
	if plot_axes:
		# matrix of axes
		axes = np.array([[radii[0], 0.0, 0.0],
		                 [0.0, radii[1], 0.0],
		                 [0.0, 0.0, radii[2]]])
		# rotate accordingly
		for i in range(len(axes)):
			axes[i] = np.dot(axes[i], rotation)
		# plot axes
		for point in axes:
			X_axis = np.linspace(-point[0], point[0], 5) + center[0]
			Y_axis = np.linspace(-point[1], point[1], 5) + center[1]
			Z_axis = np.linspace(-point[2], point[2], 5) + center[2]
			ax.plot(X_axis, Y_axis, Z_axis, color='g')
	# plot ellipsoid with wireframe
	ax.plot_wireframe(x, y, z, rstride=stride, cstride=stride, color=color, alpha=0.1)
	ax.plot_surface(x, y, z, rstride=stride, cstride=stride, color=color, alpha=0.05)


def split_by_slices(data, slice_length):
	"""
	TODO: add docstring
	Args:
		data (np.ndarray): data array
		slice_length (int): slice length in steps
	Returns:
		np.ndarray: sliced data
	"""
	slices_begin_indexes = range(0, len(data) + 1, slice_length)
	splitted_per_slice = [data[beg:beg + slice_length] for beg in slices_begin_indexes]
	# remove tails
	if len(splitted_per_slice[0]) != len(splitted_per_slice[-1]):
		del splitted_per_slice[-1]
	return splitted_per_slice


def smooth(data, box_pts):
	"""
	Smooth the data by N box_pts number
	Args:
		data (np.ndarray): original data
		box_pts (int):
	Returns:
		np.ndarray: smoothed data
	"""
	box = np.ones(box_pts) / box_pts
	return np.convolve(data, box, mode='same')


def find_extrema(array, condition):
	"""
	Advanced wrapper of numpy.argrelextrema
	Args:
		array (np.ndarray): data array
		condition (np.ufunc): e.g. np.less (<), np.great_equal (>=) and etc.
	Returns:
		np.ndarray: indexes of extrema
		np.ndarray: values of extrema
	"""
	# get indexes of extrema
	indexes = argrelextrema(array, condition)[0]
	# in case where data line is horisontal and doesn't have any extrema -- return None
	if len(indexes) == 0:
		return None, None
	# get values based on found indexes
	values = array[indexes]
	# calc the difference between nearby extrema values
	diff_nearby_extrema = np.abs(np.diff(values, n=1))
	# form indexes where no twin extrema (the case when data line is horisontal and have two extrema on borders)
	indexes = np.array([index for index, diff in zip(indexes, diff_nearby_extrema) if diff > 0] + [indexes[-1]])
	# get values based on filtered indexes
	values = array[indexes]

	return indexes, values


def get_lat_matrix(sliced_datasets, step_size, debugging=False):
	"""
	Function for finding latencies at each slice in normalized (!) data
	Args:
		sliced_datasets (np.ndarry): arrays of data
		                      data per slice
		               [[...], [...], [...], [...],
		dataset number  [...], [...], [...], [...],
		                [...], [...], [...], [...]]
		step_size (float): data step
		debugging (bool): True -- will print debugging info and plot figures
	Returns:
		np.ndarray: latencies indexes
	"""
	if type(sliced_datasets) is not np.ndarray:
		raise TypeError("Non valid type of data - use only np.ndarray")

	global_lat_indexes = []
	micro_border = 0.005
	l_poly_border = int(10 / step_size)

	datasets_number = len(sliced_datasets)
	slices_number = len(sliced_datasets[0])
	latency_matrix = np.zeros((datasets_number, slices_number))

	# or use sliced_datasets.reshape(-1, sliced_datasets.shape[2])
	for dataset_index, slices_per_experiment in enumerate(sliced_datasets):
		for slice_index, slice_data in enumerate(slices_per_experiment):
			# smooth data to avoid micro peaks and noise
			smoothed_data = smooth(slice_data, 2)
			smoothed_data[:2] = slice_data[:2]
			smoothed_data[-2:] = slice_data[-2:]

			# I. find latencies (begining of poly answer)
			gradient = np.gradient(smoothed_data)
			assert len(gradient) == len(smoothed_data)
			# get only poly area data (exclude mono answer and activity before it)
			poly_gradient = gradient[l_poly_border:]
			# get positive gradient X Y data
			pos_gradient_x = np.argwhere(poly_gradient > 0).flatten()
			pos_gradient_y = poly_gradient[pos_gradient_x].flatten()
			# get negative gradient X Y data
			negative_gradient_x = np.argwhere(poly_gradient < 0).flatten()
			negative_gradient_y = poly_gradient[negative_gradient_x].flatten()
			# calc the median, Q1, and Q3 values of dots
			if len(pos_gradient_y):
				pos_gradient_Q1, pos_gradient_med, pos_gradient_Q3 = np.percentile(pos_gradient_y, [20, 50, 80])
			else:
				pos_gradient_Q1, pos_gradient_med, pos_gradient_Q3 = np.inf, np.inf, np.inf
			if len(negative_gradient_y):
				neg_gradient_Q1, neg_gradient_med, neg_gradient_Q3 = np.percentile(negative_gradient_y, [20, 50, 80])
			else:
				neg_gradient_Q1, neg_gradient_med, neg_gradient_Q3 = -np.inf, -np.inf, -np.inf
			# find the index of latency by the cross between gradient and negative grad Q1/positive grad Q3
			latency_index = None
			for index, grad in enumerate(gradient[l_poly_border:]):
				if (grad > pos_gradient_Q3 or grad < neg_gradient_Q1) and (grad > micro_border or grad < -micro_border):
					latency_index = index + l_poly_border
					break
			# if not found -- take the last index
			else:
				latency_index = len(gradient) - 1
			# collect found item
			latency_matrix[dataset_index][slice_index] = latency_index

			if debugging:
				plt.figure(figsize=(16, 9))
				plt.axhline(y=pos_gradient_Q3, color='r', linestyle='dotted')
				plt.axhline(y=neg_gradient_Q1, color='b', linestyle='dotted')
				plt.fill_between(np.arange(len(poly_gradient)) + l_poly_border,
				                 poly_gradient, [0] * len(poly_gradient), color='r', alpha=0.6)
				plt.fill_between(range(len(gradient)),
				                 [0] * len(gradient), [-1] * len(gradient), color='w')
				plt.fill_between(np.arange(len(poly_gradient)) + l_poly_border,
				                 poly_gradient, [0] * len(poly_gradient), color='b', alpha=0.2)
				plt.axhline(y=0, color='k', linestyle='--')
				plt.plot(smoothed_data, color='b', label="slice data")
				plt.plot(np.arange(len(gradient)), gradient, color='r', label="gradient")
				plt.plot(np.arange(len(gradient)), gradient, '.', color='k', markersize=1)
				plt.plot([latency_index], [smoothed_data[latency_index]], '.', color='k', markersize=15)
				plt.xlim(0, len(smoothed_data))
				plt.xticks(range(len(smoothed_data)),
				           [x * step_size if x % 25 == 0 else None for x in range(len(smoothed_data) + 1)])
				plt.legend()
				plt.show()

	return latency_matrix


def list3d(h, w):
	return [[[] for _ in range(w)] for _ in range(h)]


def get_all_peak_amp_per_slice(sliced_datasets, dstep, split_by_intervals=False, debugging=False):
	"""
	Finds all peaks times and amplitudes at each slice

	# 1. all slices must have equal size
	# 2.

	Args:
		sliced_datasets (np.ndarray):
		dstep (float): data step size
		debugging (bool): debugging flag
	Returns:
		list: 3D list of peak times, [experiment_index][slice_index][peak time]
		list: 3D list of peak ampls, [experiment_index][slice_index][peak ampl]
	"""
	if type(sliced_datasets) is not np.ndarray:
		raise TypeError("Non valid type of data - use only np.ndarray")

	# form parameters for filtering peaks
	min_ampl = 0.3
	min_dist = int(0.7 / dstep)
	max_dist = int(4 / dstep)
	# interpritate shape of dataset
	tests_count, slices_count, slice_length = sliced_datasets.shape
	peak_per_slice_list = list3d(h=tests_count, w=slices_count)
	ampl_per_slice_list = list3d(h=tests_count, w=slices_count)

	# find all peaks times and amplitudes per slice
	for experiment_index, slices_data in enumerate(sliced_datasets):
		# combine slices into one myogram
		y = np.array(slices_data).ravel()
		# find all extrema
		e_maxima_indexes, e_maxima_values = find_extrema(y, np.greater)
		e_minima_indexes, e_minima_values = find_extrema(y, np.less)
		# start pairing extrema from maxima
		if e_minima_indexes[0] < e_maxima_indexes[0]:
			comb = zip(e_maxima_indexes, e_minima_indexes[1:])
		else:
			comb = zip(e_maxima_indexes, e_minima_indexes)
		# process each extrema pair
		for max_index, min_index in comb:
			max_value = e_maxima_values[e_maxima_indexes == max_index][0]
			min_value = e_minima_values[e_minima_indexes == min_index][0]
			dT = abs(max_index - min_index)
			dA = abs(max_value - min_value)
			# check the difference between maxima and minima
			if (min_dist <= dT <= max_dist) and dA >= 0.05 or dA >= min_ampl:
				slice_index = int(max_index // slice_length)
				peak_time = max_index - slice_length * slice_index
				peak_per_slice_list[experiment_index][slice_index].append(peak_time)
				ampl_per_slice_list[experiment_index][slice_index].append(dA)

	if debugging:
		for experiment_index, slices_data in enumerate(sliced_datasets):
			y = np.array(slices_data).ravel()
			raise NotImplemented

	if split_by_intervals:
		raise NotImplemented
		peaks_per_interval = np.zeros((slices_count, len(intervals)))
		peaks_per_interval = peaks_per_interval / dataset_size
		# reshape
		c = peaks_per_interval[:, 0].copy()
		peaks_per_interval[:, 0: -1] = peaks_per_interval[:, 1:]
		peaks_per_interval[:, -1] = c
		peaks_per_interval[:, -1] = np.append(peaks_per_interval[1:, -1], 0)
		return peaks_per_interval

	return peak_per_slice_list, ampl_per_slice_list


def get_area_extrema_matrix(sliced_datasets, latencies, step_size, debugging=False):
	"""
	Finds extrema (as a peak) and sum of amplitudes after latnecy
	Args:
		sliced_datasets (np.ndarray):
		latencies (np.ndarray): array of latencies for each experiment each slice
		step_size (float): data step size
		debugging (bool): debugging flag

	Returns:
		np.ndarray: peak_matrix - [experiment_index][slice_index] = extrema count
		np.ndarray: ampl_matrix - [experiment_index][slice_index] = amplitude area
	"""
	if type(sliced_datasets) is not np.ndarray:
		raise TypeError("Non valid type of data - use only np.ndarray")
	# interpritate shape of dataset
	tests_count, slices_count, slice_length = sliced_datasets.shape
	peak_matrix = np.zeros((tests_count, slices_count))
	ampl_matrix = np.zeros((tests_count, slices_count))
	# form parameters for filtering peaks
	min_ampl = 0.3
	min_dist = int(0.7 / step_size)
	max_dist = int(4 / step_size)
	# find extrema and area of amplitudes at each slice
	for experiment_index, slices_data in enumerate(sliced_datasets):
		for slice_index, slice_data in enumerate(slices_data):
			# smooth data (small value for smoothing only micro-peaks)
			smoothed_data = smooth(slice_data, 2)
			# get all extrema
			e_maxima_indexes, e_maxima_values = find_extrema(smoothed_data, np.greater)
			e_minima_indexes, e_minima_values = find_extrema(smoothed_data, np.less)
			# skip calculating if number of extrema is zero
			if len(e_maxima_indexes) == 0 or len(e_minima_indexes) == 0:
				continue
			# skip minima extrema if it starts before maxima -> start paring from maximal extrema
			if e_minima_indexes[0] < e_maxima_indexes[0]:
				e_minima_indexes = e_minima_indexes[1:]
				e_minima_values = e_minima_values[1:]

			# get minimal size of array to remove dots which will not be processed
			min_size = min(len(e_maxima_indexes), len(e_minima_indexes))
			# form pairs by indexes and values
			pair_indexes = np.stack((e_maxima_indexes[:min_size], e_minima_indexes[:min_size]), axis=1)
			pair_values = np.stack((e_maxima_values[:min_size], e_minima_values[:min_size]), axis=1)
			# calc delta Time and Amplitude for dots in pair
			dT = np.abs(np.diff(pair_indexes, axis=1)).ravel()
			dA = np.abs(np.diff(pair_values, axis=1)).ravel()
			# get latency for current slice
			latency = int(latencies[experiment_index][slice_index])
			# process if both dots in pair greater than latency
			pair_gt_lat = np.all(pair_indexes >= latency, axis=1)
			# (pair >= latency) AND ((dT in [min_dist, max_dist] AND dA is not a micro-peak) OR dA is high enough))
			filter_mask = pair_gt_lat & (((min_dist <= dT) & (dT <= max_dist) & (dA >= 0.05)) | (dA >= min_ampl))
			# fill the data to the matricies
			peak_matrix[experiment_index][slice_index] = len(pair_indexes[filter_mask]) * 2
			ampl_matrix[experiment_index][slice_index] = np.sum(np.abs(smoothed_data[latency:]))


	if debugging:
		raise NotImplemented

	return peak_matrix, ampl_matrix


def contour_plot(x, y, color, ax):
	"""
	TODO: add docstring
	Args:
		x:
		y:
		color (str):
		ax:
	"""
	levels_num = 10
	xmin, xmax = 0, 25
	ymin, ymax = 0, 2
	xx, yy = np.mgrid[xmin:xmax:100j, ymin:ymax:100j]
	positions = np.vstack([xx.ravel(), yy.ravel()])
	values = np.vstack([x, y])
	a = st.gaussian_kde(values)(positions).T
	z = np.reshape(a, xx.shape)
	m = np.amax(z)

	# form a step and levels
	step = (np.amax(a) - np.amin(a)) / levels_num
	# step = 0.01
	levels = np.arange(0, m, step) + step
	# convert HEX to HSL
	clr = Color(color)
	h, s, l = round(clr.hsl[0] * 360), round(clr.hsl[1] * 100, 1), round(clr.hsl[2] * 100, 1)
	# generate colors for contours level
	colors = [Color(hsl=(h / 360, s / 100, l_level / 100)).rgb for l_level in np.linspace(l, 95, len(levels))[::-1]]
	# plot filled contour
	cnt = ax.contourf(xx, yy, z, levels=levels, colors=colors, alpha=0.7, zorder=1)
	# change an edges of contours
	for c in cnt.collections:
		c.set_edgecolor("k")
		c.set_linewidth(0.2)


def joint_plot(X, Y, ax, gs, **kwargs):
	"""
	TODO: add docstring
	Args:
		X (np.ndarray):
		Y (np.ndarray):
		ax:
		gs:
		**kwargs:
	"""
	xmin, xmax = 0, 25
	ymin, ymax = 0, 2

	color = kwargs['color']

	ax.scatter(X, Y, marker="+", color=color, s=5, zorder=3, alpha=0.4)
	# create X-marginal (top)
	ax_top = plt.subplot(gs[0, 0], sharex=ax)
	ax_top.spines['top'].set_visible(False)
	ax_top.spines['right'].set_visible(False)
	# create Y-marginal (right)
	ax_right = plt.subplot(gs[1, 1], sharey=ax)
	ax_right.spines['top'].set_visible(False)
	ax_right.spines['right'].set_visible(False)
	# plot histogram top
	bin_val, bin_pos, _ = ax_top.hist(x=X, bins=np.arange(xmin, xmax + 1, 1),
	                                  weights=np.ones(len(X)) / len(X), color=color, alpha=0.0)
	bin_centers = 0.5 * (bin_pos[1:] + bin_pos[:-1])
	ax_top.plot(bin_centers, bin_val, color=kwargs['color'], linewidth=3)
	# plot histogram right
	bin_val, bin_pos, _ = ax_right.hist(x=Y, bins=np.arange(ymin, ymax + 0.05, 0.05),
	                                    weights=np.ones(len(Y)) / len(Y),
	                                    color=color, alpha=0.0, orientation="horizontal")
	bin_centers = 0.5 * (bin_pos[1:] + bin_pos[:-1])
	ax_right.plot(bin_val, bin_centers, color=color, linewidth=3)
	# set percentage ticklabels
	ax_top.yaxis.set_major_formatter(ticker.PercentFormatter(1))
	ax_right.xaxis.set_major_formatter(ticker.PercentFormatter(1))
	# add grid
	ax_top.grid(which='minor', axis='x')
	ax_right.grid(which='minor', axis='y')
	# gaussian_kde calculation
	# xx = np.linspace(xmin, xmax, 100)
	# yy = np.linspace(ymin, ymax, 100)
	# dx = st.gaussian_kde(X)(xx)
	# dy = st.gaussian_kde(Y)(yy)
	# ax_top.plot(x, dx, color=kwargs['color'])
	# ax_right.plot(dy, y, color=kwargs['color'])


def plot_3D_PCA(data_pack, names, save_to, corr_flag=False, contour_flag=False):
	"""
	TODO: add docstring
	Args:
		data_pack (list of tuple): special structure to easily work with (coords, color and label)
		names (list of str): datasets names
		save_to (str): save folder path
		corr_flag (bool): enable or disable corelation calculating
		contour_flag (bool): enable or disable egg plot
	"""
	light_filename = "_".join(names[0].split("_")[1:-1])

	def dat():
		if "Lat" in title and "Amp" in title:
			return coords[:, 0], coords[:, 1]
		if "Amp" in title and "Peak" in title:
			return coords[:, 1], coords[:, 2]
		if "Lat" in title and "Peak" in title:
			return coords[:, 0], coords[:, 2]

	# plot PCA at different point of view
	for elev, azim, title in (0, -90.1, "Lat Peak"), (0.1, 0.1, "Amp Peak"), (89.9, -90.1, "Lat Amp"):
		labels = []
		volume_sum = 0
		data_pack_xyz = []
		new_filename = f"{light_filename}_{title.lower().replace(' ', '_')}"
		# form labels
		if "Lat" in title:
			labels.append("Latency of slice")
		if "Amp" in title:
			labels.append("Area of amplitude")
		if "Peak" in title:
			labels.append("Number of exrema")

		# init 3D projection figure
		fig = plt.figure(figsize=(10, 10))
		ax = fig.add_subplot(111, projection='3d')
		# plot each data pack
		for coords, color, filename in data_pack:
			# create PCA instance and fit the model with coords
			pca = PCA(n_components=3)
			# coords is a matrix of coordinates, stacked as [[x1, y1, z1], ... , [xN, yN, zN]]
			pca.fit(coords)
			# get the center (mean value of points cloud)
			center = pca.mean_
			# get PCA vectors' head points (semi axis)
			vectors_points = [3 * np.sqrt(val) * vec for val, vec in zip(pca.explained_variance_, pca.components_)]
			vectors_points = np.array(vectors_points)
			# form full axis points (original vectors + mirrored vectors)
			axis_points = np.concatenate((vectors_points, -vectors_points), axis=0)
			# centering vectors and axis points
			vectors_points += center
			axis_points += center
			# calculate radii and rotation matrix based on axis points
			radii, rotation, matrixA = form_ellipse(axis_points)
			# choose -- calc correlaion or just plot PCA
			if corr_flag:
				# start calculus of points intersection
				volume = (4 / 3) * np.pi * radii[0] * radii[1] * radii[2]
				volume_sum += volume
				log.info(f"V: {volume}, {filename}")
				# keep ellipsoid surface dots, A matrix, center
				phi = np.linspace(0, np.pi, 200)
				theta = np.linspace(0, 2 * np.pi, 200)
				# cartesian coordinates that correspond to the spherical angles
				x = radii[0] * np.outer(np.cos(theta), np.sin(phi))
				y = radii[1] * np.outer(np.sin(theta), np.sin(phi))
				z = radii[2] * np.outer(np.ones_like(theta), np.cos(phi))
				# rotate accordingly
				for i in range(len(x)):
					for j in range(len(x)):
						x[i, j], y[i, j], z[i, j] = np.dot([x[i, j], y[i, j], z[i, j]], rotation) + center
				data_pack_xyz.append((matrixA, center, x.flatten(), y.flatten(), z.flatten()))
			# else:
			# plot PCA vectors
			for point_head in vectors_points:
				arrow = Arrow3D(*zip(center.T, point_head.T), mutation_scale=20, lw=3, arrowstyle="-|>", color=color)
				ax.add_artist(arrow)
			# plot cloud of points
			ax.scatter(*coords.T, alpha=0.2, s=30, color=color)
			# plot ellipsoid
			plot_ellipsoid(center, radii, rotation, plot_axes=False, color=color)

		if corr_flag:
			# collect all intersect point
			x1 = data_pack[0][0][:, 0]
			y1 = data_pack[0][0][:, 1]
			z1 = data_pack[0][0][:, 2]

			x2 = data_pack[1][0][:, 0]
			y2 = data_pack[1][0][:, 1]
			z2 = data_pack[1][0][:, 2]

			from analysis.ks3 import ks3

			d1 = np.stack((x1, y1, z1), axis=1)
			d2 = np.stack((x2, y2, z2), axis=1)

			D = ks3(d1, d2)
			print(f"K-S 3D: {D}")
			print("- " * 10)

			points_inside = []

			# get data of two ellipsoids: A matrix, center and points coordinates
			A1, C1, x1, y1, z1 = data_pack_xyz[0]
			A2, C2, x2, y2, z2 = data_pack_xyz[1]

			# based on stackoverflow.com/a/34385879/5891876 solution with own modernization
			# the equation for the surface of an ellipsoid is (x-c)TA(x-c)=1.
			# all we need to check is whether (x-c)TA(x-c) is less than 1 for each of points
			for coord in np.stack((x1, y1, z1), axis=1):
				if np.sum(np.dot(coord - C2, A2 * (coord - C2))) <= 1:
					points_inside.append(coord)
			# do the same for another ellipsoid
			for coord in np.stack((x2, y2, z2), axis=1):
				if np.sum(np.dot(coord - C1, A1 * (coord - C1))) <= 1:
					points_inside.append(coord)
			points_inside = np.array(points_inside)

			if not len(points_inside):
				log.info("NO INTERSECTIONS: 0 correlation")
				return

			# form convex hull of 3D surface
			hull = ConvexHull(points_inside)
			# get a volume of this surface
			v_intersection = hull.volume
			# calc correlation value
			pca_similarity = v_intersection / (volume_sum - v_intersection)
			log.info(f"PCA similarity: {pca_similarity}")
			# debugging plotting
			ax.scatter(*points_inside.T, alpha=0.2, s=1, color='r')
			# print(pca_similarity)
			print("- " * 10)
			# return
		# else:
		# figure properties
		ax.xaxis._axinfo['tick']['inward_factor'] = 0
		ax.yaxis._axinfo['tick']['inward_factor'] = 0
		ax.zaxis._axinfo['tick']['inward_factor'] = 0
		ax.set_xlabel("Latency of slice")
		ax.set_ylabel("Area of amplitude")
		ax.set_zlabel("Number of exrema")

		ax.tick_params(which='major', length=10, width=3, labelsize=20)
		ax.tick_params(which='minor', length=4, width=2, labelsize=20)

		# remove one of the plane ticks to make output pdf more readable
		if "Lat" not in title:
			# ax.set_xticks([])
			ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=len(ax.get_yticks()), integer=True))
			ax.zaxis.set_major_locator(ticker.MaxNLocator(nbins=len(ax.get_zticks()), integer=True))
		if "Amp" not in title:
			# ax.set_yticks([])
			ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=len(ax.get_xticks()), integer=True))
			ax.zaxis.set_major_locator(ticker.MaxNLocator(nbins=len(ax.get_zticks()), integer=True))
		if "Peak" not in title:
			# ax.set_zticks([])
			ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=len(ax.get_xticks()), integer=True))
			ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=len(ax.get_yticks()), integer=True))

		ax.view_init(elev=elev, azim=azim)
		fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
		bbox = fig.bbox_inches.from_bounds(1, 1, 8, 8)
		plt.show()
		plt.savefig(f"{save_to}/{new_filename}.pdf", bbox_inches=bbox, dpi=250, format="pdf")
		plt.savefig(f"{save_to}/{new_filename}.png", bbox_inches=bbox, dpi=250, format="png")
		plt.close(fig)


def plot_kde3d(data_pack):
	"""
	Draws 3D KDE
	Args:
		data_pack:
	"""
	from mayavi import mlab
	from tvtk.api import tvtk
	from scipy.interpolate import griddata
	from mayavi.mlab import contour3d, points3d
	x1 = data_pack[0][0][:, 0]
	y1 = data_pack[0][0][:, 1]
	z1 = data_pack[0][0][:, 2]
	x2 = data_pack[1][0][:, 0]
	y2 = data_pack[1][0][:, 1]
	z2 = data_pack[1][0][:, 2]
	distribution = np.transpose(np.stack((x1, y1, z1), axis=1))
	kde = st.gaussian_kde(distribution)
	density1 = kde(distribution)

	idx = density1.argsort()
	dx1 = distribution[0, idx]
	dy1 = distribution[1, idx]
	dz1 = distribution[2, idx]
	density1 = density1[idx]

	d = np.transpose(np.stack((x2, y2, z2), axis=1))
	kde = st.gaussian_kde(d)
	density2 = kde(d)

	idx = density2.argsort()
	dx2 = d[0, idx]
	dy2 = d[1, idx]
	dz2 = d[2, idx]
	density2 = density2[idx]

	# Create some test data, 3D gaussian, 200 points
	pts = 100j
	R1 = np.stack((dx1, dy1, dz1), axis=1)
	V1 = density1
	R2 = np.stack((dx2, dy2, dz2), axis=1)
	V2 = density2
	# Create the grid to interpolate on
	X1, Y1, Z1 = np.mgrid[min(dx1):max(dx1):pts, min(dy1):max(dy1):pts, min(dz1):max(dz1):pts]
	X2, Y2, Z2 = np.mgrid[min(dx2):max(dx2):pts, min(dy2):max(dy2):pts, min(dz2):max(dz2):pts]
	# Interpolate the data
	F1 = griddata(R1, V1, (X1, Y1, Z1))
	# points3d(x1, y1, z1)
	contour3d(F1, contours=6, opacity=0.3, colormap='Reds')
	F2 = griddata(R2, V2, (X2, Y2, Z2))
	# points3d(x2, y2, z2)
	contour3d(F2, contours=6, opacity=0.3, colormap='Greens')
	mlab.show()
