import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

_STATUS = ['INIT', 'ITER', 'FINAL', 'STOP']

class Horizon(object):

    def __init__(self, tstart='2018-01-01 00:00:00', tend='2019-01-01 00:00:00', repeat_every='12 hours',
                 horizon='2 days', time_step='15 minutes', tz="Europe/Paris"):
        """

        :param tstart:
        :param tend:
        :param repeat_every:
        :param duration:
        :param time_step:
        :param tz:
        """


        self.tz_info            = tz
        self.iter               = None
        self.tstart             = None
        self._current           = None
        self._previous          = None
        self.tend               = None
        self._actual_horizon    = None
        self._status            = _STATUS[0]

        try:
            self.TSTART = pd.Timestamp(tstart).tz_localize(self.tz_info)
            self.TEND   = pd.Timestamp(tend).tz_localize(self.tz_info)
        except ValueError as e:
            raise e

        self.horizon        = pd.Timedelta(horizon)
        self.repeat_every   = pd.Timedelta(repeat_every)
        self.time_step      = pd.Timedelta(time_step)

        assert ((self.TEND - self.TSTART)%self.horizon)%self.time_step == pd.Timedelta('0s'), \
            "The last 'horizon' should be divisible by the chosen 'time_step'. " \
            "Otherwise, TEND will not be present in the current horizon."
        assert self.horizon % self.time_step == pd.Timedelta('0s'), \
            "Parameter 'horizon' should be divisible by the chosen 'time_step'. " \
            "Otherwise, tend will not be present in the current horizon."
        assert self.repeat_every % self.time_step == pd.Timedelta('0s'),\
            "Parameter 'repeat_every' should be divisible by the chosen 'time_step'. " \
            "Otherwise, synchronization issues will raise for moving horizon."
        assert self.repeat_every.total_seconds() <= self.horizon.total_seconds(), \
            "duration of the current horizon must be greater than repeat_every."
        assert 2 * self.time_step.total_seconds() <= self.horizon.total_seconds(), \
            "duration of the current horizon must contain at least 2 timestamps"

        self.reset()
        self.index      = np.linspace(0, self.horizon.total_seconds(), num=len(self._current))  # time steps in seconds
        self.map        = pd.Series(self._current, index=self.index)
        self.nfe        = len(self.index) - 1  # number of finite element for discretisation

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, t):
        raise NotImplementedError('NotImplemented, user can not set the current horizon himself.')

    @property
    def previous(self):
        return self._previous

    @previous.setter
    def previous(self, value):
        raise NotImplementedError('NotImplemented, user can not set the previous horizon himself.')

    def next(self):

        if self._status == _STATUS[2]:
            self._status = _STATUS[3]
            logger.warning(f'Has no effect : the current horizon stops at horizon.TEND, we cannot go further.'
                           f' Changing _status to {_STATUS[3]}')
            return

        if self.tend + self.repeat_every < self.TEND:  # next horizon is within the time frame [TSTART, TEND]
            self.iter       += 1
            self._previous   = self._current
            self._current   += self.repeat_every
            self.tend       += self.repeat_every
            self.tstart     += self.repeat_every

            self._status    = _STATUS[1]
            logger.debug(f'Iteration over the horizon. Changing _status to {_STATUS[1]}')

        else : # next horizon should stop at TEND, in this case we should ensure that TEND is in self.current
            self.iter       += 1
            self.tstart     += self.repeat_every
            self.tend        = self.TEND
            self._previous   = self._current
            self._current    = pd.date_range(start=self.tstart, freq=self.time_step, end=self.tend)

            assert self.TEND == self._current[-1], Warning('The last Timestamp of last horizon should be TEND. This is \
                        usually indicative of a modelling error. Try chosing another time_step or TEND.')  # should not be necessary

            self._status     = _STATUS[2]
            logger.info(f'Final horizon has been reached. Changing _status to {_STATUS[2]}')

        logger.info(f'Iteration over the horizon. '
                    f'Tstart = {self.tstart}, '
                    f'Tend={self.tend}. ')

    def reset(self):
        self.iter        = 0
        self.tstart      = pd.Timestamp(self.TSTART)
        self.tend        = self.tstart + self.horizon
        self._current    = pd.date_range(start=self.tstart, freq=self.time_step, end=self.tend)

        assert self.tend == self._current[-1], Warning('The last Timestamp of current horizon should be tend. This is \
            usually indicative of a modelling error. ')  # should not be necessary

        self._status = _STATUS[0]
        logger.debug(f'Initialization of the time horizon. TSTART = {self.TSTART}, TEND={self.TEND}.')

        logger.info(f'Initialization of the time horizon :  '
                    f'TSTART = {self.tstart}, '
                    f'tend = {self.tend}, '
                    f'time step = {self.time_step}, '
                    f'repeat every = {self.repeat_every}')


def get_prediction_data(horizon, path ='.csv', usecols=None, tz_data='UTC', fillnan=False, filldict = {}, method='time'):

    """
    :param Horizon horizon: Time horizon
    :param path: csv data file
    :param tz_data: time zone information ('UTC' or 'Europe/Paris')
    :return:

    """
    # reading data file (all of it)
    if usecols is not None:
        d1 = pd.read_csv(path, index_col=0, usecols=usecols, parse_dates=True, dayfirst=True)
    else:
        d1 = pd.read_csv(path, index_col=0, parse_dates=True, dayfirst=True)

    # Nan values must be filled before interpolating, the user can use fillnan and filldict to do this
    if fillnan:
        try :
            for d in filldict:
                d1[d] = d1[d].fillna(filldict[d])
        except KeyError as e:
            raise e

    # convert date time index to the correct time zone
    if d1.index.tzinfo is None :
        d1.index = d1.index.tz_localize(tz_data).tz_convert(horizon.tz_info)
    else:
        d1.index = d1.index.tz_convert(horizon.tz_info)

    # be sure that the current horizon is in the data index set
    assert horizon.current[0]  >= d1.index[0],  ""
    assert horizon.current[-1] <= d1.index[-1], ""

    # Synchronizing / Interpolating data to the current horizon date time index

    dh1 = pd.DataFrame([np.NaN]*len(horizon.current), index=horizon.current, columns=['tmp'])

    import warnings
    with warnings.catch_warnings():
        # Pandas 0.24.1 emits useless warning when sorting tz-aware index
        warnings.simplefilter("ignore")
        if method=='time':
            a = d1.join(dh1, how='outer').interpolate(method=method)
        if method=='pad':
            a = d1.join(dh1, how='outer').sort_index().fillna(method='pad')

    del a['tmp']

    # selecting only horizon period
    data_horizon = a.loc[horizon.current]

    return data_horizon