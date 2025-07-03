import os 
import numpy as np 
import pandas as pd 

import shapely
import geopandas as gpd



class create_geojson():

    def __init__(self , grid_x , grid_y , z , crs ):
        #出力するメッシュデータ
        self.grid_x = grid_x # np.meshgrid
        self.grid_y = grid_y # np.meshgrid
        self.z = z           # mesh data
        self.crs = crs       # geometry coordinate 


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
    def set_surface4map( self ):
        mesh_x_tmp = self.grid_x[0]
        mesh_y_tmp = self.grid_y[:,0]
        self.mesh_coordinates( mesh_x_tmp , mesh_y_tmp )

        #self.mesh_coordinates( self.grid_x , self.grid_y ) #meshgridを入れるとjsonに不具合

        x_tmp = self.grid_x.flatten()
        y_tmp = self.grid_y.flatten()
        z_tmp = self.z.flatten()
        
        dat = np.transpose( np.vstack( ( np.vstack( (x_tmp , y_tmp) ) , z_tmp ) ) ) 
        #dat = dat[ ~np.isnan( dat ).any( axis=1 ) ] #nan削除
        
        # gis ポリゴンデータへの変換
        gdf = gpd.GeoDataFrame( dat , 
                                geometry=gpd.points_from_xy( dat[:,0] , dat[:,1] ) , 
                                crs=self.crs, 
                                )
        gdf.columns = [ 'x' , 'y' , 'z' , 'geometry' ]  
        
        cell = self.create_cells()
        merged = gpd.sjoin(  gdf ,cell , how='left' )
        dissolve = merged.dissolve(by="index_right", aggfunc="max")
        cell.loc[dissolve.index, 'z'] = dissolve.z.values
        self.cell = cell.dropna( how ='any' )                   


    #座標変換をする      
    def transfer_crs( self , srid_proj ):
        self.cell_transfered = self.cell.to_crs( epsg = srid_proj )        
        
    # geojsonで出力する
    def output_geojson( self , geo_df , sub_dir, filename ):
        
        # 出力フォルダの作成
        output_dir = os.path.join( 
            "../" , 
            "output" , 
            "sub_dir"                                  
        )
        os.makedirs( output_dir , exist_ok=True  )
        
        f = os.path.join( 
            output_dir , 
            filename + '.geojson'                 
        )
        geo_df.to_file( f , driver="GeoJSON", encoding='utf-8')                    