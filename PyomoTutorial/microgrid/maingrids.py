# -*- coding: utf-8 -*-
"""
Distribution Grid Units

Electrical connection to the distribution grid.

"""
from sources import  AbsPowerSource
from cost import def_bilinear_cost, def_linear_cost

from pyomo.environ import Constraint,  Var, Param, Block, Expression, Piecewise
from pyomo.network import Port
from pyomo.environ import NonNegativeReals, Binary, Reals
from pandas import Series

__all__ = ['AbsMainGridV0', 'AbsMainGridV1']

UB = 10e6


def def_pin_pout(m):
    # This could be better implemented.
    # In particular, it should not use m.p directly but m.find_component(name_var)

    """
    Defines power 'in' and 'out' variables

    :param m:
    :return:
    """

    assert isinstance(m, Block),    f"argument 'm', must be an instance of Block, but is actually {type(m)}."
    assert hasattr(m, 'p'),         f"model m does not have attribute named 'p'. This is needed. "

    m.pmax  = Param(initialize=UB,  mutable=True, doc='maximal power out (kW)')
    m.pmin  = Param(initialize=UB,  mutable=True, doc='maximal power in (kW)')

    m.pout  = Var(m.time, doc='power to the main grid',   within=NonNegativeReals,    initialize=None)
    m.pin   = Var(m.time, doc='power from the main grid', within=NonNegativeReals,    initialize=None)
    m.u     = Var(m.time, doc='binary variable',          within=Binary,              initialize=None)

    def _power_balance(b, t):
        return b.p[t] - b.pout[t] + b.pin[t] == 0

    def _pmax(b, t):
        if b.pmax.value is None:
            return Constraint.Skip
        return b.pout[t] - b.u[t] * b.pmax <= 0

    def _pmin(b, t):
        if b.pmin.value is None:
            return Constraint.Skip
        return b.pin[t] + b.u[t] * b.pmin <= b.pmin

    m._pmin      = Constraint(m.time, rule=_pmin,          doc='low bound')
    m._pmax      = Constraint(m.time, rule=_pmax,          doc='up bound')
    m._p_balance = Constraint(m.time, rule=_power_balance, doc='power balance')


class AbsMainGridV0(AbsPowerSource):
    """
    Simple MainGrid Unit.

    One Power port (named 'p' by default) associated with a simple cost (named 'cost').
    (Source convention)
    """
    def __init__(self, *args, flow_name='p', **kwgs):

        super().__init__(*args, flow_name=flow_name, **kwgs)
        self.inst_cost = def_linear_cost(self, var_name=flow_name)
        self.component(flow_name).doc = 'Supplied power from the maingrid (source convention)'
        self.pmin = Param(initialize=UB, doc = 'minimal power (kW)')
        self.pmax = Param(initialize=UB, doc = 'minimal power (kW)')
        
        @self.Constraint(self.time)
        def _pmax(b, t):
            if b.pmax.value is None:
                return Constraint.Skip
            return -UB, b.p[t] , b.pmax

        @self.Constraint(self.time)
        def _pmin(b, t):
            if b.pmin.value is None:
                return Constraint.Skip
            return  -b.pmin, b.p[t], UB
        
        

class AbsMainGridV1(AbsPowerSource):
    """
    Main Grid Unit.

    Consists of a power source with limits (pmin, pmax),
    associated with a bilinear cost (selling and buying cost, i.e. c_in and c_out).
    A binary variable 'u' is declared to tackle the price discontinuity at p=0.
    (Source convention)

    """
    def __init__(self, *args, flow_name='p', **kwgs):
        super().__init__(*args, flow_name=flow_name, **kwgs)
        def_pin_pout(self)
        self.inst_cost = def_bilinear_cost(self, var_in='pin', var_out='pout')
