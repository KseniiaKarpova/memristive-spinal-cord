from neucogar.SynapseModel import SynapseModel
from memristive_spinal_cord.layer2.parameters import Constants
from memristive_spinal_cord.layer2.parameters import SynapseModels
from enum import Enum


class Synapses(Enum):

    GLUTAMATERGIC = SynapseModel(
        'Glutamatergic',
        nest_model=SynapseModels.STATIC_SYNAPSE.value,
        params={'delay': Constants.SYNAPTIC_DELAY_EX.value}
    )

    GABAERGIC = SynapseModel(
        'GABAergic',
        nest_model=SynapseModels.STATIC_SYNAPSE.value,
        params={'delay': Constants.SYNAPTIC_DELAY_EX.value}
    )
