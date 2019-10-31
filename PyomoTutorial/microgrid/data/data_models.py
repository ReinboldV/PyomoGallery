import pandas as pd
import os

wd = os.getcwd()
path=os.path.join(wd, 'data/prediction.csv')
usecols=['Date and time (UTC)', 'Pmax', 'T1', 'TGBT']
fillnan=True
filldict={'Pmax':0}

TSTART = '2019-02-18 00:00:00'
TEND   = '2019-02-19 00:00:00'

df = pd.read_csv(path, index_col=0, usecols=usecols, parse_dates=True, dayfirst=True)
df['Pmax'] = df['Pmax'].fillna(0)
df = df.loc[TSTART:TEND]
df = df.round(decimals=4)

df.rename(columns={'TGBT': 'P_load', 'T1': 'P_load_1'}, inplace=True)
df['P_pv']       = df.Pmax * 100/1000
df.Pmax          = df.Pmax / 1000
df.P_load        = df.P_load.apply(lambda x: round(x, 4))
df.P_load_1      = df.P_load_1.apply(lambda x: round(x, 4))
df.P_pv          = df.P_pv.apply(lambda x: round(x, 4))

df_s = df.copy()
df.index = (df.index - df.index[0]).total_seconds()

data_batt = {
        'time':   {None: [df.index[0], df.index[-1]]},
        'dpcmax': {None: 20},
        'dpdmax': {None: 20},
        'e0' :    {None: 50}, # soc init  = 50% 
        'ef' :    {None: 50}, # soc final = 50% 
        'emin':   {None: 10},  # soc min  = 10% 
        'emax':   {None: 100},   # 100 kWh battery
        'pcmax':  {None: 20.0},
        'pdmax':  {None: 20.0}}

data_mg = {
    'time': {None: [df.index[0], df.index[-1]]},
    'pmax': {None: 30},
    'pmin': {None: 30},
    'cost': {None: 0.12/3600}
}

data_s = {
    'time': {None: [df.index[0], df.index[-1]]},
    'profile_index': {None: df.index},
    'profile_value': df['P_pv'].to_dict()
}

data_l = {
    'time': {None: [df.index[0], df.index[-1]]},
    'profile_index': {None: df.index},
    'profile_value': df['P_load_1'].to_dict()}

data = {None: dict(time     = {None: [df.index[0], df.index[-1]]},
                b           = data_batt,
                mg          = data_mg,
                s           = data_s,
                l           = data_l)}