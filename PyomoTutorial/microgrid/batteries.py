from base_units import AbsDynUnit
from pyomo.environ import *
from pyomo.dae import *
from pyomo.network import Port

UB = 1e6

class AbsBatteryV0(AbsDynUnit):
    """
    Battery with ideal efficiency.

    This battery is limited in power, variation of power and energy. One can fix initial and final stored energy.
    """

    def __init__(self, *args, **kwds):

        super().__init__(*args, **kwds)

        self.p      = Var(self.time, doc='energy derivative with respect to time',  initialize=0)
        self.e      = Var(self.time, doc='energy in battery',                       initialize=0)

        self.emin   = Param(default=0,       doc='minimum energy (kWh)',       mutable=True, within=NonNegativeReals)
        self.emax   = Param(default=UB,      doc='maximal energy',             mutable=True)
        self.e0     = Param(default=None,    doc='initial state',              mutable=True)
        self.ef     = Param(default=None,    doc='final state',                mutable=True)
        self.etac   = Param(default=1.0,     doc='charging efficiency',        mutable=True)
        self.etad   = Param(default=1.0,     doc='discharging efficiency',     mutable=True)
        self.dpdmax = Param(default=UB,      doc='maximal discharging power',  mutable=True)
        self.dpcmax = Param(default=UB,      doc='maximal charging power',     mutable=True)

        self.pcmax  = Param(default=UB,      doc='maximal charging power',     mutable=True, within=PositiveReals)
        self.pdmax  = Param(default=UB,      doc='maximal discharging power',  mutable=True, within=PositiveReals)

        self.de     = DerivativeVar(self.e, wrt=self.time, initialize=0,
                                    doc='variation of energy  with respect to time')
        self.dp     = DerivativeVar(self.p, wrt=self.time, initialize=0,
                                    doc='variation of the battery power with respect to time',
                                    bounds=lambda m, t: (-m.dpcmax, m.dpdmax))

        self.outlet = Port(initialize={'f': (self.p, Port.Conservative)})

        def _p_init(m, t):
            if t == m.time.bounds()[0]:
                return m.p[t] == 0
            return Constraint.Skip

        def _e_initial(m, t):
            if m.e0.value is not None:
                if t == 0:
                    return m.e[t] == m.e0
            return Constraint.Skip

        def _e_final(m, t):
            if m.ef.value is None:
                return Constraint.Skip
            if t == m.time.last():
                return m.ef-1e-5, m.e[t], m.ef+1e-5
            else:
                return Constraint.Skip

        def _e_min(m, t):
            if m.emin.value is None:
                return Constraint.Skip
            return m.e[t] >= m.emin

        def _e_max(m, t):
            if m.emax.value is None:
                return Constraint.Skip
            return m.e[t] <= m.emax

        def _pmax(m, t):
            if m.pcmax.value is None:
                return Constraint.Skip
            else:
                return -m.pcmax, m.p[t], m.pdmax

        def _dpcmax(m, t):
            if m.dpcmax.value is None:
                return Constraint.Skip
            else:
                return m.dp[t] >= -m.dpcmax

        def _dpdmax(m, t):
            if m.dpdmax.value is None:
                return Constraint.Skip
            else:
                return m.dp[t] <= m.dpdmax

        def _energy_balance(m, t):
            return m.de[t] == 1/3600*(m.p[t])

        self._e_balance = Constraint(self.time, rule=_energy_balance, doc='Energy balance constraint')
        self._p_init    = Constraint(self.time, rule=_p_init,    doc='Initialize power')
        self._e_initial = Constraint(self.time, rule=_e_initial, doc='Initial energy constraint')
        self._e_final   = Constraint(self.time, rule=_e_final,   doc='Final stored energy constraint')
        self._e_min     = Constraint(self.time, rule=_e_min,     doc='Minimal energy constraint')
        self._e_max     = Constraint(self.time, rule=_e_max,     doc='Maximal energy constraint')
        self._pmax      = Constraint(self.time, rule=_pmax,      doc='Power bounds constraint')
        self._dpdmax    = Constraint(self.time, rule=_dpdmax,    doc='Maximal varation of descharging power constraint')
        self._dpcmax    = Constraint(self.time, rule=_dpcmax,    doc='Maximal varation of charging power constraint')
