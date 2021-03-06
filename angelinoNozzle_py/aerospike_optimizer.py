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
	def __init__(self,altitude):
		"""Class that should eventually queery NASA CEA data, for now holds all values constant

		Args:
			altitude (float): altitude in meters

		Returns:
			Stores NASA CEA data in atributes
		"""	
		self.gamma = 1.237 #np.mean([1.2534,1.2852])
		self.T_c = 2831.47 # combustion chamber temperature
		self.p_c = 3102640.8 # combustion chamber pressure
		self.rho_c = 3.3826 # combustion chamber density 
		self.a_c = np.sqrt(self.gamma*(1-1/self.gamma)*200.07*self.T_c) # combustion chamber sound speed
		self.Pr = 0.55645 #average throat to exit Prandtl's number
		self.cp = 1.724 #[KJ/KG-K] average throat to exit constant pressure heat capacity
		self.c = 0.003883468 #[millipoise/K^w] viscocity to temperature coefficient
		self.w = 0.678083301 #viscocity to temperature exponent


class aerospike_optimizer():
	"""Class intended to be used to optimize an aerospike nozzle

	Args:
		r_e (float): outer radius of aerospike nozzle
		T_w (float): desired nozzle temperatures
		alpha (float): weighting of thrust
		beta (float): weighting of cooling requirement
		design_alt_init (float): initial design altitude
		truncate_ratio_init (float): inital truncation length
		chr_mesh_n (int): number of expansion waves for MOC
		no_alt_range (float): number of altitude ranges to optimize over
		no_core (int>0): number of cores to be used in computation

	Returns:
		cost_opt_contour_params (float): cost computed with spike.x and spike.y as input parameters
		cost_opt_design_params (float): cost computed with design_alt and truncate_ratio as input parameters
	"""
	def __init__(self,r_e,T_w,alpha,beta,design_alt_init,truncate_ratio_init,chr_mesh_n=120,no_alt_range = 30,no_core=1):
		self.r_e = r_e
		self.T_w = T_w
		self.alpha = alpha
		self.beta = beta
		self.design_alt_init = design_alt_init
		self.truncate_ratio_init = truncate_ratio_init
		self.chr_mesh_n = chr_mesh_n
		self.no_alt_range_int = int(no_core*round(no_alt_range/no_core))
		self.no_core = no_core

		self.CEA = CEA_constants(0)		
		self.spike_init = self.__design_angelino_nozzle(design_alt_init,truncate_ratio_init,self.CEA,r_e)

		self.spike_opt = copy.deepcopy(self.spike_init)


	def __compute_thrust_over_range(self,plug_nozzle_class,alt_range,gamma,send_end,downstream_factor=1.2,chr_mesh_n=50):
		"""Function that computes the thrust at each point over a specified range, intended to be used as apart of a process

		Args: 
			plug_nozzle_class (class plug_nozzle_angelino.plug_nozzle): the plug nozzle for which the thrust is to be computed
			alt_range (np.array): discrete altitudes over which thrust should be computed
			gamma (float): ratio of specifc heats
			send_end (class multiprocessing.connection.Connection): part of recv_end, send_end pair indicating which recv_end to send to
			downstream_factor (float): specifies what factor downstream of the final contour point MOC should be continued up to
			chr_mesh_n (int>0): specifies number expansion waves at lip for MOC

		Returns:
			None
			send_end.send(thrust_range); thrust_range (np.array): contains thrust computed at each alt_range point

		"""
		thrust_range = np.zeros(alt_range.shape)
		for i in range(alt_range.shape[0]):
			# print(alt_range[i])
		
			MOC_mesh = MOC.chr_mesh(plug_nozzle_class,gamma,alt_range[i],chr_mesh_n,downstream_factor=downstream_factor)
			thrust_range[i] = MOC_mesh.compute_thrust('linear',200)
			print(thrust_range[i])
			# except:
			# 	print("goofs and gafs")
			# 	thrust_range[i] = 0
		send_end.send(thrust_range)

	def __multicore_thrust_compute(self,plug_nozzle_class,altitude_range,gamma,downstream_factor=1.2,chr_mesh_n=50,no_core=1):
		proc_list = []
		pipe_list =[]

		alt_range_split = np.split(altitude_range,no_core)

		for i in range(no_core):
			recv_end, send_end = mp.Pipe(False)
			args = (plug_nozzle_class,alt_range_split[i],gamma,send_end,downstream_factor,chr_mesh_n)
			proc = mp.Process(target=self.__compute_thrust_over_range, args = args)
			proc_list.append(proc)
			pipe_list.append(recv_end)
			proc.start()

		for proc in proc_list:
			proc.join()

		thrust_range = [x.recv() for x in pipe_list]

		thrust_range = np.concatenate(thrust_range)

		plt.plot(altitude_range,thrust_range,'o')
	
		# for thread in threads:
		# 	thread.map

		return thrust_range

	def __design_angelino_nozzle(self,design_alt,truncate_ratio,CEA,r_e):
		""" Can be a class function, will edit going forwards
		"""
		(p_atm,T_atm,rho_atm) = gd.standard_atmosphere([design_alt])

		PR = CEA.p_c/p_atm

		M_e = gd.PR_expansion_mach(PR,CEA.gamma)

		expansion_ratio = gd.expansion_ratio(1,M_e,CEA.gamma)#6.64 #8.1273
		# print('Exp. ratio: ' + str(expansion_ratio))
		# print('PR: ' + str(PR))

		A_t = r_e**2*np.pi/expansion_ratio # max expansion (r_b = 0, r_e**2 >= A_t*expansion_ratio/np.pi)

		return plug_nozzle(expansion_ratio,A_t,r_e,CEA.gamma,CEA.T_c,CEA.p_c,CEA.a_c,CEA.rho_c,1500,truncate_ratio = truncate_ratio)

	def __cost_end_func(self,no_alt_range_int,spike,CEA,downstream_factor=1.2,chr_mesh_n=120,no_core=1):
		alt_range = np.linspace(0,9144,no_alt_range_int)

		# shuffle arrays so each core computes similar complexity on average
		np.random.shuffle(alt_range)
		(p_atm_r,T_atm_r,rho_atm_r) = gd.standard_atmosphere(alt_range)

		thrust_range = self.__multicore_thrust_compute(spike,alt_range,CEA.gamma,downstream_factor=downstream_factor,chr_mesh_n=chr_mesh_n,no_core=no_core)

		# unshuffle arrays
		ordered_idx = np.argsort(alt_range)
		alt_range = alt_range[ordered_idx]; thrust_range = thrust_range[ordered_idx]

		work = np.trapz(thrust_range,alt_range)
		plt.plot(alt_range,thrust_range,'o')
		plt.show()
		print('work = ' + str(work))

		## heat transfer required
		total_heat_flux = heat_flux(CEA.Pr,CEA.cp,CEA.gamma,CEA.c,CEA.w,CEA.T_c,T_w,spike)

		return (work, total_heat_flux)

	def __cost_func_contour_params(self,params,spike,T_w,CEA,alpha,beta,chr_mesh_n,no_alt_range_int,no_core):
		params = np.asarray(params)
		if len(params.shape) > 1:
			raise ValueError('Input params not correct shape. Should be 1D array')
		x_vals,y_vals = np.split(params,2)	


		spike.x = x_vals; spike.y = y_vals


		work, total_heat_flux = self.__cost_end_func(no_alt_range_int,spike,CEA,downstream_factor=5.0,chr_mesh_n=chr_mesh_n,no_core=no_core)
		print('Total Heat = ' +str(total_heat_flux))
		return -alpha*work + beta*total_heat_flux
		
	def __cost_func_design_params(self,params,T_w,CEA,r_e,alpha,beta,chr_mesh_n,no_alt_range_int,no_core):
		params = np.asarray(params)
		if len(params.shape) > 1:
			raise ValueError('Input params not correct shape. Should be 1D array')
		design_alt, truncate_ratio = np.split(params,2)
		spike = self.__design_angelino_nozzle(design_alt,truncate_ratio,CEA,r_e)

		work, total_heat_flux = self.__cost_end_func(no_alt_range_int,spike,CEA,downstream_factor=1.2,chr_mesh_n=chr_mesh_n,no_core=no_core)
		print('work = ' + str(work))
		return -alpha*work + beta*total_heat_flux

	def cost_opt_contour_params(self,params): 
		"""params = np.concatenate((spike_opt.x,spike_opt.y))
		"""
		return self.__cost_func_contour_params(params,self.spike_opt,self.T_w,self.CEA,self.alpha,self.beta,self.chr_mesh_n,self.no_alt_range_int,self.no_core)

	def cost_opt_design_params(self,params): 
		"""params = [design_alt,truncation_ratio]
		"""
		return self.__cost_func_design_params(params,self.T_w,self.CEA,self.r_e,self.alpha,self.beta,self.chr_mesh_n,self.no_alt_range_int,self.no_core)

