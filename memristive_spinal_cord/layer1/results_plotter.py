import pylab as pylab


class ResultsPlotter:

    @staticmethod
    def show():
        """
        Just shows a figure
        Returns:
            None
        """
        pylab.show(dpi=300)

    def __init__(self, rows_number, title):
        """
        Args:
            rows_number: total rows at the figure
            title: title for the whole image?
            # TODO The title doesn't seen on the picture. Check if this parameter does nothing
        """
        self._rows_number = rows_number
        self._cols_number = 1
        self._plot_index = 1
        self._title = title

    def reset(self):
        """
        Resets pylab settings to a default state
        Returns:
            None
        """
        pylab.figure() # creates a new figure
        pylab.title(self._title) # sets the title

    def subplot(self, flexor, extensor, title):
        """
        Plots one figure at corresponding position. The method will be called several times
        Args:
            flexor: data from simulated flexor muscle
            extensor: data from simyulated extensor muscle
            title: just a title
        Returns:
            None
        """
        if self._plot_index > self._rows_number:
            raise ValueError("Too many subplots!")
        pylab.subplot(self._rows_number, self._cols_number, self._plot_index)
        self._plot_index += 1

        pylab.plot(flexor.keys(), flexor.values(), 'r.', label='flexor')
        pylab.plot(extensor.keys(), extensor.values(), 'b-.', label='extensor')

        pylab.ylabel(title)
        pylab.legend()
