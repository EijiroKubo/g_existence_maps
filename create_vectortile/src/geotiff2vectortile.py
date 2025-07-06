#create vector-tile-datas from geotiff-files
import os
import numpy as np
import pandas as pd 
import geopandas as gpd
import shapely
import rasterio
from pyproj import Transformer
from datetime import datetime , timedelta 

# Tippecanoeの使用用：24/12/04
import subprocess
import json
import io

# --multiprocess化 start--
import multiprocessing
import yaml
# --multiprocess化 end--


class create_vectortile:
    
    def __init__(self, h_threshold , crs_to_out ):
        self.h_threshold = h_threshold           
        self.crs = crs_to_out 
            
    def mesh_transformed_coordinates(self , crs_org , crs_conv , mesh_x , mesh_y ):
        tr = Transformer.from_crs( crs_org, crs_conv )
        mesh_y_tr, mesh_x_tr = tr.transform( mesh_y , mesh_x)        
        
        return mesh_x_tr , mesh_y_tr     
        
    # セルを構成
    def create_cells(self):
        # create the cells in a loop
        grid_cells = []

        for x0 in np.arange(self.x_min, self.x_max, self.cellsize_x):
            for y0 in np.arange(self.y_min, self.y_max, self.cellsize_y):            
                # bounds
                x1 = x0 + self.cellsize_x
                y1 = y0 + self.cellsize_y
                grid_cells.append(shapely.geometry.box(x0, y0, x1, y1))

        cell = gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs=self.crs)
        return cell
    
    # geopandasのデータフレームに対して、フィーチャーごとに一意のIDを付与
    # ベクトルタイル生成時にIDを付与しなければNull値が混入してしまう
    def add_mvt_id(self , geo_df):        
        geo_df["mvt_id"] = range(1, len(geo_df) + 1)
        return geo_df    
    
    # geojsonを出力するためのメッシュ（セル）ポリゴンデータを整理
    def create_flood_cell(self, h_dat ):
        x_tmp = self.mesh_x_tr.flatten()
        y_tmp = self.mesh_y_tr.flatten()
        
        h_tmp = h_dat.flatten()
        
        # dat => [x, y, h_depth]を形成  
        dat = np.transpose(np.vstack((np.vstack((x_tmp, y_tmp)), h_tmp)))
        dat = dat[~np.isnan(dat).any(axis=1)] #nan削除
        dat = np.delete(dat, np.where(dat[:,2] < self.h_threshold)[0], axis=0) #小さい値は削除        

        # gis ポリゴンデータへの変換
        gdf = gpd.GeoDataFrame( 
            dat, 
            geometry=gpd.points_from_xy(dat[:,0], dat[:,1]), 
            crs=self.crs 
        )
        gdf.columns = ['x', 'y', 'h_depth', 'geometry'] 
        
        cell = self.create_cells()
        
        if not cell.empty:
            merged = gpd.sjoin(gdf, cell, how='left')
            dissolve = merged.dissolve(by="index_right", aggfunc="max")
            cell.loc[dissolve.index, 'h_depth'] = dissolve.h_depth.values
            cell = cell.dropna(how='any')
            
        else : 
            print( "There is no inundation mesh" )        

        return cell 
        
    # geojsonで出力する
    def output_geojson(self, geo_df, f ):        
    
        if not geo_df.empty:
            geo_df.to_file(f, driver="GeoJSON", encoding='utf-8')        
        else :
            print( "There is no inundation mesh" )

    # tippecanoeを使用して、ベクトルタイルを作成
    def create_vectortile_with_tippecanoe(self , output_dir, geojson_str):
        # Tippecanoeコマンドとオプションをリストとして定義
        command = [
            'tippecanoe',
            '--output-to-directory=' + str(output_dir) ,
            '--force', 
            #'-rg', #読み込めなくなってしまうので、一旦消しておく
            '--minimum-zoom=8',
            '--maximum-zoom=17' , 
            '--include=mvt_id' ,
            '--include=h_depth' ,
        ]        
        # Tippecanoeコマンドを使用
        # 出力ディレクトリを指定
        # データがあったら上書き
        # レート指定（ズーム等によって間引かれる割合、これだと最大、、のはず
        # ズームレベルの指定(8～17)
        # mvt_id 属性を保持           

        # subprocess.runで渡すstdinの値がio.BytesIOだと,fileno()というメソッドでサポートされていないためエラーが生じるとのこと
        # chatGPTより、以下の処理を追加するとのこと.
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,   # 標準入力をパイプに接続
            stdout=subprocess.PIPE,  # 標準出力をキャプチャ
            stderr=subprocess.PIPE,  # 標準エラー出力をキャプチャ
            text=True                # テキストモードを有効化
        )        

        # geojsonデータを渡してtippecanoe実行
        stdout, stderr = process.communicate(input=geojson_str)  

        print("標準出力:")
        print(stdout)
        print("\n標準エラー出力:")
        print(stderr)

    def create_vectortile_with_geotiff(self, input_file , output_dir , pred_time  ):        
        # Get metadata (bounds, crs, etc.) from the GeoTIFF
        # metadata = cog_reader.dataset.descriptions[1]
        with rasterio.open(input_file) as src:
            metadata = src.meta               # Get metadata
            transform = src.transform         # Get Affine matrics        
            crs_org = src.crs                 # Get CRS 
            h_data = np.array( src.read(1) )  # Get Depth data from geotiff file

        # create directory for appropriate file_number
        os.makedirs( output_dir , exist_ok = True )          

        # Set mesh information
        self.x_cells = metadata["width"] 
        self.y_cells = metadata["height"]                 
        
        x_tmp = np.arange( metadata["width"] ) * transform[0]  + transform[2]
        y_tmp = np.arange( metadata["height"] ) * transform[4] + transform[5]
        x_mesh , y_mesh = np.meshgrid( x_tmp , y_tmp  ) # mesh
        
        self.mesh_x_tr , self.mesh_y_tr = self.mesh_transformed_coordinates(crs_org , self.crs , x_mesh , y_mesh  ) #WGS84に変換（本多さん依頼事項）

        self.x_min = np.min(self.mesh_x_tr)        
        self.y_min = np.min(self.mesh_y_tr)
        self.x_max = np.max(self.mesh_x_tr)
        self.y_max = np.max(self.mesh_y_tr)    

        self.cellsize_x = ( self.x_max - self.x_min ) / (self.x_cells - 1)
        self.cellsize_y = ( self.y_max - self.y_min ) / (self.y_cells - 1) 
        
        # Create Cells Data for geojson 
        gdf_cell = self.create_flood_cell( h_data )

        # フィーチャーにmvt_idを追加
        gdf_cell = self.add_mvt_id( gdf_cell )

        # GeoJSON形式の文字列に変換
        geojson_str = gdf_cell.to_json()

        # create directory for appropriate file_number
        output_dir_by_each_time = output_dir + os.sep + pred_time 
        os.makedirs( 
            output_dir_by_each_time ,
            exist_ok = True
        )      

        # ベクトルタイルの出力
        if not gdf_cell.empty:
            
            self.create_vectortile_with_tippecanoe( 
                output_dir_by_each_time ,
                geojson_str 
            )

