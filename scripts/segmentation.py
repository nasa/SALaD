#Copyright © 2020 United States Government as represented by the
#Administrator of the National Aeronautics and Space Administration.
#All Rights Reserved.

import pandas as pd
import numpy as np
import geopandas as gpd
from otbApp import otbApp
from osgeo import gdal, ogr, osr
import fiona
import pysal as ps
import itertools
import multiprocessing
from functools import partial
from rasterstats import zonal_stats
import os
import glob

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

class Segmentation(object):
    
    def __init__(self,
                 pathToFile, Manual,
                 imageFile, brightFile, ndviFile, 
                 slopeFile, homogFile, meanFile, 
                 outPath, overLap, ulX, ulY, lrX, lrY,
                 hr_Min,hr_Max, Step_Size, Spatial_Radius, Object_Size):        
        if not pathToFile:
            raise RuntimeError('A path to a file must be specified')
        
        if not os.path.exists(pathToFile):
            raise RuntimeError(str(pathToFile) + 'does not exist.')

        self.manual = os.path.join(pathToFile, Manual)
        if not os.path.isfile(self.manual):
            raise RuntimeError('A manual landslide shape file must be specified')
        
        self.imgFile = os.path.join(pathToFile,imageFile)
        if not os.path.isfile(self.imgFile):
            raise RuntimeError('An image must be specified')

        self.brightfile = os.path.join(outPath, brightFile)
        if not os.path.isfile(self.brightfile):
            raise RuntimeError('A brightness file must be specified')

        self.ndvifile = os.path.join(outPath, ndviFile) 
        if not os.path.isfile(self.ndvifile):
            raise RuntimeError('A NDVI file must be specified')
      
        self.slopefile = os.path.join(outPath, slopeFile) 
        if not os.path.isfile(self.slopefile):
            raise RuntimeError('A slope file must be specified')
 
        self.homogfile = os.path.join(outPath, homogFile)
        if not os.path.isfile(self.homogfile):
            raise RuntimeError('A GLCM Homogeneity file must be specified')

        self.meanfile = os.path.join(outPath, meanFile)        
        if not os.path.isfile(self.meanfile):
            raise RuntimeError('A GLCM Mean file must be specified')

        self.overlap = overLap        
        self.ulx=ulX
        self.uly=ulY
        self.lrx=lrX
        self.lry=lrY
        self.hr_min=hr_Min
        self.hr_max=hr_Max
        self.step_size=Step_Size 
        self.spatial_radius=Spatial_Radius
        self.object_size=Object_Size        
        self.outfile=outPath+"training.shp"


        nm = imageFile.split('.')[0]    
        self._fileName = nm
        self._img = self.imgFile
        self._outPath = outPath

    def rasterToShape(self, raster, shp):
        """Convert segmentation result from geotiff to shape file"""
        src_ds = gdal.Open(raster)
        srcband = src_ds.GetRasterBand(1)
        srs = osr.SpatialReference()
        srs.ImportFromWkt(src_ds.GetProjection())
        drv = ogr.GetDriverByName("ESRI Shapefile")
        seg_ds = drv.CreateDataSource(shp)
        seg_layer = seg_ds.CreateLayer(shp, srs = srs)
        gdal.Polygonize(srcband, None, seg_layer, -1, [], callback=None)
        seg_ds = None
    
    def getRadius(self):
        """Compute Range Radius and create training shapefile"""
        
        # Cut original image to extent of training area and compute hr using Plateau Objective Fucntion
        train_file=os.path.join(self._outPath, self._fileName+'_train.tif')
        gdal.Translate(train_file,self._img, format='GTiff', projWin=[self.ulx,self.uly,self.lrx,self.lry])
                
        hr_list = []
       
        for size in range(self.hr_min, self.hr_max, self.step_size):
            seg_Out = os.path.join(self._outPath, "merg_"+self._fileName+"_"+str(size)+".tif")
            shp_file = os.path.join(self._outPath, "seg_"+self._fileName+"_"+str(size)+".shp")
            
            otbApp.runLSMS(train_file, seg_Out, spatialr=self.spatial_radius, ranger=size, merg_minsize=self.object_size)
            
            self.rasterToShape(seg_Out, shp_file)
            
            shp_open=fiona.open(shp_file)

            with shp_open as src:
                features = list(src)
    
            cores = os.cpu_count()
        
            tif = self.brightfile

            brightness_mean = zonal_stats_parallel(features, cores, tif, "mean")
            brightness_mean_list = list(d["mean"] for d in brightness_mean)

            brightness_std = zonal_stats_parallel(features, cores, tif, "std")
            brightness_std_list = list(d["std"] for d in brightness_std)

            # calculate weighted variance
            df = gpd.read_file(shp_file)
            df['Meanbright']=brightness_mean_list
            df['std']=brightness_std_list
            df['area']=df['geometry'].area
            df['var']=df['std']*df['std']
            df['area_var']=df['var']*df['area']
            df_final = df.replace([np.inf, -np.inf], np.nan)
            df_final=df_final.fillna(0)
            df_final.to_file(shp_file)
            wt_var=df['area_var'].sum()/df['area'].sum()

            # calculate Moran's I
            W = ps.queen_from_shapefile(shp_file)
            moran = ps.Moran(df['Meanbright'].values, W)

            hr_list.append((size, wt_var, moran.I))
            os.remove(seg_Out)
            
            
        cols=['hr','v','I']
        hr_df = pd.DataFrame(hr_list,columns=cols)
        v_max = hr_df['v'].max()
        hr_df['F_v'] = (v_max - hr_df['v']) / (v_max - hr_df['v'].min())
        i_max = hr_df['I'].max()
        hr_df['F_I'] = (i_max - hr_df['I']) / (i_max - hr_df['I'].min())
        hr_df['F_v_I'] = hr_df['F_v'] + hr_df['F_I']
        F_plateau = hr_df['F_v_I'].max() - hr_df['F_v_I'].std()
        peak = hr_df.loc[hr_df['F_v_I'] > F_plateau]
        hr = peak['hr'].iloc[0]
        hr = int(hr)
        csv_file=os.path.join(self._outPath,'POF.csv')
        hr_df.to_csv(csv_file)

        return hr
    
    def training(self, shapeIn: str):
          
        rasters = {'ndvi'       : self.ndvifile,
                   'slope'      : self.slopefile,
                   'glcmhomog'  : self.homogfile,
                   'glcmmean'   : self.meanfile}
        
        # dictionary to host output zonal stats
        out_stat = dict.fromkeys(rasters)

        # open shapefile and read features once
        shp_open=fiona.open(shapeIn)
        with shp_open as src:
            features = list(src)
    
        cores = os.cpu_count()
        
        # loop through rasters for zonal stats
        for k in rasters.keys():
            tif = rasters[k]
            stat = zonal_stats_parallel(features, cores, tif, 'mean')
            out_stat[k] = list(d["mean"] for d in stat)
                
        # add feature back to shapefile
        df = gpd.read_file(shapeIn)
        df["Meanndvi"] = out_stat['ndvi']
        df["Meanslope"] = out_stat['slope']
        df["glcmhomog"] = out_stat['glcmhomog']
        df["glcmmean"] = out_stat['glcmmean']
        df_final = df.replace([np.inf, -np.inf], np.nan)
        df_final = df_final.fillna(0)

        # Select intersecting polygons
        select_feature = gpd.read_file(self.manual)
        selection = gpd.sjoin(df_final, select_feature, how='inner', op='intersects')
        selection["segment_ar"] = selection['geometry'].area
        final_select = selection[selection['index_right'] > 0]

        # Calculate overlap 
        intersections = gpd.overlay(select_feature, final_select, 
                                    how='intersection')
        intersections["overlap_ar"] = intersections['geometry'].area
        intersections["percentage"] = (intersections['overlap_ar']
                                        / intersections['segment_ar']*100)
        intersections = intersections.loc[:, ['geometry','percentage']]
        final_intersect=intersections[intersections['percentage']>=self.overlap]

        # Combine landslide and non-landslide objects
        landslide = gpd.sjoin(df_final, final_intersect, how="inner", op='contains')
        landslide['landslide'] = 1
        landslide.drop(['percentage','index_right'], axis=1, inplace=True)
        non_landslide = df_final.drop(landslide['FID'], errors='ignore')
        non_landslide['landslide'] = 0

        # Join and save the training data
        training = landslide.append(non_landslide)
        training = training.sort_values(by=['FID'])
        training = training.drop(['std','area','var','area_var','FID'], axis=1)
        training.to_file(self.outfile)
            
    def run(self):
        
        print("Computing Radius")
        hr = self.getRadius()
        
        segOut = os.path.join(self._outPath, "merg_"+self._fileName+".tif")
        shapeOut = os.path.join(self._outPath, self._fileName+".shp")

        print("Running OTB LSMS")
        otbApp.runLSMS(self._img, segOut, spatialr=self.spatial_radius, ranger=hr, merg_minsize=self.object_size)
        
        print("Writing Segmentation Result")
        self.rasterToShape(segOut, shapeOut)

        os.remove(segOut)
        
        print("Creating Training file")
        shape_training = os.path.join(self._outPath, 
                                    "seg_"+self._fileName+"_"+str(hr)+".shp")
        self.training(shape_training)

        # Remove files generated during POF
        for f in glob.glob(os.path.join(self._outPath,"seg_*.*")):
        	os.remove(f)
