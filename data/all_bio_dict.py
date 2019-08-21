path = "/home/alex/Downloads/Bio files map - Sheet1.tsv"

from data.fig2hdf5 import fig2hdf5
from data.fig2hdf5 import fig2png

with open(path) as file:
	file.readline()
	types = []
	speeds = []
	muslces = []
	folders = []
	rats = []
	filenames = []
	begins = []
	ends = []

	curr_ty = ""
	curr_sp = ""
	curr_mu = ""
	curr_ra = ""

	for line in file.readlines():
		ty, sp, mu, ra, fi, be, en = line.replace("\n", "").split("\t")
		if ty:
			curr_ty = ty
		if sp:
			curr_sp = f"{sp}cms"
		if mu:
			curr_mu = f"{'flexor' if mu == 'FL' else 'extensor'}"
		if ra:
			curr_ra = ra

		folders.append("sliced")
		types.append(curr_ty)
		speeds.append(curr_sp)
		muslces.append(curr_mu)
		rats.append(curr_ra)
		filenames.append(fi)
		begins.append(be)
		ends.append(en)

	d = {}

	root = "/home/alex/GitHub/data/spinal"

	for t, m, s, f, r, fi, b, e in zip(types, muslces, speeds, folders, rats, filenames, begins, ends):
		filename = f"{root}/{t}/{m}/{s}/{f}/{r}/{fi}"
		if b == "-" or e == "-":
			t = f"rejected_{t}"
			b = "0"
			e = "0"
			continue

		title = f"{t} {m} {s} {f}"
		rat = fi

		if "(" in b:
			b = b.split("(")[0]
			e = e.split("(")[0]

		begin = int(b)
		end = int(e)
		# fig2png(filename, title, rat, begin, end)
		fig2hdf5(filename, title, rat, begin, end)
