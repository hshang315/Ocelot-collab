import numpy
from numpy import unravel_index
from .activation import Activation
from .layer import Layer


class Parametrize(Layer):
	def __init__(self,type="oscillate",w=1.0):
		self.trainable = False
		self.w=w
		if type=="oscillate":
			self.forward,self.backward=self.forward_osc,self.backward_osc
	def forward_osc(self,X):
		self.inp=X
		self.out=numpy.concatenate([numpy.sin(self.w*X),numpy.cos(self.w*X)],1)
		return self.out
	def backward_osc(self,err):
		return self.w*err[:,[0]]*numpy.cos(self.w*self.inp) -self.w*err[:,[1]]*numpy.sin(self.w*self.inp)
	
class Scale(Layer):
	def __init__(self,fixed=False,init_vals=None):
		self.fixed=fixed
		self.trainable=True
		self.init_vals=init_vals
		self.activation=None
		#assert( not ( (not fixed) and (init_vals is None) ) )
	
	def initialize_ws(self):
		self.n_out = self.n_inp
		if self.init_vals is None:
			self.W=numpy.ones((1,self.n_inp))
			self.init_vals=self.W
		else:
			#assert(len(init_vals)==self.n_inp or type)
			self.W=numpy.ones((1,self.n_inp))*self.init_vals
		self.b=numpy.zeros((1,self.n_inp))
		self.dW=numpy.zeros_like(self.W)
		self.db=numpy.zeros_like(self.b)
		
	def forward(self,X):
		self.inp=X
		self.out=self.init_vals*X
		if not self.fixed:
			self.out=self.W*X
		
		return self.out
	def backward(self,err):
		if not self.fixed:
			self.dW=numpy.sum(err*self.inp,0).reshape(1,-1)
			
		return self.W*err

class Dense(Layer):
	def __init__(self,n_out,activation=None,mask=None):
		self.n_out=n_out
		self.activation=activation
		self.trainable=True
		self.mask = mask 

	def save_ws(self, dname, layer_num):
		prefix = '{0}/layer{1}_'.format(dname,layer_num)
		numpy.savetxt(prefix+'W', self.W)
		numpy.savetxt(prefix+'b', self.b)

	def load_ws(self, dname, layer_num):
		prefix = '{0}/layer{1}_'.format(dname,layer_num)
		self.W = numpy.loadtxt(prefix+'W')
		self.b = numpy.loadtxt(prefix+'b')
      
	def initialize_ws(self):
		if self.mask is None:
			self.mask = numpy.ones((self.n_inp,self.n_out))
		self.W=numpy.random.randn(self.n_inp,self.n_out)*numpy.sqrt(1.0/self.n_inp)*self.mask
		self.b=numpy.zeros((1,self.n_out))
		self.dW=numpy.zeros((self.n_inp,self.n_out))
		self.db=numpy.zeros((1,self.n_out))
	def forward(self,X):
		self.inp=X
		self.out=numpy.dot(self.inp,self.W)+self.b
		return self.out
	def backward(self,err):
		
		self.db=numpy.sum(err,axis=0).reshape(1,-1)
		self.dW=numpy.dot(self.inp.T, err) * self.mask

		return numpy.dot(err,self.W.T) 

class CovMat(Layer):
	def __init__(self,alpha=1e-1,var=1.0,kernel='rbf',alpha_fixed=False):

		self.trainable=True
		self.s_alpha=alpha
		self.var = var
		self.activation=None
		self.alpha_fixed=alpha_fixed
		self.kernel=kernel
		if kernel=='rbf':
			self.forward,self.backward = self.forward_rbf,self.backward_rbf
		elif kernel == 'dot':
			self.forward,self.backward = self.forward_dot,self.backward_dot
		self.predict=self.forward
	def initialize_ws(self):
		self.W=numpy.ones((1,2))*numpy.array([[numpy.log(self.s_alpha/(1.0-self.s_alpha)),numpy.sqrt(self.var)]])
		self.b=numpy.zeros((1,1))
		self.dW=numpy.zeros((1,2))
		self.db=numpy.zeros((1,1))
	
	
	def forward_dot(self,X):
		self.inp=X
		
		#Dot product
		self.s0=numpy.dot(X,X.T)
		
		#Add variance (or alpha0)
		self.var=self.W[0,1]**2
		self.s0 = self.s0+self.var
		
		#Add noise
		self.s_alpha=1.0/(numpy.exp(-self.W[0,0])+1.0)
		self.s=self.s0+numpy.identity(X.shape[0])*(self.s_alpha+1e-8)
		
		self.out=self.s
		return self.out
	def backward_dot(self,err):
		if not self.alpha_fixed:
			a_err=err*self.s_alpha*(1.0-self.s_alpha)
			self.dW[0,0]=numpy.mean(numpy.diag(a_err))#*err.shape[0]
			self.dW[0,1]=numpy.sum(err)*2*self.W[0,1]/err.shape[0]
		
		#Backpropagate through dot product:
		err2=2.0*numpy.dot(err,self.inp)/err.shape[0]#/err.shape[0]
		return err2
	def forward_rbf(self,X):
		self.inp=X
		
		#Calculate distances
		ll=[]
		for i in range(0,X.shape[1]):
			tmp=X[:,i].reshape(1,-1)-X[:,i].reshape(-1,1)
			ll.append(tmp.reshape(X.shape[0],X.shape[0],1))
		self.z=numpy.concatenate(ll,-1)
		
		#Apply RBF function to distance
		self.s0=numpy.exp(-0.5*numpy.sum(self.z**2,-1))
		
		#Multiply with variance
		self.var=self.W[0,1]**2
		self.s=self.var*self.s0
		
		#Add noise / whitekernel
		self.s_alpha=1.0/(numpy.exp(-self.W[0,0])+1.0)
		self.out=self.s+(self.s_alpha+1e-8)*numpy.identity(X.shape[0])
		return self.out
		
		
	def backward_rbf(self,err):
		#Update trainable weight gradients (if applicable) I.e. noise and variance.
		if not self.alpha_fixed:
			a_err=err*self.s_alpha*(1.0-self.s_alpha)
			self.dW[0,0]=numpy.mean(numpy.diag(a_err))
			self.dW[0,1]=numpy.mean(err*self.s0)*err.shape[0]*2.0*self.W[0,1]
			
		#Backprop through multiplication with variance
		err=self.var*err
		
		#Backprop through RBF function
		err=-err[:,:,numpy.newaxis]*self.z*self.s0[:,:,numpy.newaxis]
		
		#Backprop through distance calculation
		err2=numpy.zeros_like(self.inp)
		X=self.inp
		for i in range(0,X.shape[1]):
			err2[:,i]=numpy.sum(err[:,:,i]-err[:,:,i].T,0)/X.shape[0]
			
		return err2

