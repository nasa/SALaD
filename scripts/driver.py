#Copyright © 2020 United States Government as represented by the
#Administrator of the National Aeronautics and Space Administration.
#All Rights Reserved.

import sys
import os
import glob
import argparse
from preprocessing import PreProcessing
from segmentation import Segmentation
from detection import Detection



def main():
    parser = argparse.ArgumentParser(description='SALaD')
    parser.add_argument('-i','--image', help='name of image file')
    parser.add_argument('-d','--dem', help='name of DEM file')
    parser.add_argument('-l','--landslides', 
        help='name of manual landslide shapefile for generating training file, e.g. "manual_landslide.shp"')
    parser.add_argument('-lx','--ulx', type=float, 
        help='upper left x coordinate of training area')
    parser.add_argument('-ly','--uly', type=float, 
        help='upper left y coordinate of training area')
    parser.add_argument('-rx','--lrx', type=float, 
        help='lower left x coordinate of training area')
    parser.add_argument('-ry','--lry', type=float, 
        help='lower left y coordinate of training area')
    parser.add_argument('-rmi','--hr_min', type=int, 
        help='minimum range radius for POF')
    parser.add_argument('-rma','--hr_max', type=int, 
        help='maximum range radius for POF')
    parser.add_argument('-s', '--step', type=int, default=2,
        help='step size for POF')
    parser.add_argument('-hs', '--spatialr', type=int, default=10,
        help='spatial radius')
    parser.add_argument('-m', '--objectsize', type=int, default=10,
        help='minimum object size')
    parser.add_argument('-p', '--path', help='location of input files')
    parser.add_argument('-op', '--outpath', help='location of output files')
    parser.add_argument('-r', '--result', 
        help='name of output shapefile, e.g. "landslide_SALaD.shp"')
    parser.add_argument('-o', '--overlap', type=float, default=50.0,
        help='overlap required between manual landslide and segmented polygons to generate a training file')
    parser.add_argument('-t', '--tree', type=int, default=500,
        help='The number of trees in the random forest')

    args = parser.parse_args()

    if args.path:
        input_path = args.path
    else: 
        input_path = os.getcwd()

    image_file = args.image
    dem_file = args.dem

    if args.outpath:
        output_path = args.outpath
    else: 
        output_path = os.getcwd()

    ulx = args.ulx
    uly = args.uly
    lrx = args.lrx
    lry = args.lry

    hr_min = args.hr_min
    hr_max = args.hr_max
    step_size = args.step
    spatial_radius = args.spatialr
    object_size = args.objectsize

    landslides=args.landslides
    overlap=args.overlap
    tree=args.tree

    if args.result:
        output_file = args.result
    else:
        output_file = f'{image_file}.shp'

    if not os.path.exists(input_path):
        raise RuntimeError('A path to raw data must be specified')
        
    if not os.path.exists(output_path):
        raise RuntimeError('A path for random forest inputs must be specified')
    
    if not os.path.isfile(os.path.join(input_path, image_file)):
        raise RuntimeError('An image must be specified')
           
    if not os.path.isfile(os.path.join(input_path, dem_file)):
        raise RuntimeError('A DEM must be specified')
        
    #file id derived from raw data 
    tag = image_file.split('.')[0]
    
    # generate 5 geotiff
    step1 = PreProcessing(pathToFile=input_path, imageFile=image_file, demFile=dem_file, outPath=output_path)
    step1.run()
    print("Preprocessing Completed")

    homogfile = "homog_"+tag+".tif"
    meanfile = "mean_"+tag+".tif"
    slopefile = "slope_"+tag+".tif"
    brightfile = "bright_"+tag+".tif"
    ndvifile = "ndvi_"+tag+".tif" 
    
    #segmentation to generate a shape file
    step2 = Segmentation(pathToFile=input_path, imageFile=image_file, 
                        Manual=landslides, brightFile=brightfile, 
                        ndviFile=ndvifile, slopeFile=slopefile, 
                        homogFile=homogfile, meanFile=meanfile, 
                        outPath=output_path, overLap=overlap, 
                        ulX=ulx, ulY=uly, lrX=lrx, lrY=lry, 
                        hr_Min=hr_min, hr_Max=hr_max, Step_Size=step_size,
                        Spatial_Radius=spatial_radius, Object_Size=object_size)
    step2.run()
    print("Segmentation Completed")

    segfile = tag+".shp"

    # Delete temporary files produced during segmentation
    for f in glob.glob("*_FINAL.tif"):
    	os.remove(f) 

    # random forest model to detect landslides
    step3 = Detection(pathToFile=output_path,
                      segFile=segfile, brightFile=brightfile, 
                      ndviFile=ndvifile, slopeFile=slopefile, 
                      homogFile=homogfile, meanFile=meanfile, 
                      outPath=output_path, outFile=output_file, Tree=tree)
    step3.run()
    print("SALaD Completed")
    

if __name__ == "__main__":
    sys.exit(main())
    
