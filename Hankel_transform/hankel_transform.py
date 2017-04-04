from scipy.special import jn, jn_zeros
from scipy.interpolate import interp1d
import numpy as np

class hankel_transform():
    def __init__(self,rmin=0.1,rmax=100,kmax=10,kmin=1.e-4,n_zeros=1000,n_zeros_step=1000,
                 j_nu=[0,2]):
        self.rmin=rmin
        self.rmax=rmax
        self.kmax=kmax
        self.kmin=kmin
        self.n_zeros=n_zeros
        self.n_zeros_step=n_zeros_step
        self.k={}
        self.r={}
        self.J={}
        self.J_nu1={}
        self.zeros={}
        for i in j_nu:
            self.k[i],self.r[i],self.J[i],self.J_nu1[i],self.zeros[i]=self.get_k_r_j(j_nu=i,
                                                   n_zeros=n_zeros,rmin=rmin,rmax=rmax,
                                                   kmax=kmax,kmin=kmin,n_zeros_step=n_zeros_step)

    def get_k_r_j(self,j_nu=0,n_zeros=1000,rmin=0.1,rmax=100,kmax=10,kmin=1.e-4,n_zeros_step=1000):
        while True:
            zeros=jn_zeros(j_nu,n_zeros)
            k=zeros/zeros[-1]*kmax
            r=zeros/kmax
            if min(r)>rmin:
                kmax=min(zeros)/rmin
                print 'changed kmax to',kmax,' to cover rmin'
                continue
            elif max(r)<rmax:
                n_zeros+=n_zeros_step
                print 'j-nu=',j_nu,' not enough zeros to cover rmax, increasing by ',n_zeros_step,' to',n_zeros
            elif min(k)>kmin:
                n_zeros+=n_zeros_step
                print 'j-nu=',j_nu,' not enough zeros to cover kmin, increasing by ',n_zeros_step,' to',n_zeros
            else:
            #print n_zeros
                break
        x=r<rmax
        x*=r>rmin
        r=r[x]
        J=jn(j_nu,np.outer(r,k))
        J_nu1=jn(j_nu+1,zeros)
        return k,r,J,J_nu1,zeros

    def projected_correlation(self,k_pk=[],pk=[],j_nu=[],kmax=[],rmax=[],rmin=[],
                              n_zeros=[],taper=False,**kwargs):
        if taper:
            pk=self.taper(k=k_pk,pk=pk,**kwargs)
        if k_pk==[]:#In this case pass a function that takes k with kwargs and outputs pk
            pk2=pk(k=self.k[j_nu],**kwargs)
        else:
            pk_int=interp1d(k_pk,pk,bounds_error=False,fill_value=0,
                            kind='linear')
            pk2=pk_int(self.k[j_nu])
        
        w=np.dot(self.J[j_nu],pk2/self.J_nu1[j_nu]**2)
        print pk2
        w*=(2.*self.kmax**2/self.zeros[j_nu][-1]**2)/(2*np.pi)
        return self.r[j_nu],w

    def projected_covariance(self,k_pk=[],pk1=[],pk2=[],j_nu=[],kmax=[],rmax=[],rmin=[],                n_zeros=[],taper=False,**kwargs):
        #print 'projected-covariance, j=',j_nu,'r-minmax',self.rmin,self.rmax,self.kmax
        if taper:
            pk1=self.taper(k=k_pk,pk=pk1,**kwargs)
            pk2=self.taper(k=k_pk,pk=pk2,**kwargs)
        pk1_int=interp1d(k_pk,pk1,bounds_error=False,fill_value=0,
                         kind='linear')
        pk1=pk1_int(self.k[j_nu])
        pk2_int=interp1d(k_pk,pk2,bounds_error=False,fill_value=0
                         ,kind='linear')
        pk2=pk2_int(self.k[j_nu])
        cov=np.dot(self.J[j_nu],(self.J[j_nu]*pk1*pk2/self.J_nu1[j_nu]**2).T)
        cov*=(2.*self.kmax**2/self.zeros[j_nu][-1]**2)/(2*np.pi)
        return self.r[j_nu],cov

    def taper(self,k=[],pk=[],large_k_lower=10,large_k_upper=100,low_k_lower=0,low_k_upper=1.e-5):
        pk_out=np.copy(pk)
        x=k>large_k_lower
        pk_out[x]*=np.cos((k[x]-large_k_lower)/(large_k_upper-large_k_lower)*np.pi/2.)
        x=k>large_k_upper
        pk_out[x]=0
        x=k<low_k_upper
        pk_out[x]*=np.cos((k[x]-low_k_upper)/(low_k_upper-low_k_lower)*np.pi/2.)
        x=k<low_k_lower
        pk_out[x]=0
        return pk_out

    def corr_matrix(self,cov=[]):
        corr=np.zeros_like(cov)
        n_bins=len(cov)
        for i in np.arange(n_bins):
            for j in np.arange(n_bins):
                corr[i][j]=cov[i][j]/np.sqrt(cov[i][i]*cov[j][j])
        corr=np.nan_to_num(corr)
        return corr

    def diagonal_err(self,cov=[]):
        return np.sqrt(np.diagonal(cov))

    def bin_cov(self,r=[],cov=[],r_bins=[]):
        bin_center=np.sqrt(r_bins[1:]*r_bins[:-1])
        n_bins=len(bin_center)
        cov_int=np.zeros((n_bins,n_bins),dtype='float64')
        norm_int=np.zeros((n_bins,n_bins),dtype='float64')
        for i in np.arange(n_bins):
            xi=r>r_bins[i]
            xi*=r<r_bins[i+1]
            ri=r[xi]
            if sum(xi)>1:
                ri2=np.sort(np.append(ri,[r_bins[i],r_bins[i+1]]))
                dri=np.gradient(ri2)[1:-1]
            else:
                dri=r_bins[i+1]-r_bins[i]
            for j in np.arange(n_bins):
                xj=r>r_bins[j]
                xj*=r<r_bins[j+1]
                rj=r[xj]
                if sum(xj)>1:            
                    rj2=np.sort(np.append(rj,[r_bins[j],r_bins[j+1]]))
                    drj=np.gradient(rj2)[1:-1]
                else:
                    drj=r_bins[j+1]-r_bins[j]
                #print r_bins[j],r_bins[j+1],sum(xj)
                covij=cov[xi,:][:,xj]
                norm_int[i][j]=np.sum(ri*dri)*np.sum(rj*drj)
                if norm_int[i][j]==0:
                    continue
                cov_int[i][j]=np.sum((covij*np.outer(ri*dri,rj*drj)).flatten())/norm_int[i][j]
        cov_int=np.nan_to_num(cov_int)
        #corr=corr_matrix(cov=cov_int)
        return bin_center,cov_int
