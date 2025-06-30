import os 
import numpy as np 
import pandas as pd 
from ctypes import *

import matplotlib.pyplot as plt 

class DIR:
    def __init__(self ):
        libfile = 'direct_analysis' + os.sep + 'calc_direct.so'
        so_abspath = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + libfile       
        self.libs = np.ctypeslib.load_library( so_abspath , "." )

        #計算メッシュサイズを送る
        self.set_meshsize = self.libs.set_mesh_size
        self.set_meshsize.argtypes = [ 
            np.ctypeslib.ndpointer(dtype=np.int32),     #i_mesh
            np.ctypeslib.ndpointer(dtype=np.int32) ]    #j_mesh
        self.set_meshsize.restype = c_void_p            

        #生息分布を送る
        self.set_existmat = self.libs.set_existmat        
        self.set_existmat.argtypes = [ np.ctypeslib.ndpointer(dtype=np.float64) ] #existence

        #dir matを受け取る
        self.get_dirmat = self.libs.get_dirmat
        self.get_dirmat.argtypes = [ 
            np.ctypeslib.ndpointer(dtype=np.int32) ,  #dir_mat(result)
            np.ctypeslib.ndpointer(dtype=np.int32),     #i_mesh
            np.ctypeslib.ndpointer(dtype=np.int32) ]    #j_mesh
        self.get_dirmat.restype = c_void_p    

    #実行
    def exec( self , existence_mat , check ):
        # existence_mat は　2次元配列 (ndarray)
        # 注意：fortranコードとpythonコードでは配列順番が変わる。dat[ i, j ] -> dat[ j , i ]
        i_no , j_no = existence_mat.shape
        dir_tmp = np.array( np.empty( ( int( i_no ) , int( j_no ) ) ), dtype='int32' ) 

        #配列サイズを送る（順番は変えて送る）
        self.set_meshsize( np.array( j_no , dtype = 'int32' ) ,
                           np.array( i_no , dtype = 'int32' )   ) 
        #生息分布を送る
        self.set_existmat( np.array( existence_mat ,
                                     dtype= 'float64' ) )

        #計算を実行
        self.get_dirmat(  dir_tmp , 
                          np.array( j_no , dtype = 'int32' ) ,  
                          np.array( i_no , dtype = 'int32' ) )
        
        if check == True:
            self.check_countor( i_no , j_no , dir_tmp )

        return dir_tmp 


    #計算結果を可視化する    
    def check_countor(self , i_no , j_no , z ):
        fig, ax = plt.subplots()
        x_tmp = np.arange( j_no )
        y_tmp = np.arange( i_no )
        gridX , gridY = np.meshgrid( x_tmp , y_tmp ) 

        im = ax.contourf(  gridX , gridY , z )
        fig.colorbar(im)
        plt.show()   