import shutil
from pkg_resources import resource_filename
import os
import pylab
from spinal_cord.toolkit.data_miner import DataMiner


def clear_results():
    results_dir_filename = resource_filename('spinal_cord', 'results')
    if os.path.isdir(results_dir_filename):
        shutil.rmtree(results_dir_filename)
        os.mkdir(results_dir_filename)
    else:
        os.mkdir(results_dir_filename)


class ResultsPlotter:
    def __init__(self, rows_number, title):
        self.rows_number = rows_number
        self.cols_number = 1
        self.plot_index = 1
        pylab.figure()
        pylab.title(title)

    def show(self):
        pylab.show()

    def subplot(self, first, first_label: str, second, second_label: str, title: str):
        if self.plot_index > self.rows_number:
            raise ValueError("Too many subplots!")
        pylab.subplot(self.rows_number, self.cols_number, self.plot_index)
        self.plot_index += 1

        data = DataMiner.get_average_voltage(first)
        times = sorted(list(data.keys()))
        values = [data[time] for time in times]
        pylab.plot(
            times,
            values,
            'r.',
            label=first_label)
        data = DataMiner.get_average_voltage(second)
        times = sorted(list(data.keys()))
        values = [data[time] for time in times]
        pylab.plot(
            times,
            values,
            'b-.',
            label=second_label)

        pylab.ylabel(title)
        pylab.legend()
