import os

import numpy as np

# GEOTIFF変換用ライブラリ
import rasterio
from rasterio.transform import from_origin



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

        self.x_min = np.min(self.mesh_x)
        self.x_max = np.max(self.mesh_x)
        self.y_min = np.min(self.mesh_y)
        self.y_max = np.max(self.mesh_y)

        self.x_cells = np.shape(self.mesh_x)[0]
        self.y_cells = np.shape(self.mesh_x)[1]

        self.cellsize_x = (self.x_max - self.x_min) / (self.x_cells - 1)
        self.cellsize_y = (self.y_max - self.y_min) / (self.y_cells - 1)

        # 地理情報（空間解像度や座標系）を設定
        self.transform = from_origin(
            self.x_min, self.y_max, self.cellsize_x, self.cellsize_y
        )
        
        
    # 指定のステップに対してgeotiffデータを出力する
    def output_geotiff(self, h_time_series, time_steps):
        t_max = np.shape( h_time_series )[0]
        
        for id, t in enumerate(time_steps):  #
            if t > t_max : #追記 24/9/8
                print("couldn't output file. maxstep=" , t_max , "/outputstep=" , t )
                
            else :             
                self.output_file(h_time_series[t], id)

    # geotiffを出力する
    def output_geotiff(self, data , sub_dir, filename ):
        
        # 出力フォルダの作成
        output_dir = os.path.join( 
            "../" , 
            "output" , 
            "sub_dir"                                  
        )
        os.makedirs( output_dir , exist_ok=True  )
                        
        f = os.path.join( 
            output_dir , 
            filename + '.geotiff'                 
        )

        with rasterio.open(
            f,
            "w",
            driver="GTiff",
            height=np.shape(data)[1],
            width=np.shape(data)[0],
            count=1,  # バンド数（ここでは1つのバンドを使用）
            dtype=data.dtype,
            crs=self.crs,
            transform=self.transform,
        ) as dst:
            dst.write(np.transpose(data), 1)  # 第1バンドにndarrayデータを書き込み

        