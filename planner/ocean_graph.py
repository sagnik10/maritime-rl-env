import numpy as np

class OceanGrid:
    def __init__(self, res=2):
        self.res=res
        self.lats=np.arange(-80,80,res)
        self.lons=np.arange(-180,180,res)
        self.grid={(lat,lon):1 for lat in self.lats for lon in self.lons}
        self._mask_land()

    def _mask_land(self):
        for k in list(self.grid.keys()):
            lat,lon=k
            if (-30<lat<50 and -20<lon<50) or (10<lat<60 and 60<lon<140):
                self.grid[k]=0

    def neighbors(self,node):
        lat,lon=node
        steps=[(self.res,0),(-self.res,0),(0,self.res),(0,-self.res)]
        out=[]
        for d in steps:
            n=(round(lat+d[0],2),round(lon+d[1],2))
            if n in self.grid and self.grid[n]==1:
                out.append(n)
        return out
