import numpy as np 
import matplotlib.pyplot as plt 

from numpy import dot, multiply, diag, power
from numpy.linalg import inv, eig, pinv

from scipy.linalg import svd, svdvals


class dmd():
    def __init__(self, Dat ,dt , h , rank , add_time_for_pred , show_dmd):

        #基本設定
        self.Dat = Dat 
        self.N = np.shape( Dat )[0] - 1 
        self.ny = np.shape( Dat )[1]
        self.nx = np.shape( Dat )[2]
        self.dt = dt
        self.h = h 
        self.rank = rank 
        self.add_time_for_pred = add_time_for_pred
        self.show_dmd = show_dmd
        
        x_tmp = np.arange( self.nx )
        y_tmp = np.arange( self.ny )
        self.x , self.y = np.meshgrid( x_tmp , y_tmp )


    def next_steps(self):
        #タイムステップを進める
        self.tt += self.dt

    def createmat(self , X , N , h ):
        #モード分解を行うためのinputデータを作成
        p1 = np.array([])
        p2 = np.array([])

        x_size = np.size( X[0] )

        for i in range( N - h + 1 ):
            print( i , "/", N - h )
            for j in range(h):
                p1 = np.append( p1 , X[i + j ] ) 
                p2 = np.append( p2 , X[i + j + 1 ] ) 
            
        p1 = np.reshape( p1 , ( N- h + 1 , x_size * h) )
        p1 = np.transpose(p1)
        p2 = np.reshape( p2 , ( N- h + 1 , x_size * h) )
        p2 = np.transpose(p2)

        return p1 , p2 
    
    
    def mode_decomposing(self , p1 , p2  , rank ):
        #モード分解
        self.U2 , self.Sig2 , self.Vh2 = svd( p1 , False)
        U = self.U2[:,:rank]
        Sig = np.diag(self.Sig2)[:rank,:rank]
        V = self.Vh2.conj().T[:,:rank]

        F =  np.dot( np.dot( np.dot( U.conj().T , p2 ) , V  ) , np.linalg.pinv( Sig ) ) 
        mu,W = eig(F)

        phi = np.dot( U , W )
        #phi = dot(dot(dot( p2, V), inv(Sig)), W) #記事2に詳述
        
        return  mu,phi
    

    def check_mode(self, phi ,tate , yoko , rank ):

        fig, ax = plt.subplots( tate, yoko )
        dd_out = [] 

        mode_num = 0 
        for i in range(tate):
            for j in range(yoko):
                #for mode_num in range(rank):
                if mode_num < rank:
                    dd = phi[: self.ny * self.nx , mode_num ]
                    dd = np.reshape( dd , ( self.ny , self.nx ) )
            
                    ax[ i ,j ].contourf( self.x , self.y , dd  , levels = 10 , cmap = 'twilight_shifted')
                    mode_num += 1 
                    
                    dd_out.append( dd )
                            
        #グラフを表示する
        if self.show_dmd == True:
            plt.show()
            
        return dd_out
            


    def apply_dmdmode(self , mu , phi , init_val , rank , d_length , dt_in , add_time ): #dtを後で変更=>内挿、精度を確認
        tt = np.arange( 0 , ( d_length + add_time ) * dt_in  , dt_in )

        b = dot(pinv(phi), init_val )
        Psi = np.zeros([rank, len(tt)], dtype='complex')
        for i,_t in enumerate(tt):
            Psi[:,i] = multiply( power(mu, _t/ self.dt ), b )

        return np.dot( phi , Psi )


    def check_proportion_val(self):
        #寄与率をチェックして、使用するモードを検討する為のツール
        fig, ax = plt.subplots()
        scatter = ax.scatter( range(0, len(self.Sig2)), self.Sig2, label="SVD" )
        print(type(scatter))
        plt.show()


    def plot(self , val ):
        h = plt.contourf( self.x , self.y , val  , levels = 10 , cmap = 'twilight_shifted')
        #h = plt.contourf( self.x , self.y , val , vmin = -1.0 , vmax = 1.0 , levels = 10 , cmap = 'twilight_shifted')
        plt.axis('scaled')
        plt.colorbar()
        plt.show()
        
        
    
    def reshape_vv(self , VV ): 
        #予測データを( time , ny , nx )の形式に変換する
        VV_re = []
        for i in range( np.shape(VV)[2] ):
            VV_re.append( VV[:,:,i] )
            
            
        return VV_re
        
    
    def exec(self ):
        p1 , p2 = self.createmat( self.Dat , self.N , self.h )
        mu , phi = self.mode_decomposing( p1 , p2 , self.rank )
        
        # self.check_proportion_val() #モード寄与率を確認
        print( "amplitude" , np.real( np.log(mu)) / 1.0 ) #0.005 = dt
        print( "frequency" , np.imag( np.log(mu)) / 1.0 ) #0.005 = dt
        dd_mode = self.check_mode( phi , 3, 3 , self.rank ) #モードを可視化 (phi,tate,yoko) =>tate × yoko  = rank
        
        VV = self.apply_dmdmode( mu , phi , p1[:,0] , self.rank , self.N , self.dt , self.add_time_for_pred ) #モードからデータを再現
        VV = VV[ : self.nx * self.ny  , : ] #下半分は無視
        VV = np.reshape( VV , ( self.ny , self.nx , np.shape(VV)[1] ) )
    
        VV2return = self.reshape_vv( VV )
        
        return VV2return , dd_mode 
    
