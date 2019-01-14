import os
import pylab
import numpy as np
import h5py as hdf5
from collections import defaultdict
from analysis.functions import read_bio_data, normalization


def __read_data(filepath):
	"""
	Read all data from hdf5 file
	Args:
		filepath (str):
			path to the file
	Returns:
		dict[str, list]: voltage data for each test
	"""
	data_by_test = {}
	with hdf5.File(filepath) as file:
		for test_name, test_values in file.items():
			data_by_test[test_name] = test_values[:]  # [:] will return ndarray, don't use list() !!!
	return data_by_test


def __restructure_data(original_data, sim_step):
	"""
	Restructuring data from test -> slices to slices -> test
	Args:
		original_data (dict[str, list]):
			data container of voltages for each test
	Returns:
		dict[int, dict[str, list]]: restuctured data for easiest way to build the shadows.
		slice index -> [test name -> test values which are corresponed to the current slice ]
	"""
	# constant
	slice_duration = 25
	# i = 0
	# for k, v in original_data.items():
	# 	first = -v[0]
	# 	# transforming to extracellular form
	# 	original_data[k] = [-d - first for d in v]
	# 	# if i % 5 == 0:
	# 		# pylab.plot(original_data[k])
	# 	i += 1
	# pylab.show()
	# get simulation time by len of records and multiplication by simulation step
	sim_time = len(next(iter(original_data.values()))) * sim_step   # + 0.1  # for nest
	# get number of slices by floor division of slice duration (25 ms)
	num_slices = int(sim_time) // slice_duration
	# get normlization coefficient from slice duration and simulation step
	normalized_time_from_index = int(slice_duration / sim_step)
	# generate dict container
	voltages_by_slice = {slice_index: defaultdict(list) for slice_index in range(num_slices)}
	# relocate voltage data by their test and slice affiliation
	print(len(voltages_by_slice))
	for test_name, test_values in original_data.items():
		for index, voltage in enumerate(test_values):
			# get index of the slice by floor division of normalize to 1 ms time
			slice_index = index // normalized_time_from_index
			# collect current voltage to the affiliated test name and slice number
			voltages_by_slice[slice_index][test_name].append(voltage)
	return voltages_by_slice


def __plot(slices, sim_step, raw_data_filename, save_path=None):
	"""
	Plot shadows with mean
	Args:
		slices (dict[int, dict[str, list]]):
			restructured data: dict[slice index, dict[test name, voltages]]
		sim_step (float):
			simulation step
		raw_data_filename (str):
			path to the raw data
		save_path (str or None):
			folder path for saving results
	"""
	# bio_data = read_bio_data('../bio-data/3_1.31 volts-Rat-16_5-09-2017_RMG_9m-min_one_step.txt')[0]
	# bio_indexes = read_bio_data('../bio-data/3_1.31 volts-Rat-16_5-09-2017_RMG_9m-min_one_step.txt')[1]
	# bio_data = normalization(bio_data, zero_relative=True)
	# print("bio_data = ", len(bio_data))
	# print(bio_indexes)
	bio_data_list = []
	offset = 0
	for sl in range(12):
		print("sl = ", sl)
		print("offset = ", offset)
		bio_data_list_tmp = []
		# for index in range(offset, bio_indexes[sl + 1]):
			# bio_data_list_tmp.append(bio_data[index])
		bio_data_list.append(bio_data_list_tmp)
		# offset = bio_indexes[sl + 1]
	print("bio_data_list = ", len(bio_data_list))
	yticks = []
	pylab.figure(figsize=(10, 5))
	times_bio = []
	offset_bio = 0
	for index, sl in enumerate(range(len(bio_data_list))):
		times_bio_tmp = []
		for i in range(offset_bio, offset_bio + len(bio_data_list[sl])):
			times_bio_tmp.append(i * 10)
		offset_bio += len(bio_data_list[sl])
		times_bio.append(times_bio_tmp)
	times_for_bio = []
	for sl in range(len(times_bio)):
		times_for_bio_tmp = []
		for i in range(len(times_bio[sl])):
			times_for_bio_tmp.append(i * 10)
		times_for_bio.append(times_for_bio_tmp)
	for index, sl in enumerate(range(len(bio_data_list))):
		offset = index * 0.5
	for slice_number, tests in slices.items():
		offset = slice_number * 0.5
		for k, v in tests.items():
			tests[k] = normalization(v, zero_relative=True)

		mean_data = list(map(lambda elements: np.mean(elements), zip(*tests.values())))  #
		print("mean_data = ", mean_data)
		times = [time * sim_step for time in range(len(mean_data))]  # divide by 10 to convert to ms step
		means = [voltage + offset for voltage in mean_data]
		yticks.append(means[0])
		minimal_per_step = [min(a) for a in zip(*tests.values())]
		maximal_per_step = [max(a) for a in zip(*tests.values())]
		# plot mean with shadows
		pylab.plot(times, means, linewidth=0.5, color='k')
		pylab.fill_between(times,
		                   [mini + offset for mini in minimal_per_step],  # the minimal values + offset (slice number)
		                   [maxi + offset for maxi in maximal_per_step],  # the maximal values + offset (slice number)
		                   alpha=0.35)
	for index, sl in enumerate(range(len(bio_data_list))):
		offset = index * 0.5
		pylab.plot([t * 0.25 for t in range(len(bio_data_list[sl]))], [data + offset for data in bio_data_list[sl]],
		           color='r', linewidth=0.8)
	pylab.xticks(range(26), [i if i % 1 == 0 else "" for i in range(26)], fontsize=14)
	pylab.yticks(yticks, range(1, len(slices) + 1), fontsize=14)
	pylab.xlim(0, 25)
	pylab.grid(which='major', axis='x', linestyle='--', linewidth=0.5)
	pylab.show()
	# if the save path is not specified
	if not save_path:
		save_path = "/".join(raw_data_filename.split("/")[:-1])
	pylab.savefig(os.path.join(save_path, "shadows.png"), format="png", dpi=512)


def plot_shadows(raw_data_filename, sim_step, save_path=None):
	data = __read_data(raw_data_filename)
	slices, sim_time = __restructure_data(data, sim_step=sim_step)
	__plot(slices, sim_step, raw_data_filename, save_path)


def debugging():
	path = '../../neuron-data/15cm.hdf5'
	# add info about simulation step. Neuron is 0.025ms, NEST is 0.1ms
	sim_step = 0.025    # don't forget to change the step size!

	data = __read_data(path)
	slices = __restructure_data(data, sim_step=sim_step)
	__plot(slices, sim_step, path)


if __name__ == "__main__":
	debugging()
