import os
import sys 
import rasterio
from rio_tiler.io import COGReader
from rio_tiler.models import ImageData
from rio_tiler.utils import create_cutline
from PIL import Image
import numpy as np
import pandas as pd 
from matplotlib import cm
import yaml


class create_tiledmap:

    def __init__(self , h_threshold ):
        f = 'xycode_by_zoomlevel.csv'
        self.df_zoom_xy = pd.read_csv( f , encoding= 'utf-8' ) #ズームレベルとXYコードの対応表を読み込む
        self.h_threshold = h_threshold


    # 2024/5/8 rev : np.whereの中でrbgを書き換えてしまうと浸水想定区域図作成マニュアルの配色にならない
    def create_colormap_based_on_floodmap(self, image_data , tile_size ):
        dat = np.array( image_data ).reshape( (tile_size , tile_size)   ).copy()
        r_dat00 = dat.copy()
        g_dat00 = dat.copy()
        b_dat00 = dat.copy()
        a_dat00 = dat.copy()

        #floodmap => 浸水想定区域図作成マニュアル　第四版 P.34
        r_dat01 = np.where( r_dat00 == 0  , 0 , r_dat00  ).copy()
        r_dat02 = np.where( (20.0 <= r_dat01 ) & ( r_dat01 <200.0 )  , 220 , r_dat01  ).copy() #20.0m以上
        r_dat03 = np.where( ( 0   <  r_dat02 ) & ( r_dat02 <  0.3 )  , 255 , r_dat02  ).copy() #0.3m未満
        r_dat04 = np.where( ( 0.3 <= r_dat03 ) & ( r_dat03 <  0.5 )  , 247 , r_dat03  ).copy() #0.5m未満
        r_dat05 = np.where( ( 0.5 <= r_dat04 ) & ( r_dat04 <  1.0 )  , 248 , r_dat04  ).copy() #1.0m未満
        r_dat06 = np.where( ( 1.0 <= r_dat05 ) & ( r_dat05 <  3.0 )  , 255 , r_dat05  ).copy() #3.0m未満
        r_dat07 = np.where( ( 3.0 <= r_dat06 ) & ( r_dat06 <  5.0 )  , 255 , r_dat06  ).copy() #5.0m未満
        r_dat08 = np.where( ( 5.0 <= r_dat07 ) & ( r_dat07 < 10.0 )  , 255 , r_dat07  ).copy() #10.0m未満
        r_dat09 = np.where( (10.0 <= r_dat08 ) & ( r_dat08 < 20.0 )  , 242 , r_dat08  ).copy() #20.0m未満

        g_dat01 = np.where( g_dat00 == 0  , 0 , g_dat00  )
        g_dat02 = np.where( (20.0 <= g_dat01 ) & ( g_dat01 <200.0 )  , 122 , g_dat01  ).copy() #20.0m以上    
        g_dat03 = np.where( ( 0   <  g_dat02 ) & ( g_dat02 <  0.3 )  , 255 , g_dat02  ).copy() #0.3m未満
        g_dat04 = np.where( ( 0.3 <= g_dat03 ) & ( g_dat03 <  0.5 )  , 245 , g_dat03  ).copy() #0.5m未満
        g_dat05 = np.where( ( 0.5 <= g_dat04 ) & ( g_dat04 <  1.0 )  , 225 , g_dat04  ).copy() #1.0m未満
        g_dat06 = np.where( ( 1.0 <= g_dat05 ) & ( g_dat05 <  3.0 )  , 216 , g_dat05  ).copy() #3.0m未満
        g_dat07 = np.where( ( 3.0 <= g_dat06 ) & ( g_dat06 <  5.0 )  , 183 , g_dat06  ).copy() #5.0m未満
        g_dat08 = np.where( ( 5.0 <= g_dat07 ) & ( g_dat07 < 10.0 )  , 145 , g_dat07  ).copy() #10.0m未満
        g_dat09 = np.where( (10.0 <= g_dat08 ) & ( g_dat08 < 20.0 )  , 133 , g_dat08  ).copy() #20.0m未満
    
        b_dat01 = np.where( b_dat00 == 0  , 0 , b_dat00  )
        b_dat02 = np.where( (20.0 <= b_dat01 ) & ( b_dat01 <200.0 )  , 220 , b_dat01  ).copy() #20.0m以上    
        b_dat03 = np.where( ( 0   <  b_dat02 ) & ( b_dat02 <  0.3 )  , 179 , b_dat02  ).copy() #0.3m未満
        b_dat04 = np.where( ( 0.3 <= b_dat03 ) & ( b_dat03 <  0.5 )  , 169 , b_dat03  ).copy() #0.5m未満
        b_dat05 = np.where( ( 0.5 <= b_dat04 ) & ( b_dat04 <  1.0 )  , 166 , b_dat04  ).copy() #1.0m未満
        b_dat06 = np.where( ( 1.0 <= b_dat05 ) & ( b_dat05 <  3.0 )  , 192 , b_dat05  ).copy() #3.0m未満
        b_dat07 = np.where( ( 3.0 <= b_dat06 ) & ( b_dat06 <  5.0 )  , 183 , b_dat06  ).copy() #5.0m未満
        b_dat08 = np.where( ( 5.0 <= b_dat07 ) & ( b_dat07 < 10.0 )  , 145 , b_dat07  ).copy() #10.0m未満
        b_dat09 = np.where( (10.0 <= b_dat08 ) & ( b_dat08 < 20.0 )  , 201 , b_dat08  ).copy() #20.0m未満

        a_dat01 = np.where( ( self.h_threshold < a_dat00 ) & ( a_dat00 < 200 )  , 255 , a_dat00 ).copy()
        a_dat02 = np.where( a_dat01 <= self.h_threshold , 0 , a_dat01 ).copy()

        colored_image = np.zeros( ( tile_size , tile_size , 4 )  ).astype(np.uint8)
        colored_image[ :, :, 0] = r_dat09.astype( np.uint8 ) # R
        colored_image[ :, :, 1] = g_dat09.astype( np.uint8 ) # G
        colored_image[ :, :, 2] = b_dat09.astype( np.uint8 ) # B
        colored_image[ :, :, 3] = a_dat02.astype( np.uint8 ) # a

        return colored_image


    def return_xycode_by_zoomlevels( self, zoom_level_in ):
        # Setting the appropriate map code to exhibit => xycode_by_zoomlevel.csvで必要箇所のコードを設定

        if 8 <= zoom_level_in or zoom_level_in <= 17:
            xy_tmp = self.df_zoom_xy[ self.df_zoom_xy['zoom_level'] == zoom_level_in ]
            zx = [ n for n in range( int(xy_tmp['zx_L']) , int(xy_tmp['zx_R']) + 1 ) ] 
            zy = [ n for n in range( int(xy_tmp['zy_U']) , int(xy_tmp['zy_D']) + 1 ) ] 

        else: 
            print( "zoom_level isn't set between 8 and 17")

        return zx , zy 


    def create_tiled_map_with_zoom_level_and_colormap(self, input_file, output_dir ,dirname_time , zoom_level  , tile_size=256 ): #  , colormap='viridis'):
        # Create a COG (Cloud-Optimized GeoTIFF) reader        
        cog_reader = COGReader(input_file)

        # Get metadata (bounds, crs, etc.) from the GeoTIFF
        # metadata = cog_reader.dataset.descriptions[1]
        with rasterio.open(input_file) as src:
            metadata = src.meta
            transform = src.transform 

        # Calculate the number of tiles for the specified zoom level
        num_tiles = 2 ** zoom_level

        # Calculate the tile width and height
        tile_width = metadata["width"] // num_tiles
        tile_height = metadata["height"] // num_tiles

        # Create output directory if it does not exist
        #output_dir = f"{os.path.splitext(input_file)[0]}_tiles"
        
        dir_tmp = output_dir + os.sep + dirname_time
        #os.makedirs(output_dir, exist_ok=True)
        os.makedirs( dir_tmp , exist_ok = True )                            # create directory for appropriate file_number
        os.makedirs( dir_tmp + os.sep + str(zoom_level) , exist_ok = True ) # create directory for appropriate zoomlevel

        # Setting the appropriate map code to exhibit => 鬼怒川に合わせて設定
        zx , zy = self.return_xycode_by_zoomlevels( zoom_level )


        # Loop through each tile and save it as an image file
        for i in zx:
            
            # create directory for appropriate x-id
            os.makedirs( dir_tmp + os.sep + str(zoom_level) + os.sep + str(i) , 
                        exist_ok = True ) 
            output_dir = os.getcwd() + os.sep + dir_tmp + os.sep + str(zoom_level) + os.sep + str(i) + os.sep

            for j in zy:         
                # Calculate tile bounds
                tile_bounds = (
                    transform[2] + j * tile_width,
                    transform[5] + i * tile_height,
                    transform[2] + (j + 1) * tile_width,
                    transform[5] + (i + 1) * tile_height
                )

                # Read the image data for the tile
                try:
                    tile_image, _ = cog_reader.tile(
                        #tile_bounds,
                        i , j , zoom_level,
                        tilesize=tile_size,
                        resampling_method="nearest"
                    )

                    # Apply colormap
                    # colored_tile_image = apply_colormap(tile_image, colormap)

                    # Create colormap based on hazardmap 
                    colored_tile_image = self.create_colormap_based_on_floodmap( tile_image , tile_size  ) 

                    # Convert image data to PIL Image
                    pil_image = Image.fromarray( colored_tile_image , mode='RGBA' ) 

                    # Save the tile as an image file
                    tile_filename = os.path.join(output_dir, f"{j}.png")
                    pil_image.save(tile_filename)

                except: 
                    # 計算対象範囲とタイル画像生成領域は完全に一致しないため、生成されない場合は以下のエラーメッセージが生じる
                    print(zoom_level ,":" , i , ":" , j ," file couldn't be created" )
                                        
                    

