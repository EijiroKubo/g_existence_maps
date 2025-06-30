import os 
import numpy as np 
import pandas as pd 
from datetime import datetime, timedelta
from ctypes import * 

import matplotlib.pyplot as plt 


class calc_existence_model1():
    def __init__(self , data , crs , sigma_amp , ll ):
        '''
        データ（レコード）数:data_num
        データ:data        (geopandas dataframe)
        データcrs: crs 
        空間分布のシグマ（空間広がり度）：sigma(2・2対角行列)
        時間分布のλ：ll
        
        '''
        self.data_num = np.shape( data )[0]
        self.data = data 
        self.crs = crs 
        
        self.sigma = np.array( [ 1, 0 , 0, 1 ] ).reshape((2,2)) * sigma_amp #単位行列×sigma_amp
        self.ll = ll
            
    
    #計算領域の範囲を指定    
    def set_bound_and_grid( self , x_min , x_max , y_min , y_max , buff_meter , delta_mesh ):

        self.x_bound = [ x_min - buff_meter , x_max + buff_meter ]  
        self.y_bound = [ y_min - buff_meter , y_max + buff_meter ]
        
        x_position = np.arange( self.x_bound[0] , self.x_bound[1] , delta_mesh )
        y_position = np.arange( self.y_bound[0] , self.y_bound[1] , delta_mesh )
        
        self.grid_x , self.grid_y = np.meshgrid(x_position , y_position )  
    

    #各データの観測日からの経過時間を計測
    def deltatimes( self ):
        datetime_data = pd.to_datetime( self.data.iloc[:,0] ) #取得データの日付をdatetime型に変換
        dt = datetime.now() - datetime_data.dt.to_pydatetime()
        
        day = []
        for i in dt:
            day.append( ( i.days * 86400  + i.seconds )  / 86400 )
        return day
        
        
    #生息分布を計算
    def calc_existence_proj(self , time_buff , check_view) : 
        
        passedtimes = self.deltatimes()  #計算用経過時間(単位：日)
        x_tmp = self.grid_x.flatten()
        y_tmp = self.grid_y.flatten()        
        
        xy_data = np.vstack( (self.data.geometry.x , self.data.geometry.y) ) #観測地点のxy座標
        
        
        for n in range( self.data_num ):
            xy_tmp = np.vstack( (x_tmp - xy_data[0,n], y_tmp - xy_data[1,n] ) ) #計算用グリッド座標                            
            
            #passedtimes - time_buff < 0 のデータは反映しない
            if passedtimes[n] + time_buff < 0:
                usability = 0 
            else: 
                usability = 1 
            
            #P_tmp = 時間分布×空間分布
            P = np.exp( -1.0 * ( passedtimes[n] + time_buff ) * self.ll ) * \
                np.exp( -1.0 * np.diag(  xy_tmp.T @ np.linalg.inv( self.sigma ) @  xy_tmp  ) ) * \
                usability
                    
            P = np.reshape( P , (np.shape(self.grid_x)[0] , np.shape(self.grid_x)[1] ) )#メッシュサイズに変形
            
            if n == 0:                 
                z = P
        
            else: 
                z = z + P
        
                
        #生息分布をチェックする
        def check_response_surface( gridX , gridY , z_interpolate , point_x , point_y , point_z ):
            fig, ax = plt.subplots()

            im = ax.contourf(  gridX , gridY ,  z_interpolate )
            fig.colorbar(im)
            ax.scatter( point_x , point_y , s=30 ,  c = 'w' ,linewidths=1 , ec = 'k' ) #c = point_z 
            plt.show()        
        
        #生息分布データのチェック
        if check_view == True :             
            check_response_surface( self.grid_x , 
                                    self.grid_y , 
                                    z ,
                                    self.data.geometry.x , 
                                    self.data.geometry.y , 
                                    np.ones(self.data_num) )            
            
        return z #結果を返す
            
    
    #数日先の縮退を想定したマップ
    def predict_mat(self , days_buff ):        
        z = np.array([])
        
        for buff in days_buff:
            print( "days buff:" , buff )
            z_tmp = self.calc_existence_proj( buff, None )
            z = np.append( z , z_tmp )
            
        z = np.reshape( z , ( np.size(days_buff) , np.shape(z_tmp)[0] , np.shape(z_tmp)[1] ) )
        
        return z 
        
        
