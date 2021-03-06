import numpy as np 
import matplotlib.pyplot as plt
import scipy.optimize
import multiprocessing as mp
import copy
import pickle

import gasdynamics as gd
from heat_flux import heat_flux
from plug_nozzle_angelino import plug_nozzle 
import MOC


## NASA CEA CONSTANTS
class CEA_constants():
	def __init__(self,gamma,T_c,p_c,rho_c,a_c,Pr,cp,c,w):
		self.gamma = gamma
		self.T_c = T_c
		self.p_c = p_c
		self.rho_c = rho_c
		self.a_c = a_c
		self.Pr = Pr 
		self.cp = cp 
		self.c = c
		self.w = w

def compute_thrust_over_range(plug_nozzle_class,alt_range,gamma,send_end,downstream_factor=1.2,chr_mesh_n=50):
	## INPUTS: plug_nozzle class object, gamma, numpy array containing altitude range over which to compute the thrust,
	##		   the downstream_factor (default 1.2) for the characteristic mesh calculations, and chr_mesh_n (default 50), the number 
	##		   of expansion waves for the MOC_mesh

	## OUTPUTS: numpy array of thrusts for altitude range for given inputs
	thrust_range = np.zeros(alt_range.shape)
	for i in range(alt_range.shape[0]):
		# print(alt_range[i])
		try:
			MOC_mesh = MOC.chr_mesh(plug_nozzle_class,gamma,alt_range[i],chr_mesh_n,downstream_factor=downstream_factor)
			thrust_range[i] = MOC_mesh.compute_thrust('nearest',10)
		except:
			thrust_range[i] = 0

		print(i)
	send_end.send(thrust_range)

def multicore_thrust_compute(plug_nozzle_class,altitude_range,gamma,downstream_factor=1.2,chr_mesh_n=50,no_core=1):
	proc_list = []
	pipe_list =[]

	alt_range_split = np.split(altitude_range,no_core)

	for i in range(no_core):
		recv_end, send_end = mp.Pipe(False)
		args = (plug_nozzle_class,alt_range_split[i],gamma,send_end,downstream_factor,chr_mesh_n)
		proc = mp.Process(target=compute_thrust_over_range, args = args)
		proc_list.append(proc)
		pipe_list.append(recv_end)
		proc.start()

	for proc in proc_list:
		proc.join()

	thrust_range = [x.recv() for x in pipe_list]

	thrust_range = np.concatenate(thrust_range)

	# for thread in threads:
	# 	thread.map

	return thrust_range


def design_angelino_nozzle(design_alt,truncate_ratio,CEA,r_e):
	(p_atm,T_atm,rho_atm) = gd.standard_atmosphere([design_alt])

	PR = CEA.p_c/p_atm

	M_e = gd.PR_expansion_mach(PR,CEA.gamma)

	expansion_ratio = gd.expansion_ratio(1,M_e,CEA.gamma)#6.64 #8.1273
	# print('Exp. ratio: ' + str(expansion_ratio))
	# print('PR: ' + str(PR))

	A_t = r_e**2*np.pi/expansion_ratio # max expansion (r_b = 0, r_e**2 >= A_t*expansion_ratio/np.pi)

	return plug_nozzle(expansion_ratio,A_t,r_e,CEA.gamma,CEA.T_c,CEA.p_c,CEA.a_c,CEA.rho_c,100,truncate_ratio = truncate_ratio)

