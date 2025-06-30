import os 
import numpy as np 

import shapely
import geopandas as gpd

import matplotlib.pyplot as plt 
import pykrige.kriging_tools as kt
from pykrige.ok import OrdinaryKriging



class surface_interpolate():
    def __init__( self , data , crs ):
        '''
        データ（レコード）数:data_num
        データ:data        (geopandas dataframe)
        データのcrs
        '''
        self.data_num = np.shape( data )[0]
        self.data = data 
        self.crs = crs 
        

    #サンプル表示用のxy範囲の設定        
    def set_sample_area(self , buff_meter ):
        #サンプル表示範囲 = 収集データの包絡範囲＋buff_meter(余白分)
        
        x_max = np.max( self.data.geometry.x )
        x_min = np.min( self.data.geometry.x )

        y_max = np.max( self.data.geometry.y )
        y_min = np.min( self.data.geometry.y )        
        
        x_bound = [ x_min - buff_meter , x_max + buff_meter ]  
        y_bound = [ y_min - buff_meter , y_max + buff_meter ]
        
        return x_bound , y_bound 
        
                
    #クリギングモデルを作成
    def make_kriging_model(self ):
        x_min = np.min( self.data.geometry.x ) 
        y_min = np.min( self.data.geometry.y ) 
        
        #注意：すべて同じ値だとエラーが出るため、テスト表示用にランダムを加えている
        self.d_z = np.ones( self.data_num ) + 0.01 * np.random.rand( 12 )

        
        #応答局面を生成：
        try:
            self.k = OrdinaryKriging(
                self.data.geometry.x  , #data = geopandas.DataFrame
                self.data.geometry.y  , #data = geopandas.DataFrame 
                self.d_z ,
                variogram_model="linear" ,
                verbose=False ,
                enable_plotting=False ,
                )
                   
        except :
            print( 'couldnt create kriging model' )
    
            
    #クリギングモデルを用いて表面を生成            
    def create_surface( self , buff_meter , delta_mesh , check_view ):
        x_bound, y_bound = self.set_sample_area( buff_meter ) #出力範囲を設定
        
        self.x_position = np.arange(x_bound[0] , x_bound[1] , delta_mesh )
        self.y_position = np.arange(y_bound[0] , y_bound[1] , delta_mesh )
        
        self.z, self.ss = self.k.execute("grid", self.x_position , self.y_position )        
            
        
        #応答曲面を可視化する関数
        def check_response_surface( gridX , gridY , z_interpolate , point_x , point_y , point_z ):
            fig, ax = plt.subplots()

            im = ax.contourf(  gridX , gridY ,  z_interpolate )
            fig.colorbar(im)
            ax.scatter( point_x , point_y , s=30 ,  c = 'w' ,linewidths=1 , ec = 'k' ) #c = point_z 
            plt.show()        
        
        #グリッドに対する応答曲面のチェック
        if check_view == True :             
            check_response_surface( self.x_position , 
                                    self.y_position , 
                                    self.z ,
                                    self.data.geometry.x , 
                                    self.data.geometry.y , 
                                    self.d_z )            
                
    
    #メッシュの座標を記録
    def mesh_coordinates(self ,mesh_x , mesh_y ):
        self.mesh_x = mesh_x
        self.mesh_y = mesh_y

        self.x_min = np.min( self.mesh_x )
        self.x_max = np.max( self.mesh_x )
        self.y_min = np.min( self.mesh_y )
        self.y_max = np.max( self.mesh_y ) 

        self.x_cells = np.shape( self.mesh_x )[0]
        self.y_cells = np.shape( self.mesh_y )[0]

        self.cellsize_x = ( self.x_max - self.x_min ) / ( self.x_cells - 1 )
        self.cellsize_y = ( self.y_max - self.y_min ) / ( self.y_cells - 1 )         


    #セルを構成
    def create_cells(self):

        # create the cells in a loop
        grid_cells = []
        for x0 in np.arange(self.x_min, self.x_max+self.cellsize_x, self.cellsize_x ):
            for y0 in np.arange( self.y_min, self.y_max + self.cellsize_y, self.cellsize_y ):
                # bounds
                x1 = x0-self.cellsize_x
                y1 = y0+self.cellsize_y
                grid_cells.append( shapely.geometry.box(x0, y0, x1, y1)  )

        cell = gpd.GeoDataFrame(grid_cells, columns=['geometry'], 
                                        crs=self.crs)
        return cell        
        
        
    #地図に投影用のデータを作成する    
    def set_surface4map(self ):
        self.mesh_coordinates( self.x_position , self.y_position) 

        mesh_x , mesh_y = np.meshgrid( self.x_position , 
                                       self.y_position )
        x_tmp = mesh_x.flatten()
        y_tmp = mesh_y.flatten()
        z_tmp = self.z.flatten()
        
        dat = np.transpose( np.vstack( ( np.vstack( (x_tmp , y_tmp) ) , z_tmp ) ) ) 
        dat = dat[ ~np.isnan( dat ).any( axis=1 ) ] #nan削除
        
        # gis ポリゴンデータへの変換
        gdf = gpd.GeoDataFrame( dat , 
                                geometry=gpd.points_from_xy( dat[:,0] , dat[:,1] ) , 
                                crs=self.crs,  #要修正
                                )
        gdf.columns = [ 'x' , 'y' , 'z' , 'geometry']  
        
        cell = self.create_cells()
        merged = gpd.sjoin(  gdf ,cell , how='left' )
        dissolve = merged.dissolve(by="index_right", aggfunc="max")
        cell.loc[dissolve.index, 'z'] = dissolve.z.values

        self.cell = cell.dropna( how ='any' )                   


    #座標変換をする      
    def transfer_crs( self , srid_proj ):
        self.cell_transfered = self.cell.to_crs( epsg = srid_proj )        
        
    
    # geojsonで出力する
    def output_geojson(self , geo_df ):
        f = os.getcwd() + os.sep + '' + os.sep + 'result.geojson'
        geo_df.to_file( f , driver="GeoJSON", encoding='utf-8')        