if __name__ == '__main__':

    # Set Current Directory ====================================
    os.chdir( os.path.dirname(os.path.abspath('__file__') ) )
    print("now_dir :", os.getcwd())


    # config file ============================================== 
    with open("config_geotiff2vectortile.yml", "r", encoding="UTF-8") as yml:
        config = yaml.safe_load(yml)


    # 暫定版としてresult_geotiffを1ファイル読みこんで出力
    
    # Get The Start Time of This Process ======================
    
    s_format = '%Y%m%d%H%M'        
    output_date = datetime.now()    #検証時は要修正
    output_directory = "../output_vectortile/" + datetime.strftime( output_date , s_format )  #time_tablesに沿って設定          

    # Other Settings ==========================================
    h_threshold = 0.10                # minimum depth for create geojson  
    crs_to_out= config["epsg_out"]    # projection for the output grid files➡WGS84

    CVT = create_vectortile( h_threshold , crs_to_out )    
    
    input_file = os.path.join( "../" , "input_geotiff" , "result_ex.geotiff" ) 
    CVT.create_vectortile_with_geotiff(input_file , output_directory , str(0) ) 
    
    '''
    # Read_Settings ============================================
    # Read time_tables
    f_timetable = '../result_geotiff/floodpred_timetable_tif.csv' #計算プログラムの名称変更に対応：24/9/17
    df_tt = pd.read_csv( f_timetable )    
    
    # Read start time
    f_stdate = '../result_geotiff/modellinkage_stime.csv' #計算プログラムの名称変更に対応：24/9/17
    df_stdate_tmp = pd.read_csv( f_stdate , header=None )
    stdate = pd.to_datetime( df_stdate_tmp.iloc[0] )
    
    s_format = '%Y%m%d%H%M'    
    
    # Get The Start Time of This Process ======================
    output_date = datetime.now()    #検証時は要修正
    output_directory = "../output_vectortile/" + datetime.strftime( output_date , s_format )  #time_tablesに沿って設定        
        
    # Other Settings ==========================================
    h_threshold = 0.10                # minimum depth for create geojson  
    crs_to_out= config["epsg_out"]    # projection for the output grid files➡WGS84
        
    CVT = create_vectortile( h_threshold , crs_to_out )    

    for t, i in enumerate(df_tt["id"]):    
                
        pred_time = datetime.strftime( stdate.iloc[0] + timedelta( seconds= 1 ) * df_tt["pred"][t]  , s_format )          
        input_file = "../result_geotiff/floodpred_tif_" + str( int(i) )  + ".tif" #計算プログラムの名称変更に対応：24/9/17              
        CVT.create_vectortile_with_geotiff(input_file , output_directory ,str(pred_time) ) 
    '''