def COST_FNC(params,spike,T_w,CEA,alpha,beta,chr_mesh_n=145,no_core=4):
	try:
		x_vals,y_vals = params
	except ValueError:
		x_vals,y_vals = np.split(params,2)	


	spike.x = x_vals; spike.y = y_vals


	### CALCULATING COST
	##	thurst estimation over altitude
	alt_range = np.linspace(0,9144,3*no_core)
	np.random.shuffle(alt_range)
	(p_atm_r,T_atm_r,rho_atm_r) = gd.standard_atmosphere(alt_range)
	#print(CEA.p_c/p_atm_r)
	#thrust_range = multicore_thrust_compute(spike,alt_range,CEA.gamma,downstream_factor=1.2,chr_mesh_n=50,no_core=4)
	thrust_range = multicore_thrust_compute(spike,alt_range,CEA.gamma,downstream_factor=1.2,chr_mesh_n=chr_mesh_n,no_core=no_core)

	# unshuffle of arrays
	ordered_idx = np.argsort(alt_range)
	alt_range = alt_range[ordered_idx]; thrust_range = thrust_range[ordered_idx]

	work = np.trapz(thrust_range,alt_range)
	print("work = " + str(work) + ". Bounds [" + str(alt_range[0]) + ', ' + str(alt_range[-1]) + ']')
	plt.plot(alt_range,thrust_range,'o')
	plt.show()
	## heat transfer required

	#total_heat_flux = heat_flux(CEA.Pr,CEA.cp,CEA.gamma,CEA.c,CEA.w,CEA.T_c,T_w,spike)

	# print('Work*alpha: ' + str(work*alpha))
	# print('Heat flux*beta: ' + str(total_heat_flux*beta))
	return -alpha*work #+ total_heat_flux*beta
	


## CONSTANTS OF DESIGN FOR AERODYNAMICS
r_e = 0.067/2 #0.034 # likely too large

## NASA CEA CONSTANTS
gamma = 1.2381 #np.mean([1.2534,1.2852])
T_c = 2833.63
p_c = 34.474*10**5
rho_c = 3.3826
a_c = np.sqrt(gamma*(1-1/gamma)*200.07*T_c) 


#input variables from NASA CEA in metric units:
Pr=0.55645 #average throat to exit Prandtl's number
cp=1.724 #[KJ/KG-K] average throat to exit constant pressure heat capacity
c=0.003883468 #[millipoise/K^w] viscocity to temperature coefficient
w=0.678083301 #viscocity to temperature exponent

## CONSTANTS OF DESIGN FOR HEAT FLUX
#user input variable in metric units:
T_w=600 #[K] desired temperature of nozzle 


## CONSTANTS OF SIM
alpha = 1 #0.07/8 # 0.07/8 : 1 ratio of alpha : beta gives very similar weights
beta = 0
design_alt = 6000
truncate_ratio = 1.0# bounds on truncate < 0.1425

CEA = CEA_constants(gamma,T_c,p_c,rho_c,a_c,Pr,cp,c,w)

## CONVERTING TO OPTIMIZABLE FUNCTION

# def min_design_alt(X):
# 	return X[0] - 3000

# def max_design_alt(X):
# 	return -X[0] + 12000

# def min_truncate(X):
# 	return X[1] - 0.2

# def max_truncate(X):
# 	return -X[1] + 1

# cons = [{'type':'ineq', 'fun':min_design_alt},{'type':'ineq', 'fun':max_design_alt},{'type':'ineq', 'fun':min_truncate},{'type':'ineq', 'fun':max_truncate}]


spike_init = design_angelino_nozzle(design_alt,truncate_ratio,CEA,r_e)

spike_opt = copy.deepcopy(spike_init)

def cost_opt(params) : return COST_FNC(params,spike_opt,T_w,CEA,alpha,beta,chr_mesh_n=120,no_core=4) # (x_vals,y_vals,spike,T_w,CEA,alpha,beta,chr_mesh_n=145,no_core=4)

print(cost_opt([spike_opt.x,spike_opt.y]))

#res = scipy.optimize.minimize(cost_opt,[spike_opt.x,spike_opt.y])#,constraints = cons)

# with open('spike_opt.pkl','wb') as output:
# 	pickle.dump(spike_opt,output,pickle.HIGHEST_PROTOCOL)

# with open('spike_points.pkl','wb') as output:
# 	pickle.dump(res,output,pikcle.HIGHEST_PROTOCOL)

# with open('meshes.pkl','rb') as input:
# 	meshes = pickle.load(input)

# minmizer_kwargs = {"constraints":cons}

# res = scipy.optimize.basinhopping(cost_lambda,[design_alt,truncate_ratio],minimizer_kwargs=minmizer_kwargs)
# print(res)