class RNNCell(Layer):
	def __init__(self,n_out,activation='tanh',return_seq=False):
		self.n_out=n_out
		self.trainable=True
		self.activation=activation
		self.rs=return_seq
	def initialize_ws(self):
		self.W=numpy.random.randn(self.n_inp+self.n_out,self.n_out)
		self.W[0:self.n_inp,:]/=numpy.sqrt(self.n_inp)
		#self.W[self.n_inp::,:]/=(10.0*numpy.sqrt(self.n_out))
		self.W[self.n_inp::,:]=numpy.identity(len(self.W[self.n_inp::]))/numpy.sqrt(self.n_inp)
		self.b=numpy.zeros((1,self.n_out))#0.0
		self.dW=numpy.zeros((self.n_inp+self.n_out,self.n_out))
		self.db=numpy.zeros((1,self.n_out))#0.0
		self.init_run=True
		
	def forward(self,X):
		if self.init_run:
			self.afs=[]
			for i in range(0,len(X[0,:,0])):
				self.afs.append(Activation(self.activation))
			self.init_run=False
		
		self.inp=X
		
		self.tmp=numpy.zeros((X.shape[0],X.shape[1],self.n_out))

		
		tmpX=X.reshape(X.shape[0]*X.shape[1],X.shape[2])
		
		self.tmp[:,0,:]=numpy.dot(X[:,0,:],self.W[0:self.n_inp,:])+self.b
		self.tmp[:,0,:]=self.afs[0].forward(self.tmp[:,0,:])
		
		for i in range(1,len(X[0,:,0])):
			self.tmp[:,i,:]= numpy.dot(self.tmp[:,i-1,:],self.W[self.n_inp::,:])+numpy.dot(X[:,i,:],self.W[0:self.n_inp,:])+self.b 
			self.tmp[:,i,:]=self.afs[i].forward(self.tmp[:,i,:])
			
		if self.rs:
			self.out=self.tmp
		else:
			self.out=self.tmp[:,-1,:]

		return self.out
		
	def backward(self,err):
		if self.rs:
			erra=numpy.zeros_like(self.inp)
			self.dW=numpy.zeros((self.n_inp+self.n_out,self.n_out))
			self.db=numpy.zeros((1,self.n_out))
			for j in range(0,len(err[0,:,0])):
				
				errs=err[:,j,:]
				for i in reversed(range(1,j+1)):
					errs=self.afs[i].backward(errs)
					erra[:,i,:]+=numpy.dot(errs,self.W[0:self.n_inp,:].T)
					self.dW[0:self.n_inp,:]+=numpy.dot(errs.T,self.inp[:,i,:]).T
					self.db+=numpy.sum(errs,0).reshape(1,-1)
					self.dW[self.n_inp::,:]+=numpy.dot(errs.T,self.tmp[:,i-1,:]).T
					errs=numpy.dot(errs,self.W[self.n_inp::,:].T)
				
				errs=self.afs[0].backward(errs)
				erra[:,0,:]+=numpy.dot(errs,self.W[0:self.n_inp,:].T)
				self.db+=numpy.sum(errs,0).reshape(1,-1)
				self.dW[0:self.n_inp,:]+=numpy.dot(errs.T,self.inp[:,0,:]).T

		else:
			self.dW=numpy.zeros((self.n_inp+self.n_out,self.n_out))
			self.db=numpy.zeros((1,self.n_out))
			erra=numpy.zeros_like(self.inp)
			for i in reversed(range(1,len(self.inp[0,:,0]))):
				err=self.afs[i].backward(err)
				erra[:,i,:]=numpy.dot(err,self.W[0:self.n_inp,:].T)
				self.dW[0:self.n_inp,:]+=numpy.dot(err.T,self.inp[:,i,:]).T
				self.db+=numpy.sum(err,0).reshape(1,-1)
				self.dW[self.n_inp::,:]+=numpy.dot(err.T,self.tmp[:,i-1,:]).T
				err=numpy.dot(err,self.W[self.n_inp::,:].T)
			
			err=self.afs[0].backward(err)
			erra[:,0,:]=numpy.dot(err,self.W[0:self.n_inp,:].T)
			self.db+=numpy.sum(err,0).reshape(1,-1)
			self.dW[0:self.n_inp,:]+=numpy.dot(err.T,self.inp[:,0,:]).T
		
			

		return erra

		
