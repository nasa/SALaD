#Copyright © 2020 United States Government as represented by the
#Administrator of the National Aeronautics and Space Administration.
#All Rights Reserved.

import os
from osgeo import gdal
import numpy as np
from otbApp import otbApp

class PreProcessing(object):
    
    def __init__(self,
                 pathToFile,
                 imageFile,
                 demFile, 
                 outPath):
        
        if not pathToFile:
            raise RuntimeError('A path to a file must be specified')
        
        if not os.path.exists(pathToFile):
            raise RuntimeError(str(pathToFile) + 'does no exist.')
        
        
        self.imgFile = os.path.join(pathToFile,imageFile)
        self.demFile = os.path.join(pathToFile, demFile)
        
        nm = imageFile.split('.')[0]
        self._fileName=nm
        
        if not os.path.isfile(self.imgFile):
            raise RuntimeError('An image must be specified')
        
        if not os.path.isfile(self.demFile):
            raise RuntimeError('A DEM must be specified')
        
        self._outPath = outPath
   
    def getImgInfo(self, image, band=1):
        """ Extract metadata from geotiff """
        img = gdal.Open(image)
        if img is None:
            raise RuntimeError('Unable to open '+str(self.imagFile))
        
        self._rows = img.RasterYSize
        self._cols = img.RasterXSize
        
        bd = img.GetRasterBand(band)
        arr = bd.ReadAsArray()
        self._maxvalue = arr.max()
        
        self._geo=img.GetGeoTransform()
        self._proj=img.GetProjection()
                       
        img = None
 
    def _writeTiff (self, filename, xsize, ysize, band, gdaltype, 
                    geo, proj,data):
        """ Write geotiff """
        driver = gdal.GetDriverByName("GTiff")
        out = driver.Create(filename, xsize, ysize, band, gdaltype)
        out.SetGeoTransform(geo)
        out.SetProjection(proj)
        out.GetRasterBand(1).WriteArray(data)

    
        
    def generateGLCM(self): 
        """ Compute textural features using OTB application """               
        self.getImgInfo(self.imgFile, 3)
        
        mean_stack=np.zeros((4,self._rows,self._cols))
        homog_stack=np.zeros((4,self._rows,self._cols))
        
        for x in range(4):
            
            if x==0:
                cx=0
                cy=1
                dir=0
            elif x==1:
                cx=1
                cy=1
                dir=45
            elif x==2:
                cx=1
                cy=0
                dir=90
            else:
                cx=1
                cy=-1
                dir=135
            
            tmpfile = "mean_"+str(dir)+".tif"    
            otbApp.runTextureExtraction(self.imgFile, 3, tmpfile, 
                             cx, cy, 3, 3, 0, int(self._maxvalue), 32, 'advanced')
            fd = gdal.Open( tmpfile )
            band = fd.GetRasterBand(1)
            arr = band.ReadAsArray()
            mean_stack[x,:] = arr
            os.remove(tmpfile)
            
            tmpfile = "homog_"+str(dir)+".tif"
            otbApp.runTextureExtraction(self.imgFile, 3, tmpfile, 
                             cx, cy, 3, 3, 0, int(self._maxvalue), 32, 'simple')
            fd = gdal.Open( tmpfile )
            band = fd.GetRasterBand(4)
            arr = band.ReadAsArray()
            homog_stack[x,:] = arr
            os.remove(tmpfile)

                               
        glcm_mean = np.mean(mean_stack, axis=0)
        glcm_homog = np.mean(homog_stack, axis=0)
        
        name = "mean_"+self._fileName+".tif"
        mean_outfile = os.path.join(self._outPath, name)
        self._writeTiff(mean_outfile, self._cols, self._rows, 1, gdal.GDT_Float32,
                        self._geo, self._proj, glcm_mean)

        name = "homog_"+self._fileName+".tif"
        homog_outfile = os.path.join(self._outPath, name)
        self._writeTiff(homog_outfile, self._cols, self._rows, 1, gdal.GDT_Float32,
                        self._geo, self._proj, glcm_homog)

    def generateSlope(self):
        """ Generate slope and clip """ 
        gdal.DEMProcessing('slope.tif',self.demFile,'slope')
        slope="slope.tif"

        self.getImgInfo(self.imgFile, 1)      

        minx = self._geo[0]
        maxy = self._geo[3]
        maxx = minx + self._geo[1] * self._cols
        miny = maxy + self._geo[5] * self._rows

        name = "slope_"+self._fileName+".tif"
        slope_outfile = os.path.join(self._outPath, name)
        gdal.Translate(slope_outfile,slope,width=self._cols,height=self._rows,
                       resampleAlg=0,format='GTiff',projWin=[minx,maxy,maxx,miny])
        os.remove("slope.tif")
             
    def generateIndex(self):
        """ Compute Brightness and NDVI """         
        self.getImgInfo(self.imgFile, 3)
        
        img = gdal.Open(self.imgFile)
        
        blue_band = img.GetRasterBand(1)
        green_band = img.GetRasterBand(2)
        red_band = img.GetRasterBand(3)
        nir_band = img.GetRasterBand(5)

        red = red_band.ReadAsArray()
        blue = blue_band.ReadAsArray()
        green = green_band.ReadAsArray()
        nir = nir_band.ReadAsArray()

        red_flt = red.astype(np.float32)
        nir_flt = nir.astype(np.float32)

        np.seterr(divide='ignore', invalid='ignore')
        
        ndvi=(nir_flt-red_flt)/(nir_flt+red_flt)
        name = "ndvi_"+self._fileName+".tif"
        ndvi_outfile = os.path.join(self._outPath, name)
        self._writeTiff(ndvi_outfile, self._cols, self._rows, 1, gdal.GDT_Float32,
                        self._geo, self._proj, ndvi)        

        bright=(blue+green+red+nir)/4
        name = "bright_"+self._fileName+".tif"
        bright_outfile = os.path.join(self._outPath, name)
        self._writeTiff(bright_outfile, self._cols, self._rows, 1, gdal.GDT_Float32,
                        self._geo, self._proj, bright)
      
    # run    
    def run(self):
        print("Computing Textural Features")
        self.generateGLCM()
        print("Computing Slope")
        self.generateSlope()
        print("Computing NDVI and Brightness")
        self.generateIndex()
        


        
            
        
    
    
