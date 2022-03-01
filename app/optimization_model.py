# -*- coding: utf-8 -*-
"""model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_jxnL3HQvWheA9remErj5oWdwRA-j_e6
"""

!pip install gurobipy
import random
import gurobipy as grb
import pandas as pd


# Gurobi WLS license file
# Your credentials are private and should not be shared or copied to public repositories.
# Visit https://license.gurobi.com/manager/doc/overview for more information.
WLSACCESSID='6467d903-5c72-46b0-89de-4cc058f8df40'
WLSSECRET='2e64aa23-f34c-4f10-bf2f-25ec48e06700'
LICENSEID=770264

# Setup Gurobi License for model
# Create environment with WLS license
e = grb.Env(empty=True)
e.setParam('WLSACCESSID', WLSACCESSID)
e.setParam('WLSSECRET', WLSSECRET)
e.setParam('LICENSEID', LICENSEID)
e.start()

# Create the model within the Gurobi environment
opt_model = grb.Model(name="MIP Model",env=e)

# Read backend data from github
intensity_scores = pd.read_csv("https://raw.githubusercontent.com/gaurav613/fydp_bess/main/Data/Intensity_score.csv")

"""Variables: Decision Variables and Parameters"""

## decision variables
# C m = Total cost savings by month
# Gm = GHG reduction by month
# HhmC = hour span to charge; binary variable
# HhmD = hour span to discharge; binary variable
# Ph,mS ,Ph,mD = Energy stored/discharged by battery at hour, h [kWh]
months = range(1,13)
hours = range(1,25)

# # total costs
cost_m  = [opt_model.addVar(vtype=grb.GRB.CONTINUOUS, name="cost_{}".format(month)) for month in months]
# # reduced ghg
ghg_m  = [opt_model.addVar(vtype=grb.GRB.CONTINUOUS, name="ghg_{}".format(month)) for month in months]

# # total costs
TN_m = [opt_model.addVar(vtype=grb.GRB.CONTINUOUS, name="TN_{}".format(month)) for month in months]
TM_m =[opt_model.addVar(vtype=grb.GRB.CONTINUOUS, name="TM_{}".format(month)) for month in months]
TF_m = [opt_model.addVar(vtype=grb.GRB.CONTINUOUS, name="TF_{}".format(month)) for month in months]

# binary indicator for hour span to charge
HC_hm  = {(i,j):opt_model.addVar(vtype=grb.GRB.BINARY,
                        name="HC_{0}_{1}".format(i,j)) 
for i in months for j in hours}

# binary indicator for hour span to discharge
HD_hm  = {(i,j):opt_model.addVar(vtype=grb.GRB.BINARY,
                        name="HD_{0}_{1}".format(i,j)) 
for i in months for j in hours}

# energy charged at hour h
PC_hm = {(i,j):opt_model.addVar(vtype=grb.GRB.CONTINUOUS,
                        name="PC_{0}_{1}".format(i,j)) 
for i in months for j in hours}

# energy discharged at hour h
PD_hm = {(i,j):opt_model.addVar(vtype=grb.GRB.CONTINUOUS,
                        name="PD_{0}_{1}".format(i,j)) 
for i in months for j in hours}

# energy from grid at hour h
PG_hm = {(i,j):opt_model.addVar(vtype=grb.GRB.CONTINUOUS,
                        name="PG_{0}_{1}".format(i,j)) 
for i in months for j in hours}

# energy from grid at hour h
SoC_hm = {(i,j):opt_model.addVar(vtype=grb.GRB.CONTINUOUS,
                        name="SoC_{0}_{1}".format(i,j)) 
for i in months for j in hours}

# Ihm = fixed GHG intensity factor by month & hour
I_hm = []
for month in months:
   I_hm.append(intensity_scores[intensity_scores['Month'] == month]['avg_GHGIntensity'].tolist())

# on peak hours
on_hours = [7,8,9,10,17,18]
# mid peak hours
mid_hours = [11,12,13,14,15,16]
# off peack hours
off_hours = [0,1,2,3,4,5,6,19,20,21,22,23]

# CN = fixed on-peak electricity pricing [$/kWh]
CN = 0.17
# CM = fixed mid-peak electricity pricing [$/kWh]
CM = 0.113
# CF = fixed off-peak electricity pricing [$/kWh]
CF = 0.082
# UmN = household usage during on-peak [kWh]
UN_m = 500
# UmM = household usage during mid-peak [kWh]
UM_m = 300
# UmF = household usage during off-peak [kWh]
UF_m = 380
#  = Depth of discharge factor [%] (Saved energy for backup)
depth = 0.2
# WC, WG= Weights applied to decision variables
w_c = 0.9
w_g = 0.1
# c=d==5 [kWh], rate of energy charge/discharge
rate = 5 #kWh
# = 90%, efficiency rating of battery
efficiency = 0.9
# Max capacity of battery, 13.5 kWh
capacity = 13.5

# Ph,mG ,Ph,mU = Energy from the grid/usage by user at hour, h [kWh]
PU_hm = []# usage

for month in months:
  PU_hm.append([0]*24)

# Converting monthly household usage into hourly usage
for i in months:
  for j in on_hours:
    PU_hm[i-1][j] = round(UN_m/(6),4)

