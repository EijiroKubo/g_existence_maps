import numpy as np 
import pandas as pd 

from shapely.geometry import Point
import geopandas as gpd 
from pyproj import Transformer



class data():
    def __init__(self , file_abs_path , srid  ):
        self.file_abs_path = file_abs_path 
        self.srid_org = srid
 
    
    #１：元データを読み込む
    def read_csv_data(self):
        df = pd.read_csv( self.file_abs_path , header = None )
        
        Geometry = [ Point(xy) for xy in zip(df.iloc[:,1], df.iloc[:,0]) ]
        self.gdf_org = gpd.GeoDataFrame( df.iloc[:,2] , crs=self.srid_org , geometry=Geometry  )


    #２： 座標変換
    def transfar_data(self, srid_proj ):
        self.gdf_transfered = self.gdf_org.to_crs( epsg=srid_proj )  # 変換式を作成
        
       
    #３：１と２をまとめた処理
    def read_and_transfer_data(self , srid_proj ):
        self.read_csv_data()
        self.transfar_data( srid_proj )
        
        
        


        