import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt 
from matplotlib import animation


class view_predict:
    def __init__(self, pred_res , val_min , val_max, intval , rep_dely ):
        #flood_re[ t , i , j ]=>t = 時間ステップ、 j , i =>メッシュij
        self.timesteps = np.shape( pred_res )[0]
        self.pred_res = pred_res 

        self.val_min = val_min   #コンター高さ最小値
        self.val_max = val_max   #コンター高さ最大値
        self.intval = intval     #コンター更新のΔt（再生速度）
        self.rep_dely = rep_dely #コンター映像リプレイ時のディレイ

        self.view_result() #可視化

        
    def view_result(self):
        fig, ax = plt.subplots()
        ims=[]
    
        for i in range( self.timesteps ):     
            im = ax.imshow( np.flipud( self.pred_res[i] ) ,  #縦が反転しているので、修正する
                            animated=True, 
                            vmin = self.val_min , 
                            vmax = self.val_max  )
            
            ims.append([im])

        anim = animation.ArtistAnimation(fig, ims, 
                                         interval=self.intval ,
                                         repeat_delay = self.rep_dely )
        plt.show()

        #ani.save('anim.gif', writer="imagemagick")
        #ani.save('anim.mp4', writer="ffmpeg")
