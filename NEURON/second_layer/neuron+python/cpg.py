import logging
logging.basicConfig(level=logging.DEBUG)
import numpy as np
from neuron import h
h.load_file('nrngui.hoc')

#paralleling NEURON staff
pc = h.ParallelContext()
rank = int(pc.id())
nhost = int(pc.nhost())

#param
speed = 125 # duration of layer 25 = 21 cm/s; 50 = 15 cm/s; 125 = 6 cm/s
ees_fr = 40 # frequency of EES
versions = 1
step_number = 1 # number of steps
layers = 5  # default
extra_layers = 0 + layers
nMN = 200
nAff = 120
nInt = 196
N = 50
v = int(sys.argv[4])

exnclist = []
inhnclist = []
eesnclist = []
stimnclist = []

from interneuron import interneuron
from motoneuron import motoneuron
from bioaff import bioaff

import random

'''
network creation
see topology https://github.com/research-team/memristive-spinal-cord/blob/master/doc/diagram/cpg_generator_FE_paper.png
and all will be clear
'''
class CPG:
    def __init__(self, speed, ees_fr, inh_p, step_number, layers, extra_layers, N):

        self.interneurons = []
        self.motoneurons = []
        self.afferents = []
        self.stims = []
        self.ncell = N
        self.groups = []
        self.motogroups = []
        self.affgroups = []
        self.IP_E = []
        self.IP_F = []

        for layer in range(layers):
            self.dict_0 = {layer: "OM{}_0".format(layer + 1)}
            self.dict_1 = {layer: "OM{}_1".format(layer + 1)}
            self.dict_2E = {layer: "OM{}_2E".format(layer + 1)}
            self.dict_2F = {layer: "OM{}_2F".format(layer + 1)}
            self.dict_3 = {layer: "OM{}_3".format(layer + 1)}
            self.dict_C = {layer: "C{}".format(layer + 1)}

        for layer in range(layers + 1):
            self.dict_CV = {layer: "CV{}".format(layer + 1)}
            self.dict_CV_1 = {layer: "CV{}_1".format(layer + 1)}
            self.dict_IP_E = {layer: "IP{}_E".format(layer + 1)}
            self.dict_IP_F = {layer: "IP{}_F".format(layer + 1)}

        for layer in range(layers, extra_layers):
            self.dict_0 = {layer: "OM{}_0".format(layer + 1)}
            self.dict_1 = {layer: "OM{}_1".format(layer + 1)}
            self.dict_2E = {layer: "OM{}_2E".format(layer + 1)}
            self.dict_2F = {layer: "OM{}_2F".format(layer + 1)}
            self.dict_3 = {layer: "OM{}_3".format(layer + 1)}
            self.dict_C = {layer: "C{}".format(layer + 1)}

        self.OM1_0E = self.addpool(self.ncell, "OM1_0E", "int")
        self.OM1_0F = self.addpool(self.ncell, "OM1_0F", "int")

        '''addpool'''
        for layer in range(layers):
            self.dict_0[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_0", "int")
            self.dict_1[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_1", "int")
            self.dict_2E[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2E", "int")
            self.dict_2F[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2F", "int")
            self.dict_3[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_3", "int")

        for layer in range(layers + 1):
            self.dict_CV[layer] = self.addpool(self.ncell, "CV" + str(layer + 1), "aff")
            self.dict_CV_1[layer] = self.addpool(self.ncell, "CV" + str(layer + 1) + "_1", "aff")

            '''interneuronal pool'''
            self.dict_IP_E[layer] = self.addpool(self.ncell, "IP" + str(layer + 1) + "_E", "int")
            self.dict_IP_F[layer] = self.addpool(self.ncell, "IP" + str(layer + 1) + "_F", "int")
            self.IP_E.append(self.dict_IP_E[layer])
            self.IP_F.append(self.dict_IP_F[layer])

        for layer in range(layers, extra_layers):
            self.dict_0[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_0", "int")
            self.dict_1[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_1", "int")
            self.dict_2E[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2E", "int")
            self.dict_2F[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2F", "int")
            self.dict_3[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_3", "int")

        self.IP_E = sum(self.IP_E, [])
        self.IP_F = sum(self.IP_F, [])

        self.sens_aff = self.addpool(nAff, "sens_aff", "aff")
        self.Ia_aff_E = self.addpool(nAff, "Ia_aff_E", "aff")
        self.Ia_aff_F = self.addpool(nAff, "Ia_aff_F", "aff")

        self.mns_E = self.addpool(nMN, "mns_E", "moto")
        self.mns_F = self.addpool(nMN, "mns_F", "moto")

        '''reflex arc'''
        self.Ia_E = self.addpool(nInt, "Ia_E", "int")
        self.iIP_E = self.addpool(nInt, "iIP_E", "int")
        self.R_E = self.addpool(nInt, "R_E", "int")

        self.Ia_F = self.addpool(nInt, "Ia_F", "int")
        self.iIP_F = self.addpool(nInt, "iIP_F", "int")
        self.R_F = self.addpool(nInt, "R_F", "int")
        # self.Iagener_E = []
        # self.Iagener_F = []

        '''ees'''
        self.ees = self.addgener(1, ees_fr, 10000, False)

        '''skin inputs'''
        cfr = 200
        c_int = 1000 / cfr

        for layer in range(layers+1):
            self.dict_C[layer] = []
            for i in range(step_number):
                self.dict_C[layer].append(self.addgener(speed * (layer + 1) + i * (speed * (layers + 1) + 125), random.gauss(cfr, cfr/10), speed / c_int))

        for layer in range(layers, extra_layers):
            self.dict_C[layer] = []
            for i in range(step_number):
                self.dict_C[layer].append(self.addgener(speed * (layer - 5) + 3 + i * (speed * 7 + 125), random.gauss(cfr, cfr/10), speed / c_int))

        self.C_1 = []
        self.C_0 = []

        # for i in range(step_number):
        #     self.Iagener_E.append(self.addIagener((1 + i * (speed * 6 + 125)), self.ncell, speed))
        # for i in range(step_number):
        #     self.Iagener_F.append(self.addIagener((speed * 6 + i * (speed * 6 + 125)), self.ncell, 25))
        for i in range(step_number):
            self.C_0.append(self.addgener(speed * 7 + i * (speed * 7 + 125), cfr, (125/c_int), False))

        self.C_0.append(self.addgener(3, cfr, speed / c_int))

        for layer in range(layers+1):
            self.C_1.append(self.dict_CV_1[layer])
        self.C_1 = sum(self.C_1, [])

        # self.Iagener_E = sum(self.Iagener_E, [])
        # self.Iagener_F = sum(self.Iagener_F, [])

        '''generators'''
        createmotif(self.OM1_0E, self.dict_1[0], self.dict_2E[0], self.dict_3[0])
        for layer in range(1, layers):
            createmotif(self.dict_0[layer], self.dict_1[layer], self.dict_2E[layer], self.dict_3[layer])

        for layer in range(layers, extra_layers):
            createmotif(self.dict_0[layer], self.dict_1[layer], self.dict_2E[layer], self.dict_3[layer])

        '''extra flexor connections'''
        for layer in range(1, layers):
            connectcells(self.dict_2F[layer - 1], self.dict_2F[layer], 0.01, 2)

        for layer in range(layers, extra_layers):
            connectcells(self.dict_2F[layer - 1], self.dict_2F[layer], 0.01, 2)

        for layer in range(layers):
            connectcells(self.dict_1[layer], self.dict_2F[layer], 0.05, 3)
            connectcells(self.dict_2F[layer], self.dict_1[layer], 0.05, 4)

        for layer in range(layers, extra_layers):
            connectcells(self.dict_1[layer], self.dict_2F[layer], 0.05, 2)
            connectcells(self.dict_2F[layer], self.dict_1[layer], 0.05, 4)

        connectcells(self.dict_CV[0], self.OM1_0F, 0.001, 3)
        connectcells(self.OM1_0F, self.dict_1[0], 0.05, 2)

        '''between delays vself.Ia excitatory pools'''
        '''extensor'''
        for layer in range(1, layers):
            connectcells(self.dict_CV[layer - 1], self.dict_CV[layer], 0.5, 2)

        connectcells(self.dict_CV[0], self.OM1_0E, 0.0002, 2)
        for layer in range(1, layers):
            connectcells(self.dict_CV[layer], self.dict_0[layer], 0.0004, 2)

        '''inhibitory projections'''
        '''extensor'''
        for layer in range(2, layers):
            if layer > 3:
                for i in range(layer - 2):
                    connectcells(self.dict_CV_1[layer], self.dict_3[i], 0.5, 1)
            else:
                for i in range(layer - 1):
                    connectcells(self.dict_CV_1[layer], self.dict_3[i], 0.5, 1)

        genconnect(self.ees, self.Ia_aff_E, 0.1, 2)
        genconnect(self.ees, self.Ia_aff_F, 0.1, 2)
        genconnect(self.ees, self.dict_CV[0], 0.5, 2)

        connectcells(self.Ia_aff_E, self.mns_E, 0.12, 1)
        connectcells(self.Ia_aff_F, self.mns_F, 0.12, 1)

        '''IP'''
        for layer in range(2, 4):
            connectcells(self.dict_IP_E[layer - 1], self.dict_IP_E[layer], layer*0.005, 2)
            connectcells(self.dict_IP_F[layer - 1], self.dict_IP_F[layer], layer*0.01, 2)
        for layer in range(layers):
            '''Extensor'''
            connectcells(self.dict_1[layer], self.dict_IP_E[layer], 0.3, 3)
            connectcells(self.dict_2E[layer], self.dict_IP_E[layer], 0.3, 2)
            connectcells(self.dict_IP_E[layer], self.mns_E, 0.3, 2)
            if layer > 2:
                connectcells(self.dict_IP_E[layer], self.Ia_aff_E, layer*0.001, 1, True)
            else:
                connectcells(self.dict_IP_E[layer], self.Ia_aff_E, 0.0002, 1, True)
            if layer > 2:
                '''Flexor'''
                connectcells(self.dict_1[layer], self.dict_IP_F[layer], 0.3, 2)
                connectcells(self.dict_2F[layer], self.dict_IP_F[layer], 0.3, 2)
                connectcells(self.dict_IP_F[layer], self.mns_F, 0.3, 2)
            else:
                connectcells(self.dict_1[layer], self.dict_IP_F[layer], 0.1, 2)
                connectcells(self.dict_2F[layer], self.dict_IP_F[layer], 0.1, 2)
                connectcells(self.dict_IP_F[layer], self.mns_F, 0.2, 2)

        for layer in range(layers+1): 
            '''skin inputs'''
            connectcells(self.dict_C[layer], self.dict_CV_1[layer], 0.05, 1)

        connectcells(self.IP_F, self.Ia_aff_F, 0.0001, 2, True)

        '''C'''

        '''C1'''
        connectcells(self.dict_CV_1[0], self.OM1_0E, 0.0002, 1)
        connectcells(self.dict_CV_1[0], self.dict_0[1], 0.00005, 2)
        connectcells(self.dict_CV_1[0], self.dict_0[2], 0.00005, 2)
        connectcells(self.dict_CV_1[0], self.dict_0[3], 0.00001, 2)

        '''C2'''
        connectcells(self.dict_CV_1[1], self.OM1_0E, 0.0003, 1)
        connectcells(self.dict_CV_1[1], self.dict_0[1], 0.0004, 2)
        connectcells(self.dict_CV_1[1], self.dict_0[2], 0.0002, 2)
        connectcells(self.dict_CV_1[1], self.dict_0[3], 0.00005, 2)
        connectcells(self.dict_CV_1[1], self.dict_0[4], 0.00001, 2)

        '''C3'''
        connectcells(self.dict_CV_1[2], self.OM1_0E, 0.00005, 3)
        connectcells(self.dict_CV_1[2], self.dict_0[1], 0.0004, 3)
        connectcells(self.dict_CV_1[2], self.dict_0[2], 0.0006, 3)
        connectcells(self.dict_CV_1[2], self.dict_0[3], 0.0002, 3)
        connectcells(self.dict_CV_1[2], self.dict_0[4], 0.0001, 3)

        '''C4'''
        connectcells(self.dict_CV_1[3], self.dict_0[2], 0.0003, 3)
        connectcells(self.dict_CV_1[3], self.dict_0[3], 0.0004, 3)
        connectcells(self.dict_CV_1[4], self.dict_0[2], 0.0003, 3)
        connectcells(self.dict_CV_1[4], self.dict_0[3], 0.0004, 3)
        connectcells(self.dict_CV_1[3], self.dict_0[4], 0.0001, 2)
        connectcells(self.dict_CV_1[4], self.dict_0[4], 0.0001, 2)

        '''C5'''
        connectcells(self.dict_CV_1[5], self.dict_0[4], 0.0002, 3)
        connectcells(self.dict_CV_1[5], self.dict_0[3], 0.00001, 3)

        '''C=1 Extensor'''
        connectcells(self.IP_E, self.iIP_E, 0.8, 1)

        for layer in range(layers):
            connectcells(self.dict_CV_1[layer], self.iIP_E, 0.8, 1)

        connectcells(self.iIP_E, self.OM1_0F, 0.99, 1, True)

        for layer in range(layers - 1):
            connectcells(self.iIP_E, self.dict_2F[layer], 0.99, 1, True)

        connectcells(self.iIP_E, self.IP_F, 0.99, 1, True)
        connectcells(self.iIP_E, self.Ia_aff_F, 0.99, 1, True)
        connectcells(self.iIP_E, self.mns_F, 0.99, 1, True)

        '''C=0 Flexor'''
        connectcells(self.iIP_F, self.IP_E, 0.99, 1, True)
        connectcells(self.iIP_F, self.iIP_E, 0.99, 1, True)
        connectcells(self.C_0, self.Ia_aff_E, 0.09, 1, True)
        connectcells(self.C_0, self.IP_E, 0.99, 1, True)
        connectcells(self.C_0, self.iIP_F, 0.5, 1)

        '''reflex arc'''
        connectcells(self.iIP_E, self.Ia_E, 0.5, 1)
        connectcells(self.Ia_aff_E, self.Ia_E, 0.8, 1)
        connectcells(self.mns_E, self.R_E, 0.00025, 1)
        connectcells(self.Ia_E, self.mns_F, 0.08, 1, True)
        connectcells(self.R_E, self.mns_E, 0.005, 1, True)
        connectcells(self.R_E, self.Ia_E, 0.001, 1, True)

        connectcells(self.iIP_F, self.Ia_F, 0.5, 1)
        connectcells(self.Ia_aff_F, self.Ia_F, 0.8, 1)
        connectcells(self.mns_F, self.R_F, 0.0004, 1)
        connectcells(self.Ia_F, self.mns_E, 0.04, 1, True)
        # connectcells(self.R_F, self.mns_F, 0.005, 1, True)
        connectcells(self.R_F, self.Ia_F, 0.001, 1, True)

        connectcells(self.R_E, self.R_F, 0.04, 1, True)
        connectcells(self.R_F, self.R_E, 0.04, 1, True)
        connectcells(self.Ia_E, self.Ia_F, 0.08, 1, True)
        connectcells(self.Ia_F, self.Ia_E, 0.08, 1, True)
        connectcells(self.iIP_E, self.iIP_F, 0.04, 1, True)
        connectcells(self.iIP_F, self.iIP_E, 0.04, 1, True)

    def addpool(self, num, name="test", neurontype="int"):
        '''
        Creates interneuronal pool and returns gids of pool
        Parameters
        ----------
        num: int
            neurons number in pool
        neurontype: string
            int: interneuron 
            delay: interneuron with 5ht
            moto: motoneuron
            aff: afferent
        Returns
        -------
        gids: list
            the list of neurons gids
        '''
        gids = []
        gid = 0
        if neurontype.lower() == "delay":
            delaytype = True
        else:
            delaytype = False
        if neurontype.lower() == "moto":
            diams = motodiams(num)
        for i in range(rank, num, nhost):
            if neurontype.lower() == "moto":
                cell = motoneuron(diams[i])
                self.motoneurons.append(cell)
            elif neurontype.lower() == "aff":
                cell = bioaff(random.randint(2, 10))
                self.afferents.append(cell)
            else:
                cell = interneuron(delaytype)
                self.interneurons.append(cell)
            while pc.gid_exists(gid) != 0:
                gid += 1
            gids.append(gid)
            pc.set_gid2node(gid, rank)
            nc = cell.connect2target(None)
            pc.cell(gid, nc)

        # ToDo remove me (Alex code) - NO
        if neurontype.lower() == "moto":
            self.motogroups.append((gids, name))
        elif neurontype.lower() == "aff":
            self.affgroups.append((gids, name))
        else:
            self.groups.append((gids, name))

        return gids

    def addgener(self, start, freq, nums, r=True):
        '''
        Creates generator and returns generator gid
        Parameters
        ----------
        start: int
            generator start up
        freq: int
            generator frequency
        nums: int
            signals number
        Returns
        -------
        gid: int
            generator gid
        '''
        gid = 0
        stim = h.NetStim()
        stim.number = nums
        if r:
            stim.start = random.uniform(start - 5, start + 5)
            stim.noise = 0.2
        else:
            stim.start = start
        stim.interval = 1000 / freq
        #skinstim.noise = 0.1
        self.stims.append(stim)
        while pc.gid_exists(gid) != 0:
            gid += 1
        pc.set_gid2node(gid, rank)
        ncstim = h.NetCon(stim, None)
        pc.cell(gid, ncstim)
        return gid

    def addIagener(self, start, num, speed):
        '''
        Creates self.Ia generators and returns generator gids
        Parameters
        ----------
        start: int
            generator start up
        num: int
            number in pool
        Returns
        -------
        gids: list
            generators gids
        '''
        gids = []
        gid = 0
        for i in range(rank, num, nhost):
            stim = h.SpikeGenerator(0.5)
            stim.start = start
            stim.number = 1000000
            stim.speed = speed * 6
            stim.k = 3 / stim.speed
            self.stims.append(stim)
            while pc.gid_exists(gid) != 0:
                gid += 1
            gids.append(gid)
            pc.set_gid2node(gid, rank)
            ncstim = h.NetCon(stim, None)
            pc.cell(gid, ncstim)

        return gids

def connectcells(pre, post, weight, delay, inhtype = False):
    ''' Connects with excitatory synapses
      Parameters
      ----------
      pre: list
          list of presynase neurons gids
      post: list
          list of postsynapse neurons gids
      weight: float
          weight of synapse
          used with Gaussself.Ian distribution
      delay: int
          synaptic delay
          used with Gaussself.Ian distribution
      nsyn: int
          numder of synapses
      inhtype: bool
          is this connection inhibitory?
    '''
    nsyn = random.randint(N/2, N)
    for i in post:
        if pc.gid_exists(i):
            for j in range(nsyn):
                srcgid = random.randint(pre[0], pre[-1])
                target = pc.gid2cell(i)
                if inhtype:
                    syn = target.synlistinh[j]
                    nc = pc.gid_connect(srcgid, syn)
                    inhnclist.append(nc)
                    # str nc.weight[0] = 0
                else:
                    syn = target.synlistex[j]
                    nc = pc.gid_connect(srcgid, syn)
                    exnclist.append(nc)
                    # str nc.weight[0] = random.gauss(weight, weight / 10)
                nc.weight[0] = random.gauss(weight, weight / 10)
                nc.delay = random.gauss(delay, delay / 5)


def genconnect(gen_gid, afferents_gids, weight, delay, inhtype = False):
    ''' Connects with generator
      Parameters
      ----------
      afferents_gids: list
          list of presynase neurons gids
      gen_gid: int
          generator gid
      weight: float
          weight of synapse
          used with Gaussian distribution
      delay: int
          synaptic delay
          used with Gaussian distribution
      nsyn: int
          numder of synapses
      inhtype: bool
          is this connection inhibitory?
    '''
    nsyn = random.randint(N/2, N)
    for i in afferents_gids:
        if pc.gid_exists(i):
            for j in range(nsyn):
                target = pc.gid2cell(i)
                if inhtype:
                    syn = target.synlistinh[j]
                else:
                    syn = target.synlistees[j]
                nc = pc.gid_connect(gen_gid, syn)
                stimnclist.append(nc)
                nc.delay = random.gauss(delay, delay / 5)
                nc.weight[0] = random.gauss(weight, weight / 10)

def createmotif(OM0, OM1, OM2, OM3):
    ''' Connects motif module
      see https://github.cself.OM/research-team/memristive-spinal-cord/blob/master/doc/dself.Iagram/cpg_generatoself.R_FE_paper.png
      Parameters
      ----------
      self.OM0: list
          list of self.OM0 pool gids
      self.OM1: list
          list of self.OM1 pool gids
      self.OM2: list
          list of self.OM2 pool gids
      self.OM3: list
          list of self.OM3 pool gids
    '''
    connectcells(OM0, OM1, 0.05, 2)
    connectcells(OM1, OM2, 0.05, 3)
    connectcells(OM2, OM1, 0.05, 4)
    connectcells(OM2, OM3, 0.0008, 1)
    connectcells(OM3, OM2, 0.09, 1, True)
    connectcells(OM3, OM1, 0.09, 1, True)


def spike_record(pool, version):
    ''' Records spikes from gids
      Parameters
      ----------
      pool: list
        list of neurons gids
      version: int
          test number
      Returns
      -------
      v_vec: list of h.Vector()
          recorded voltage
    '''
    v_vec = []

    for i in pool:
        cell = pc.gid2cell(i)
        vec = h.Vector()
        vec.record(cell.soma(0.5)._ref_vext[0])
        v_vec.append(vec)
    return v_vec

def motodiams(number):
    nrn_number = number
    standby_percent = 70
    active_percent = 100 - standby_percent

    standby_size = int(nrn_number * standby_percent / 100)
    active_size = nrn_number - standby_size

    loc_active, scale_active = 27, 3
    loc_stanby, scale_stanby = 44, 4

    x2 = np.concatenate([np.random.normal(loc=loc_active, scale=scale_active, size=active_size),
                     np.random.normal(loc=loc_stanby, scale=scale_stanby, size=standby_size)])

    return x2


def avgarr(z):
    ''' Summarizes extracellular voltage in pool
      Parameters
      ----------
      z: list
        list of neurons voltage
      Returns
      -------
      summa: list
          list of summarized voltage
    '''
    summa = 0
    for item in z:
        summa += np.array(item)
    return summa


def spikeout(pool, name, version, v_vec):
    ''' Reports simulation results
      Parameters
      ----------
      pool: list
        list of neurons gids
      name: string
        pool name
      version: int
          test number
      v_vec: list of h.Vector()
          recorded voltage
    '''
    global rank
    pc.barrier()
    for i in range(nhost):
        if i == rank:
            outavg = []
            for j in range(len(pool)):
                outavg.append(list(v_vec[j]))
            outavg = avgarr(outavg)
            path = str('./res/' + name + 'r%dv%d_foot_25tests_15speed' % (rank, v))
            f = open(path, 'w')
            for v in outavg:
                f.write(str(v) + "\n")
        pc.barrier()


def prun(speed, step_number):
    ''' simulation control
    Parameters
    ----------
    speed: int
      duration of each layer
    '''
    tstop = (7 * speed + 125) * step_number
    pc.set_maxstep(10)
    h.stdinit()
    pc.psolve(tstop)


def finish():
    ''' proper exit '''
    pc.runworker()
    pc.done()
    # print("hi after finish")
    h.quit()

if __name__ == '__main__':
    '''
    cpg_ex: cpg
        topology of central pattern generation + reflex arc 
    '''
    k_nrns = 0
    k_name = 1

    for i in range(versions):
        cpg_ex = CPG(speed, ees_fr, 100, step_number, layers, extra_layers, N)
        motorecorders = []
        for group in cpg_ex.motogroups:
            motorecorders.append(spike_record(group[k_nrns], i))
        # affrecorders = []
        # for group in cpg_ex.affgroups:
        #   affrecorders.append(spike_record(group[k_nrns], i))
        # recorders = []
        # for group in cpg_ex.groups:
        #   recorders.append(spike_record(group[k_nrns], i))

        print("- " * 10, "\nstart")
        prun(speed, step_number)
        print("- " * 10, "\nend")

        for group, recorder in zip(cpg_ex.motogroups, motorecorders):
            spikeout(group[k_nrns], group[k_name], i, recorder)
        # for group, recorder in zip(cpg_ex.affgroups, affrecorders):
        #   spikeout(group[k_nrns], group[k_name], i, recorder)
        # for group, recorder in zip(cpg_ex.groups, recorders):
        #   spikeout(group[k_nrns], group[k_name], i, recorder)
    finish()