if __name__ == '__main__':

	## CONSTANTS OF DESIGN FOR AERODYNAMICS
	r_e = 0.027 #0.034 # likely too large

	## CONSTANTS OF DESIGN FOR HEAT FLUX
	#user input variable in metric units:
	T_w=600 #[K] desired temperature of nozzle 


	## CONSTANTS OF SIM
	alpha = 1#0.07/8 # 0.07/8 : 1 ratio of alpha : beta gives very similar weights
	beta = 0#1
	design_alt = 9144
	truncate_ratio = 1# bounds on truncate < 0.1425

	CEA = CEA_constants(0) # not a functioning class as of now

	optimizer = aerospike_optimizer(r_e,T_w,alpha,beta,design_alt,truncate_ratio,chr_mesh_n=150,no_alt_range =16,no_core=4)



	def old_vs_new_spike():
		optimizer = aerospike_optimizer(r_e,T_w,alpha,beta,design_alt,truncate_ratio,chr_mesh_n=100,no_alt_range = 32,no_core=4)

		contours = np.concatenate((optimizer.spike_opt.x,optimizer.spike_opt.y))

		#optimizer_old = aerospike_optimizer(r_e,T_w,alpha,beta,6000,truncate_ratio,chr_mesh_n=120,no_alt_range=32,no_core=4)

		optimizer_old = aerospike_optimizer(r_e,T_w,alpha,beta,6000,truncate_ratio,chr_mesh_n=100,no_alt_range = 32,no_core=4)

		contours = np.concatenate((optimizer_old.spike_opt.x,optimizer_old.spike_opt.y))

		#optimizer_old = aerospike_optimizer(r_e,T_w,alpha,beta,6000,truncate_ratio,chr_mesh_n=120,no_alt_range=32,no_core=4)

		# print(optimizer_old.cost_opt_contour_params(contours))
		# print(optimizer.cost_opt_contour_params(contours))


		#print(optimizer.cost_opt_design_params([design_alt,truncate_ratio]))
		#plt.legend()

		plt.plot(optimizer.spike_init.x,optimizer.spike_init.y,'b-',optimizer.spike_init.lip_x,optimizer.spike_init.lip_y,'bx',label='Optimized Spike')
		plt.plot(optimizer_old.spike_init.x,optimizer_old.spike_init.y,'r--',optimizer_old.spike_init.lip_x,optimizer_old.spike_init.lip_y,'rx',label='Old Spike')
		plt.plot([optimizer_old.spike_init.x[-1],optimizer_old.spike_init.x[-1]],[optimizer_old.spike_init.y[-1],0],'r--')
		plt.plot([optimizer.spike_init.x[-1],optimizer.spike_init.x[-1]],[optimizer.spike_init.y[-1],0],'b-')
		plt.plot(optimizer.spike_init.x,np.zeros(optimizer.spike_init.x.shape),'k-')
		plt.axis('equal')
		plt.legend()
		plt.show()

# def cost_opt_design_params(params) : return cost_func_design_params(params,T_w,CEA,r_e,alpha,beta,chr_mesh_n=30,no_core=4)
	
	# old_vs_new_spike()

	optimizer.cost_opt_design_params([design_alt,truncate_ratio])
# print(cost_opt_contour_params(np.concatenate((spike_opt.x,spike_opt.y))))

#res = scipy.optimize.minimize(optimizer.cost_opt_contour_params,contours)#,constraints = cons)

# with open('spike_opt.pkl','wb') as output:
# 	pickle.dump(spike_opt,output,pickle.HIGHEST_PROTOCOL)

# with open('spike_points.pkl','wb') as output:
# 	pickle.dump(res,output,pikcle.HIGHEST_PROTOCOL)

# with open('meshes.pkl','rb') as input:
# 	meshes = pickle.load(input)


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

# minmizer_kwargs = {"constraints":cons}

# res = scipy.optimize.basinhopping(cost_lambda,[design_alt,truncate_ratio],minimizer_kwargs=minmizer_kwargs)
# print(res)