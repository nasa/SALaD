#Copyright © 2020 United States Government as represented by the
#Administrator of the National Aeronautics and Space Administration.
#All Rights Reserved.

import itertools
import multiprocessing
from rasterstats import zonal_stats
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import os
import fiona
import geopandas as gpd
from functools import partial

def chunks(data, n):
    """Break down polygons into chunks"""
    for i in range(0, len(data), n):
        yield data[i:i+n]

def zonal_stats_wrapper(feats, tif, stats):
    return zonal_stats(feats, tif, stats=stats, nodata=-999)

def zonal_stats_parallel(features, cores, raster, opr):
    """Compute zonal_stats in parallel"""
    p = multiprocessing.Pool(cores)
    func = partial(zonal_stats_wrapper, tif=raster, stats=opr)
    stats_lists = p.map(func, chunks(features, cores))
    stat = list(itertools.chain(*stats_lists))
    p.close()
    return stat

class Detection(object):
    def __init__(self, pathToFile,
                 segFile, brightFile, ndviFile, 
                 slopeFile, homogFile, meanFile,
                 outPath, outFile, Tree): 
               
        if not pathToFile:
            raise RuntimeError('A path to a file must be specified')
        
        if not os.path.exists(pathToFile):
            raise RuntimeError(str(pathToFile) + 'does no exist.')
        
        self.segfile = os.path.join(pathToFile, segFile)        
        if not os.path.isfile(self.segfile):
            raise RuntimeError('A segmented shape file must be specified')
 
        self.brightfile = os.path.join(pathToFile, brightFile)      
        if not os.path.isfile(self.brightfile):
            raise RuntimeError('A brightness file must be specified')

        self.ndvifile = os.path.join(pathToFile, ndviFile) 
        if not os.path.isfile(self.ndvifile):
            raise RuntimeError('A NDVI file must be specified')
      
        self.slopefile = os.path.join(pathToFile, slopeFile) 
        if not os.path.isfile(self.slopefile):
            raise RuntimeError('A slope file must be specified')
 
        self.homogfile = os.path.join(pathToFile, homogFile)
        if not os.path.isfile(self.homogfile):
            raise RuntimeError('A GLCM Homogeneity file must be specified')

        self.meanfile = os.path.join(pathToFile, meanFile)        
        if not os.path.isfile(self.meanfile):
            raise RuntimeError('A GLCM Mean file must be specified')

        self.trainfile=pathToFile+"training.shp"
        self.tree = Tree      
        self.outfile = os.path.join(outPath, outFile)
    
    def run(self):
        
        shp_file = self.segfile
        
        rasters = {'brightness' : self.brightfile,
                   'ndvi'       : self.ndvifile,
                   'slope'      : self.slopefile,
                   'glcmhomog'  : self.homogfile,
                   'glcmmean'   : self.meanfile}
        
        # dictionary to host output zonal stats
        out_stat = dict.fromkeys(rasters)

        # open shapefile and read features once
        with fiona.open(shp_file) as src:
            features = list(src)
    
        cores = os.cpu_count()
        
        print("Running zonal_stats with "+str(cores)+" CPUs")
        for k in rasters.keys():
            stat = zonal_stats_parallel(features, cores, rasters[k], 'mean')
            out_stat[k] = list(d["mean"] for d in stat)
        
        df = gpd.read_file(shp_file)
        df["Meanbright"] = out_stat['brightness']
        df["Meanndvi"] = out_stat['ndvi']
        df["Meanslope"] = out_stat['slope']
        df["glcmhomog"] = out_stat['glcmhomog']
        df["glcmmean"] = out_stat['glcmmean']
        df_final = df.replace([np.inf, -np.inf], np.nan)
        df_final = df_final.fillna(0)

        print("Training RF model")
        df_train = gpd.read_file(self.trainfile)
        predictor_vars = ["Meanbright","Meanndvi","Meanslope","glcmhomog","glcmmean"]
        x, y = df_train[predictor_vars], df_train.landslide
        
        print("Fitting RF model")
        modelRandom = RandomForestClassifier(self.tree)
        modelRandom.fit(x, y)
        
        predictions = modelRandom.predict(df_final[predictor_vars])
        df_final["outcomes"] = predictions
        
        print("Writing outcomes")
        crs = df.crs
        df_land = df_final[df_final['outcomes']>0]
        df_land_dissolve = gpd.geoseries.GeoSeries([geom for geom in df_land.unary_union.geoms])
        df_land_dissolve.crs = crs
        df_land_dissolve.to_file(self.outfile)
