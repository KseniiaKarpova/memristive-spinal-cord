import logging
import numpy as np
import pylab as plt


logging.basicConfig(format='[%(funcName)s]: %(message)s', level=logging.INFO)
logger = logging.getLogger()

percents = [25, 50, 75]

def calc_boxplots(dots):
  low_box_Q1, median, high_box_Q3 = np.percentile(dots, percents)
  # calc borders
  IQR = high_box_Q3 - low_box_Q1
  Q1_15 = low_box_Q1 - 1.5 * IQR
  Q3_15 = high_box_Q3 + 1.5 * IQR

  high_whisker, low_whisker = high_box_Q3, low_box_Q1,

  for dot in dots:
    if high_box_Q3 < dot <= Q3_15 and dot > high_whisker:
      high_whisker = dot
    if Q1_15 <= dot < low_box_Q1 and dot < low_whisker:
      low_whisker = dot

  high_flier, low_flier = high_whisker, low_whisker
  for dot in dots:
    if dot > Q3_15 and dot > high_flier:
      high_flier = dot

    if dot < Q1_15 and dot < low_flier:
      low_flier = dot

  return median, high_box_Q3, low_box_Q1, high_whisker, low_whisker, high_flier, low_flier


def plot_shadows_boxplot(data_per_test, ees_hz, step, save_folder, filename, debugging=False):
	"""
	Plot shadows (and/or save) based on the input data
	Args:
		data_per_test (np.ndarray of np.ndarray): data per test with list of dots
		ees_hz (int): EES value
		step (float): step size of the data for human-read normalization time
		save_folder (str): saving folder path
		filename (str): filename
		debugging (bool): show debug info
	Returns:
		kawai pictures =(^-^)=
	"""
	print('work')
	# stuff variables
	slice_length_ms = int(1 / ees_hz * 1000)
	slices_number = int(len(data_per_test[0]) / slice_length_ms * step)
	steps_in_slice = int(slice_length_ms / step)
	# tests dots at each time -> N (test number) dots at each time
	splitted = np.split(np.array([calc_boxplots(dot) for dot in data_per_test.T]), slices_number)

	# build plot
	yticks = []
	shared_x = np.arange(steps_in_slice) * step

	fig, ax = plt.subplots(figsize=(16, 9))

	for i, data in enumerate(splitted):
		data += i * 6
		ax.fill_between(shared_x, data[:, 6], data[:, 5], alpha=0.1, color='r')  # 6 f_low, 5 f_high
		ax.fill_between(shared_x, data[:, 4], data[:, 3], alpha=0.3, color='r')  # 4 w_low, 3 w_high
		ax.fill_between(shared_x, data[:, 2], data[:, 1], alpha=0.6, color='r')  # 2 b_low, 1 b_high
		ax.plot(shared_x, data[:, 0], color='k', linewidth=0.7)  # 0 med
		yticks.append(data[0, 0])

	# plotting stuff
	ax.set_xlim(0, slice_length_ms)
	ax.set_xticks(range(slice_length_ms + 1))
	ax.set_xticklabels(range(slice_length_ms + 1))
	ax.set_yticks(yticks)
	ax.set_yticklabels(range(1, slices_number + 1))
	fig.subplots_adjust(left=0.04, bottom=0.05, right=0.99, top=0.99)
	fig.savefig(f"{save_folder}/shadow_{filename}.png", dpi=250, format="png")

	if debugging:
		plt.show()

	plt.close()

	logging.info(f"saved file in {save_folder}")
