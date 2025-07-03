import os
import sys
import rasterio
from rio_tiler.io import COGReader
from PIL import Image
import numpy as np
import pandas as pd
import yaml
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib import cm


class create_tiledmap:

    def __init__(self, h_threshold, colormap_name='viridis'):
        f = 'xycode_by_zoomlevel.csv'
        self.df_zoom_xy = pd.read_csv(f, encoding='utf-8')
        self.h_threshold = h_threshold
        self.colormap_name = colormap_name

    def apply_colormap_from_matplotlib(self, image_data, tile_size):
        dat = np.array(image_data).reshape((tile_size, tile_size)).astype(np.float32)

        # alpha マスク：しきい値以下は透明
        alpha_mask = (dat > self.h_threshold).astype(np.uint8)

        # NaN や Inf の処理
        dat = np.nan_to_num(dat, nan=0.0, posinf=0.0, neginf=0.0)

        vmax = np.max(dat) if np.max(dat) > 0 else 1.0
        normalized = np.clip(dat / vmax, 0, 1)

        cmap = cm.get_cmap(self.colormap_name)
        rgba_img = (cmap(normalized) * 255).astype(np.uint8)
        rgba_img[..., 3] = 255 * alpha_mask

        return rgba_img

    def return_xycode_by_zoomlevels(self, zoom_level_in):
        if 8 <= zoom_level_in <= 17:
            xy_tmp = self.df_zoom_xy[self.df_zoom_xy['zoom_level'] == zoom_level_in]
            zx = [n for n in range(int(xy_tmp['zx_L']), int(xy_tmp['zx_R']) + 1)]
            zy = [n for n in range(int(xy_tmp['zy_U']), int(xy_tmp['zy_D']) + 1)]
        else:
            print("zoom_level isn't set between 8 and 17")
            zx, zy = [], []
        return zx, zy

    def create_tiled_map_with_zoom_level_and_colormap(self, input_file, output_dir, dirname_time, zoom_level, tile_size=256):
        cog_reader = COGReader(input_file)

        with rasterio.open(input_file) as src:
            metadata = src.meta
            transform = src.transform

        num_tiles = 2 ** zoom_level
        tile_width = metadata["width"] // num_tiles
        tile_height = metadata["height"] // num_tiles

        dir_tmp = os.path.join(output_dir, dirname_time)
        os.makedirs(os.path.join(dir_tmp, str(zoom_level)), exist_ok=True)

        zx, zy = self.return_xycode_by_zoomlevels(zoom_level)

        for i in zx:
            x_dir = os.path.join(dir_tmp, str(zoom_level), str(i))
            os.makedirs(x_dir, exist_ok=True)

            for j in zy:
                try:
                    tile_image, _ = cog_reader.tile(i, j, zoom_level, tilesize=tile_size, resampling_method="nearest")
                    tile_array = tile_image.data[0]  # バンド0 を使用
                    colored_tile_image = self.apply_colormap_from_matplotlib(tile_array, tile_size)
                    pil_image = Image.fromarray(colored_tile_image, mode='RGBA')
                    tile_filename = os.path.join(x_dir, f"{j}.png")
                    pil_image.save(tile_filename)

                except Exception as e:
                    print(f"{zoom_level}:{i}:{j} file couldn't be created - {str(e)}")


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath('__file__')))
    print("now_dir :", os.getcwd())

    f_timetable = '../result_geotiff/floodpred_timetable_tif.csv'
    df_tt = pd.read_csv(f_timetable)

    f_stdate = '../result_geotiff/modellinkage_stime.csv'
    df_stdate_tmp = pd.read_csv(f_stdate, header=None)
    stdate = pd.to_datetime(df_stdate_tmp.iloc[0])
    s_format = '%Y%m%d%H%M'

    zoom_levels = np.arange(8, 18)
    output_date = datetime.now()
    output_directory = "../output_tilemaps/" + datetime.strftime(output_date, s_format)

    with open("config_geotiff2tiledmap.yml", "r", encoding="UTF-8") as yml:
        config = yaml.safe_load(yml)

    h_threshold = 0.10
    colormap = "viridis"  # 任意に変更可
    CTM = create_tiledmap(h_threshold, colormap_name=colormap)

    for t, i in enumerate(df_tt["id"]):
        time = datetime.strftime(stdate.iloc[0] + timedelta(seconds=1) * df_tt["pred"][t], s_format)
        input_file = "../result_geotiff/result_" + str(int(i)) + ".tif"

        for z in zoom_levels:
            CTM.create_tiled_map_with_zoom_level_and_colormap(input_file, output_directory, str(time), z)
