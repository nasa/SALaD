#Copyright © 2020 United States Government as represented by the
#Administrator of the National Aeronautics and Space Administration.
#All Rights Reserved.

import otbApplication
import os

# -----------------------------------------------------------------------------
# class OTBApp
# -----------------------------------------------------------------------------

#Default maximum memory that OTB should use for processing, in MB. If not set, default value is 128 MB.
os.environ["OTB_MAX_RAM_HINT"] = "50000"

class otbApp(object):
    
    # OTB application computes Haralick features
    # ref: 
    # https://www.orfeo-toolbox.org/CookBook/Applications/app_HaralickTextureExtraction.html
    @staticmethod
    def runTextureExtraction(image, channel,outfile, 
                             xoff, yoff, xrad, yrad, 
                             vmin,vmax,bin, texture):
        # The following lines set all the application parameters:
        app = otbApplication.Registry.CreateApplication("HaralickTextureExtraction")

        app.SetParameterString("in", image)
        
        app.SetParameterString("out", outfile)

        app.SetParameterInt("channel", channel)

        app.SetParameterInt("parameters.xoff", xoff)

        app.SetParameterInt("parameters.yoff", yoff)

        app.SetParameterInt("parameters.xrad", xrad)

        app.SetParameterInt("parameters.yrad", yrad)

        app.SetParameterInt("parameters.min", vmin)

        app.SetParameterInt("parameters.max", vmax)

        app.SetParameterInt("parameters.nbbin", bin)

        app.SetParameterString("texture", texture)
        
        app.ExecuteAndWriteOutput()

    # Perform Large-Scale Mean-Shift segmentation workflow (LSMS)
    # ref:
    # https://www.orfeo-toolbox.org/CookBook/Applications/app_MeanShiftSmoothing.html
    # https://www.orfeo-toolbox.org/CookBook/Applications/app_MeanShiftSmoothing.html
    # https://www.orfeo-toolbox.org/CookBook/Applications/app_LSMSSmallRegionsMerging.html
    @staticmethod
    def runLSMS(image,segOut,
                spatialr=10, ranger=16,
                tilesizex=500, tilesizey=500, 
                sm_thres=0.1, sm_maxiter=100,
                seg_minsize=0, merg_minsize=10):
        # The following line creates an instance of the MeanShiftSmoothing application
        app1 = otbApplication.Registry.CreateApplication("MeanShiftSmoothing")

        # The following lines set all the application parameters:
        app1.SetParameterString("in", image)

        app1.SetParameterInt("spatialr", spatialr)

        app1.SetParameterFloat("ranger", ranger)

        app1.SetParameterFloat("thres", sm_thres)

        app1.SetParameterInt("maxiter", sm_maxiter)


        # The following line execute the application
        app1.Execute()



        # The following line creates an instance of the LSMSSegmentation application
        app2 = otbApplication.Registry.CreateApplication("LSMSSegmentation")

        # The following lines set all the application parameters:
        app2.ConnectImage("in", app1, "fout")

        #LSMSSegmentation.SetParameterString("out", seg_out)

        app2.SetParameterFloat("spatialr", spatialr)

        app2.SetParameterFloat("ranger", ranger)

        app2.SetParameterInt("minsize", seg_minsize)

        app2.SetParameterInt("tilesizex", tilesizex)

        app2.SetParameterInt("tilesizey", tilesizey)

        # The following line execute the application
        app2.Execute()
        

        # The following line creates an instance of the LSMSSmallRegionsMerging application
        app3 = otbApplication.Registry.CreateApplication("LSMSSmallRegionsMerging")

        # The following lines set all the application parameters:
        app3.SetParameterString("in", image)

        app3.ConnectImage("inseg", app2, "out")

        app3.SetParameterString("out", segOut)

        app3.SetParameterInt("minsize", merg_minsize)

        app3.SetParameterInt("tilesizex", tilesizex)

        app3.SetParameterInt("tilesizey", tilesizey)

        # The following line execute the application
        app3.ExecuteAndWriteOutput()
