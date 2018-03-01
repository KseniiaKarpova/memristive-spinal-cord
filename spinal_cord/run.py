import nest
from spinal_cord.level1 import Level1
from spinal_cord.level2 import Level2
from spinal_cord.toolkit.plotter import clear_results


clear_results()
nest.SetKernelStatus({
    'total_num_virtual_procs': 8,
    'print_time': True,
    'resolution': 0.1
})
nest.Install('research_team_models')
level1 = Level1()
level2 = Level2(level1)

nest.Simulate(5000.)
level1.plot_afferents()
level1.plot_motogroups()
level2.plot_pool()
level2.plot_pc()