for i in months:
  for j in mid_hours:
    PU_hm[i-1][j] = round(UM_m/(6),4) 

for i in months:
  for j in off_hours:
    PU_hm[i-1][j] = round(UF_m/(12),4)

# Constraints

# State of battery constraints
# Battery always starts the day at depth of discharge
opt_model.addConstrs(SoC_hm[i,1] == capacity * depth for i in months)
opt_model.addConstrs(SoC_hm[i,j-1] + (HC_hm[i,j]*PC_hm[i,j]) - (HD_hm[i,j]*PD_hm[i,j]) == SoC_hm[i,j] for i in months for j in hours[1:])

# Prevent charging and discharging at same hour
opt_model.addConstrs(HC_hm[i,j] + HD_hm[i,j] <= 1 for i in months for j in hours)

# Maximum number of hours to charge and discharge
opt_model.addConstrs(grb.quicksum(HC_hm[i,j] for j in hours) <= 3 for i in months)
opt_model.addConstrs(grb.quicksum(HD_hm[i,j] for j in hours) <= 3 for i in months)

# Maximum rate of charge and discharge
opt_model.addConstrs(PC_hm[i,j] <= rate for i in months for j in hours)
opt_model.addConstrs(PD_hm[i,j] <= rate for i in months for j in hours)

# Maximum storage capacity of battery
opt_model.addConstrs(SoC_hm[i,j] - capacity <= 0 for i in months for j in hours)

# Minimum battery energy at depth of discharge
opt_model.addConstrs(SoC_hm[i,j] - (capacity*depth) >= 0 for i in months for j in hours)

# Supply & Demand constraint of energy
opt_model.addConstrs((efficiency*PD_hm[i,j]*HD_hm[i,j])+PG_hm[i,j] == PU_hm[i-1][j-1] + PC_hm[i,j]*HC_hm[i,j] for i in months for j in hours)

# Total cost constraints
opt_model.addConstrs(grb.quicksum((PG_hm[i,j+1]+PC_hm[i,j+1])*CN for j in on_hours) == TN_m[i-1] for i in months)
opt_model.addConstrs(grb.quicksum((PG_hm[i,j+1]+PC_hm[i,j+1])*CM for j in mid_hours) == TM_m[i-1] for i in months)
opt_model.addConstrs(grb.quicksum((PG_hm[i,j+1]+PC_hm[i,j+1])*CF for j in off_hours) == TF_m[i-1] for i in months)

## Objective function
# Aggregate cost savings & GHG reduction into one variable
opt_model.addConstrs(((TN_m[i-1]+TM_m[i-1]+TF_m[i-1])) == cost_m[i-1] for i in months)
#opt_model.addConstrs(grb.quicksum((I_hm[i-1][j-1]*HD_hm[i,j]*PD_hm[i,j])-(I_hm[i-1][j-1]*HC_hm[i,j]*PC_hm[i,j]) for j in hours) == ghg_m[i-1] for i in months)
#opt_model.addConstrs(grb.quicksum((I_hm[i-1][j-1]*HD_hm[i,j])-(I_hm[i-1][j-1]*HC_hm[i,j]) for j in hours) == ghg_m[i-1] for i in months)
opt_model.addConstrs(grb.quicksum(I_hm[i-1][j-1]*(PU_hm[i-1][j-1]-PD_hm[i,j]+PC_hm[i,j]) for j in hours) == ghg_m[i-1] for i in months)
# Set objective function
opt_model.setObjective(grb.quicksum(w_c*cost_m[i-1] + w_g*ghg_m[i-1] for i in months),grb.GRB.MINIMIZE)
#opt_model.setObjective(sum(cost_m[i-1] for i in months),grb.GRB.MINIMIZE)



# Optimize the model
opt_model.optimize()
opt_model.display()

# Generate results from model

# Convert results into a list and then into dataframe
results = opt_model.getVars()
results_list = []

for var in results:
  results_list.append([var.varName,var.x])

results_df = pd.DataFrame (results_list, columns = ['Var', 'Val'])
results_df[['Var', 'Month','Hour']] = results_df['Var'].str.split('_', expand = True)
HC_results = results_df[results_df.Var.str.match('HC')]
HD_results = results_df[results_df.Var.str.match('HD')]
PC_results = results_df[results_df.Var.str.match('PC')]
PD_results = results_df[results_df.Var.str.match('PD')]
SoC_results = results_df[results_df.Var.str.match('SoC')]
SoC_results

cost_results = results_df[results_df.Var.str.match('cost')]
ghg_results = results_df[results_df.Var.str.match('ghg')]

Act_cost = UN_m*CN+UM_m*CM+UF_m*CF

# generating random output data
import random
costs = []
ghg = []
for i in range(len(months)):
  n = random.randint(100,200)
  costs.append(n)
  n1 = random.uniform(10,20)
  ghg.append(n1)

cost_df = pd.DataFrame(list(zip(months,costs)), columns = ["Month","Cost"])
ghg_df = pd.DataFrame(list(zip(months,ghg)), columns = ["Month","GHG"])

cost_df.to_csv("costs.csv")
ghg_df.to_csv("ghg.csv")