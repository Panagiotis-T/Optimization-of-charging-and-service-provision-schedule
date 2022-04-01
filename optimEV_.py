import numpy as np
import pandas
from gurobipy import *
import random
import csv

year="year"


drivingData=       'data'+year+"/filename.csv" ##energy consumption for all vehicles
#HoursHome=       'data'+year+"/filename.csv"
NotHoursHome=       'data'+year+"/filename.csv" ##hours that vehicle was available to provide frequency regulation
energyData=        "data"+year+"/filename.csv" ##frequency
spotData=          "data"+year+"/filename.csv" ##spotprice
spotData_dso=          "data"+year+"/filename.csv" ##spotprice including tariff
fcrData=          "data"+year+"/filename.csv" ##capacity payment compensation
upData=          "data"+year+"/filename.csv" ##price for upward regulation
downData=          "data"+year+"/filename.csv" ##price for downward regulation

## Define inputs

energy_orig = list(pandas.read_csv(energyData, sep=',', header=None).values)
gridE = list(pandas.read_csv(drivingData, sep=',', header=None).values) # driving consumption
# hours_orig = list(pandas.read_csv(HoursHome, sep=',', header=None).values) # hours when EV is parked home
nothours_orig = list(pandas.read_csv(NotHoursHome, sep=',', header=None).values) # hours when EV is not parked home
spot_orig = list(pandas.read_csv(spotData, sep=',', header=None).values) #spot price
spot_dso_orig = list(pandas.read_csv(spotData_dso, sep=',', header=None).values) #spot price with DSO tariff added
fcr_orig = list(pandas.read_csv(fcrData, sep=',', header=None).values)
up_orig = list(pandas.read_csv(upData, sep=',', header=None).values)
down_orig = list(pandas.read_csv(downData, sep=',', header=None).values)

opt_model = Model(name="MIP Model")

n = 8759 #one year data
m = 1 #for one vehicle
T = range(0, n+1)
Vehicles = range(0, m)

energy = [energy_orig] * m
spot = [spot_orig] * m
spot_dso = [spot_dso_orig] * m
fcr = [fcr_orig] * m
# up = [up_orig] * m
# down = [down_orig] * m

h = 0.9 ##efficiency
Pmax = 10 ##maximum charging capability
Pmin = 0 ##minimum power for charging
SOCmax = 36 ##maximum battery limit
SOCmin = 8 ##minimum battery limit


##Power when charging
Pcharge  = opt_model.addVars(T, Vehicles,vtype=GRB.CONTINUOUS,
                        lb=Pmin,
                        ub= Pmax)

Pcharge_avail  = opt_model.addVars(T, Vehicles,vtype=GRB.CONTINUOUS,
                        lb=0)
##Power when discharging
Pdis  = opt_model.addVars(T, Vehicles, vtype=GRB.CONTINUOUS,
                        lb=Pmin,
                        ub= Pmax)

Pdis_avail  = opt_model.addVars(T, Vehicles, vtype=GRB.CONTINUOUS,
                        lb=0)

charge_switch = opt_model.addVars(T, Vehicles, vtype = GRB.BINARY)
discharge_switch = opt_model.addVars(T, Vehicles, vtype = GRB.BINARY)

#Capacity nominal
Pcap  = opt_model.addVars(T, Vehicles,vtype=GRB.CONTINUOUS,
                        lb=Pmin,
                        ub=Pmax)

Pcap_switch = opt_model.addVars(T, Vehicles, vtype = GRB.BINARY)

##
gridE_switch = opt_model.addVars(T, Vehicles, vtype = GRB.BINARY)




#State of charge
SOC  = opt_model.addVars(T, Vehicles,vtype=GRB.CONTINUOUS,
                        lb=SOCmin,
                        ub= SOCmax)

# <= constraints
opt_model.addConstrs((Pcharge[(t,v)] + Pdis[(t,v)] + Pcap[(t,v)] <= Pmax for t in T for v in Vehicles))

# Pcharge_avail=(SOCmax-SOC)/deltaT, Pdis_avail=(SOC-SOCmin)/deltaT
# Pcharge<=Pcharge_avail, Pcharge<=Pcharge_avail
# opt_model.addConstrs((Pcharge_avail[(t,v)] == SOCmax - SOC[(t,v)] for t in T for v in Vehicles))
# opt_model.addConstrs((Pdis_avail[(t,v)] == SOC[(t,v)] - SOCmin for t in T for v in Vehicles))
opt_model.addConstrs((Pcharge_avail[(t,v)] == SOCmax - SOC[(t,v)] + Pcap[(t,v)] * energy[v][t] for t in T for v in Vehicles))
opt_model.addConstrs((Pcharge[(t,v)] <= Pcharge_avail[(t,v)] for t in T for v in Vehicles))
opt_model.addConstrs((Pdis_avail[(t,v)] == SOC[(t,v)] - SOCmin + Pcap[(t,v)] * energy[v][t] for t in T for v in Vehicles))
opt_model.addConstrs((Pdis[(t,v)] <= Pdis_avail[(t,v)] for t in T for v in Vehicles))

# define initial SOC
T0 = range(0, 1)
opt_model.addConstrs((SOC[(t,v)] == 20 for t in T0 for v in Vehicles), name = "InitialSOC")

# T1 = range(1,len(T))
T1 = range(0,len(T)-1)