class calc_existence_model2():
    def __init__(self , data , crs , sigma_amp , ll , C_coff , D_coff , threads ):
        '''
        データ（レコード）数:data_num
        データ:data        (geopandas dataframe)
        データcrs: crs 
        空間分布のシグマ（空間広がり度）：sigma(2・2対角行列)
        時間分布のλ：ll
        '''       
        self.data_num = np.shape( data )[0]
        self.data = data 
        self.crs = crs         
        self.sigma = sigma_amp 
        self.ll = ll
        self.C_coff = C_coff 
        self.D_coff = D_coff 
        self.threads = threads
        
        #以下、shared object=============================================================
        libfile = 'existence_analysis' + os.sep + 'calc_existence.so'
        so_abspath = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + libfile       
        self.libs = np.ctypeslib.load_library( so_abspath , "." )
        
        #計算メッシュデータを送る
        self.set_meshdata = self.libs.set_mesh_data
        self.set_meshdata.argtypes = [ 
            np.ctypeslib.ndpointer(dtype=np.int32),     #i_mesh
            np.ctypeslib.ndpointer(dtype=np.int32),     #j_mesh
            np.ctypeslib.ndpointer(dtype=np.int32),     #timesteps 
            np.ctypeslib.ndpointer(dtype=np.float64),   #grid_x
            np.ctypeslib.ndpointer(dtype=np.float64),   #grid_y
            ] 
        self.set_meshdata.restype = c_void_p                    
        
        #観測データを送る
        self.set_obsdata = self.libs.set_observation
        self.set_obsdata.argtypes = [ 
            np.ctypeslib.ndpointer(dtype=np.int32),     # obsdata_number
            np.ctypeslib.ndpointer(dtype=np.float64),   # observation data
            ] 
        self.set_obsdata.restype = c_void_p           
        
        #計算パラメータを送る
        self.set_parameter = self.libs.set_parameters
        self.set_parameter.argtypes = [ 
            np.ctypeslib.ndpointer(dtype=np.float64),   # sigma
            np.ctypeslib.ndpointer(dtype=np.float64),   # C_cofficient
            np.ctypeslib.ndpointer(dtype=np.float64),   # D_cofficient
            np.ctypeslib.ndpointer(dtype=np.int32),     # parallel thread
            ] 
        self.set_parameter.restype = c_void_p         

        #計算を実行する
        self.calc_fp = self.libs.calc_existence_fokkerplanck
        self.calc_fp.argtypes = [ 
            np.ctypeslib.ndpointer(dtype=np.float64),   # max_passed_days
            np.ctypeslib.ndpointer(dtype=np.float64),   # days_to_lookback
            np.ctypeslib.ndpointer(dtype=np.float64),   # days_to_predict
            np.ctypeslib.ndpointer(dtype=np.float64),   # result
            ] 
        self.calc_fp.restype = c_void_p         
        #==================================================================================
        
        
    #計算領域の範囲を指定    
    def set_bound_and_grid( self , x_min , x_max , y_min , y_max , buff_meter , delta_mesh ):
        self.x_bound = [ x_min - buff_meter , x_max + buff_meter ]  
        self.y_bound = [ y_min - buff_meter , y_max + buff_meter ]
        
        x_position = np.arange( self.x_bound[0] , self.x_bound[1] , delta_mesh )
        y_position = np.arange( self.y_bound[0] , self.y_bound[1] , delta_mesh )
        
        self.grid_x , self.grid_y = np.meshgrid(x_position , y_position )          


    #各データの観測日からの経過時間を計測
    def deltatimes( self ):
        datetime_data = pd.to_datetime( self.data.iloc[:,0] ) #取得データの日付をdatetime型に変換
        dt = datetime.now() - datetime_data.dt.to_pydatetime()
        
        day = []
        for i in dt:
            day.append( ( i.days * 86400  + i.seconds )  / 86400 )
        return day
        
        
    #生息分布を計算
    def calc_existence_fp(self , passed_days , predict_days , timesteps  , check_view ): 
        
        #配列サイズの設定
        i_no , j_no = self.grid_x.shape 
        self.set_meshdata( np.array( j_no , dtype = 'int32' ) , 
                           np.array( i_no , dtype = 'int32' ) , 
                           np.array( timesteps , dtype= 'int32' ) , 
                           np.array( self.grid_x , dtype= 'float64' ) , 
                           np.array( self.grid_y , dtype= 'float64' ) 
                           )
        
        #観測データの設定
        passedtimes = self.deltatimes()  #計算用経過時間(単位：日)
        data_send = np.vstack( (self.data.geometry.x , self.data.geometry.y) ) #観測地点のxy座標
        data_send = np.vstack( ( data_send , passedtimes ) )
        
        self.set_obsdata(  np.array( self.data.shape[0] , dtype= 'int32'   ) , 
                           np.array( data_send          , dtype= 'float64' ) )
        
        #計算パラメータの設定
        self.set_parameter( np.array( self.sigma   , dtype= 'float64'  ) , 
                            np.array( self.C_coff  , dtype= 'float64'   ) , 
                            np.array( self.D_coff  , dtype= 'float64'   ) , 
                            np.array( self.threads , dtype= 'int32'     )   
                            )  
        
        z = np.array( np.empty( ( int(timesteps) , int( i_no ) , int( j_no ) ) ), dtype='float64' ) 
        self.calc_fp( np.array( np.max( passedtimes ) , dtype='float64' )  , 
                      np.array( passed_days , dtype='float64' ) , 
                      np.array( predict_days , dtype='float64' ) , 
                      z )
                                       
        return z #結果を返す
                    