"""
Economic Units and methods

This module contains Economic units and methods to define parameter, variables and objectives to an exiting block
"""

from pyomo.environ import Param, Var, Expression, NonNegativeReals, PositiveReals, Constraint

__all__ = ['def_linear_cost', 'def_bilinear_cost','def_linear_dyn_cost',
           'def_bilinear_dynamic_cost', 'def_absolute_cost']


def def_linear_cost(m, var_name='p'):
    """
    Method for adding a linear constant cost associated to variable 'p', to a block
    Final instantaneous cost expression is called "inst_cost"

    :param m: Block
    :param str var_name: Names of the expensive variable
    :return: A pyomo expression of the instantaneous cost

    """
    m.cost = Param(initialize=0, mutable=True, doc=f'simple linear cost, associated with variable {var_name}, (euros/kWh)')

    def _instant_cost(m, t):
        return m.find_component(var_name)[t] * m.cost / 3600

    return Expression(m.time, rule=_instant_cost,
                      doc=f'instantaneous linear cost (euros/s), associated with variable {var_name}')


def def_linear_dyn_cost(m, var_name='p'):
    """
    Method for adding a linear dynamic cost associated to variable 'p', to a block
    Final instantaneous cost expression is called "inst_cost"

    .. math::
        m.instant\_cost(t) = m.var(t) \\times m.cost(t), \ \\forall t \\in m.time

    :param m: Block
    :param str var_name: Names of the expensive variable
    :return: pyomo Expression
    """
    from .base_units import fix_profile

    fix_profile(m, flow_name='cost', index_name='cost_index', profile_name='cost_value')

    def _instant_cost(m, t):
        return m.find_component(var_name)[t] * m.cost[t] / 3600

    return Expression(m.time, rule=_instant_cost,
                      doc=f'instantaneous linear cost (euros/s), associated with variable {var_name}')



def def_absolute_cost(m, var_name='p'):
    """
    Method for adding absolute cost, i.e. a bilinear cost of coefficient -1 and +1 associated with variable 'p'.
    Final instantaneous cost expression is called "inst_cost"

    :param m: Block
    :param var_name: Names of the expensive variable
    :return: pyomo Expression
    """

    abs_var_name = f'abs_{var_name}'
    m.add_component(abs_var_name, Var(m.time, within=NonNegativeReals, initialize=0, doc=f'Absolute value of variable {var_name}'))
    m.add_component(f'{var_name}_cost', Param(default=1, mutable=True,within=PositiveReals,
                    doc=f'cost associated to the absolute value of {var_name} (euros/kWh)'))

    def _bound1(m, t):
        return m.find_component(abs_var_name)[t] >= -m.find_component(f'{var_name}_cost')*m.find_component(var_name)[t]

    def _bound2(m, t):
        return m.find_component(abs_var_name)[t] >=  m.find_component(f'{var_name}_cost')*m.find_component(var_name)[t]

    def _instant_cost(m, t):
        return m.find_component(abs_var_name)[t] * m.find_component(f'{var_name}_cost') / 3600

    m.add_component(f'_{var_name}_cost_1', Constraint(m.time, rule=_bound1))
    m.add_component(f'_{var_name}_cost_2', Constraint(m.time, rule=_bound2))

    return Expression(m.time, rule=_instant_cost,
                      doc=f'instantaneous bilinear cost (euros/s), associated with variable {var_name}')


def def_bilinear_cost(bl, var_in='p_in', var_out='p_out'):
    """
    Method for adding bilinear cost to a block associated to variables 'var_in', 'var_out'.

    Names of costs are 'cost_in' 'cost_out' and are not tunable for the moment.
    Final instantaneous cost expression is called "inst_cost"

    :param bl: Block
    :param str var_in: Name of the input variable
    :param str var_out: Name of the input variable
    :return: pyomo Expression
    """
    bl.cost_in  = Param(default=0, mutable=True, doc=f'buying cost of variable {var_in} (euro/kWh)')
    bl.cost_out = Param(default=0, mutable=True, doc=f'selling cost of variable {var_out} (euro/kWh)')

    def _instant_cost(m, t):
        return (m.find_component(var_out)[t] * m.cost_out - m.find_component(var_in)[t] * m.cost_in)/3600

    return Expression(bl.time, rule=_instant_cost,
                      doc=f'instantaneous bilinear cost (euros/s), associated with variable {var_in} and {var_out}')


def def_bilinear_dynamic_cost(bl, var_in='p_in', var_out='p_out'):
    """
    Method for adding bilinear dynamic cost to a block associated to variables 'var_in', 'var_out'.

    Names of costs are 'cost_in' 'cost_out' and are not tunable for the moment.
    Final instantaneous cost expression is called "inst_cost"

    :param bl: Block
    :param str var_in: Name of the input variable
    :param str var_out: Name of the input variable
    :return: Expression
    """

    from .base_units import fix_profile

    fix_profile(bl, flow_name='cost_in',  index_name='cost_in_index',  profile_name='cost_in_value')
    fix_profile(bl, flow_name='cost_out', index_name='cost_out_index', profile_name='cost_out_value')

    def _instant_cost(m, t):
        return (m.find_component(var_out)[t] * m.cost_out[t] - m.find_component(var_in)[t] * m.cost_in[t])/3600

    return Expression(bl.time, rule=_instant_cost,
                      doc=f'instantaneous bilinear and dynamic cost, associated with variable {var_in} and {var_out}')