# == constraints
opt_model.addConstrs((SOC[(t+1,v)] == SOC[(t,v)]
                      + gridE[t][v] + Pcap[(t,v)] * energy[v][t]
                      + Pcharge[(t,v)] * h
                      - Pdis[(t,v)] * 1 / h
                      for t in T1
                      for v in Vehicles),
                     name="constraint7_{0}_{1}")


## avoid driving and providing services at the same time
opt_model.addConstrs((Pcap[t,v] >= Pcap_switch[t,v] * Pmin for t in T for v in Vehicles))
opt_model.addConstrs((Pcap[t,v] <= Pcap_switch[t,v] * Pmax for t in T for v in Vehicles))
opt_model.addConstrs((np.absolute(gridE[t][v])*Pcap_switch[t,v] == 0 for t in T for v in Vehicles))

## avoid driving and charging at the same time
opt_model.addConstrs((Pcharge[t,v] >= charge_switch[t,v] * Pmin for t in T for v in Vehicles))
opt_model.addConstrs((Pcharge[t,v] <= charge_switch[t,v] * Pmax for t in T for v in Vehicles))
opt_model.addConstrs((np.absolute(gridE[t][v])*charge_switch[t,v] == 0 for t in T for v in Vehicles))

## avoid driving and discharging at the same time
opt_model.addConstrs((Pdis[t,v] >= discharge_switch[t,v] * Pmin for t in T for v in Vehicles))
opt_model.addConstrs((Pdis[t,v] <= discharge_switch[t,v] * Pmax for t in T for v in Vehicles))
opt_model.addConstrs((np.absolute(gridE[t][v])*discharge_switch[t,v] == 0 for t in T for v in Vehicles))

## avoid charging and discharging at the same time
opt_model.addConstrs(charge_switch[t,v] * discharge_switch[t,v] == 0 for t in T for v in Vehicles)

## avoid providing services when the EV is not parked at home
opt_model.addConstrs((np.absolute(nothours_orig[t][v])*Pcap_switch[t,v] == 0 for t in T for v in Vehicles))

# avoid charging when the EV is not parked at home
# opt_model.addConstrs((np.absolute(nothours_orig[t][v])*charge_switch[t,v] == 0 for t in T for v in Vehicles))

# avoid discharging when the EV is not parked at home
opt_model.addConstrs((np.absolute(nothours_orig[t][v])*discharge_switch[t,v] == 0 for t in T for v in Vehicles))

#objective function
opt_model.setObjective((quicksum(Pcharge[(t,v)] * spot_dso[v][t] - Pdis[(t,v)] * spot_dso[v][t] - Pcap[(t,v)] * fcr[v][t]
                            for t in T for v in Vehicles)), GRB.MINIMIZE)

opt_model.optimize()

for v in Vehicles:
    print('----------------')
    print(f'Vehicle {v}')
    print()
    print('t -- SOC -- Pcharge -- Pdischarge -- Pcapacity -- energy -- gridE')
    for t in T:
        print('{:2d}'.format(t),
              '{:.3f}'.format(SOC[(t, v)].x) , '{:.3f}'.format(Pcharge[(t, v)].x),
              '{:.3f}'.format(Pdis[(t, v)].x), '{:.3f}'.format(Pcap[(t, v)].x),
              '{}'.format(energy[v][t]),
              '{}'.format(gridE[t][v]))


# Export data to csv

##Pcapacity

opt_df = pandas.DataFrame.from_dict(Pcap, orient="index",
                                columns = ["variable_object"])
opt_df.index = pandas.MultiIndex.from_tuples(opt_df.index,
                               names=["column_i", "column_j"])
opt_df.reset_index(inplace=True)

opt_df["solution_value"] = opt_df["variable_object"].apply(lambda item: item.X)

opt_df.drop(columns=["variable_object"], inplace=True)
opt_df.to_csv("./filename.csv")

##Pcharge

opt_df = pandas.DataFrame.from_dict(Pcharge, orient="index",
                                    columns = ["variable_object"])
opt_df.index = pandas.MultiIndex.from_tuples(opt_df.index,
                                             names=["column_i", "column_j"])
opt_df.reset_index(inplace=True)

opt_df["solution_value"] = opt_df["variable_object"].apply(lambda item: item.X)

opt_df.drop(columns=["variable_object"], inplace=True)
opt_df.to_csv("./filename.csv")

##Pdischarge

opt_df = pandas.DataFrame.from_dict(Pdis, orient="index",
                                    columns = ["variable_object"])
opt_df.index = pandas.MultiIndex.from_tuples(opt_df.index,
                                             names=["column_i", "column_j"])
opt_df.reset_index(inplace=True)

opt_df["solution_value"] = opt_df["variable_object"].apply(lambda item: item.X)

opt_df.drop(columns=["variable_object"], inplace=True)
opt_df.to_csv("./filename.csv")

##SOC

opt_df = pandas.DataFrame.from_dict(SOC, orient="index",
                                    columns = ["variable_object"])
opt_df.index = pandas.MultiIndex.from_tuples(opt_df.index,
                                             names=["column_i", "column_j"])
opt_df.reset_index(inplace=True)

opt_df["solution_value"] = opt_df["variable_object"].apply(lambda item: item.X)

opt_df.drop(columns=["variable_object"], inplace=True)
opt_df.to_csv("./filename.csv")
