from enum import Enum


class Weights(Enum):

    # Tier Interconnections
    e0e1 = 200.
    e0e3 = 100.
    e1e2 = 100.
    e2e1 = 100.
    e2i1 = 100.
    e3e4 = 100.
    e3i0 = 100.
    e4e3 = 100.
    i0e1 = -0. #-60
    i1e1 = -0. #-50

    # Coonnections between tiers

    e0e0 = 50.
    e3e0 = 60.
    e2e2 = 150.

    # Connections to pool

    e2p = 10.

    # Motogroup interconnections

    aff_ia_moto = 15. #blue moti
    aff_ia_ia = 5.  #blue top
    aff_ii_ia = 5.  # red top
    aff_ii_ii = 28. #red bot
    ii_moto = 27. # bot to moto
    ia_ia = -0.7  # ingib
    ia_moto = -6.9 # cross

    # Pool to Motogroup
    p_ex_moto = 55.
    p_ex_ia = 5.
    p_fl_moto = 55.
    p_fl_ia = 5.