if __name__ == '__main__':
    #Not Use these code in below 
    #args = sys.argv              # arguments is used for setting arbit-zoomlevel
    #f_no = str( args[1] )        # Specify the resultfile id 
    #zoom_level = int( args[2] )  # Specify the desired zoom level
    #colormap = 'viridis'         # Specify the desired colormap

    # Set Current Directory
    os.chdir( os.path.dirname(os.path.abspath('__file__') ) )
    print("now_dir :", os.getcwd())

    # Read_Settings 
    f_timetable = '../result_geotiff/floodpred_timetable_tif.csv' #time_table(24/9/17:モデル修正に伴うファイル名変更)
    df_tt = pd.read_csv( f_timetable )
    
    f_stdate = '../result_geotiff/modellinkage_stime.csv' #start time(24/9/17:モデル修正に伴うファイル名変更)
    df_stdate_tmp = pd.read_csv( f_stdate , header=None )
    stdate = pd.to_datetime( df_stdate_tmp.iloc[0] )
    #stdate = datetime( 2015 , 9 , 10 , 13 , 0 ) # starttime    
    s_format = '%Y%m%d%H%M'

    # Set the zoom_levels to output
    zoom_levels = np.arange( 8 , 18 )

    # Get The Start Time of This Process
    output_date = datetime.now()    
    output_directory = "../output_tilemaps/" + datetime.strftime( output_date , s_format )  #time_tablesに沿って設定

    # 予測結果のフォルダ階層
    # output_tilemaps/予測（タイル画像作成）開始時刻/予測対象時刻/zoomレベル/ｘコード/yコード.png

    # --multiprocess化 start--
    args = []
    for t, i in enumerate(df_tt["id"]):
        # --multiprocess化 start--
        input_file = "../result_geotiff/floodpred_tif_" + str( int(i)) + ".tif" #time_table(24/9/17:モデル修正に伴うファイル名変更)
        time = datetime.strftime( stdate.iloc[0] + timedelta(seconds=1) * df_tt["pred"][t], s_format)  # time_tablesに沿って設定
        args.append((input_file, output_directory, time, zoom_levels))

    # 並列処理する部分を新規メソッドに切り出し、並列数の上限を指定し新規メソッドを並列実行
    # 並列数上限を comfig から設定
    with open("config_geotiff2tiledmap.yml", "r", encoding="UTF-8") as yml:
        config = yaml.safe_load(yml)


    h_threshold = 0.10
    CTM = create_tiledmap( h_threshold )

    for t, i in enumerate(df_tt["id"]):
        #time = datetime.strftime( stdate + timedelta( minutes= 10 ) * t , s_format )
        #time = datetime.strftime( stdate + timedelta( minutes= 10 ) * t * 6  , s_format )  #時間ピッチに修正
        time = datetime.strftime( stdate.iloc[0] + timedelta( seconds= 1 ) * df_tt["pred"][t]  , s_format )  #time_tablesに沿って設定

        #input_file = "../result_geotiff_for0606/result_geotiff_1300/result_" + str( int(i) )  + ".tif"
        input_file = "../result_geotiff/result_" + str( int(i) )  + ".tif"

        for z in zoom_levels:            
            CTM.create_tiled_map_with_zoom_level_and_colormap(input_file , output_directory ,str(time) , z ) # , colormap)