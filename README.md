# SALaD
SALaD (Semi-Automatic Landslide Detection) is a landslide mapping system. SALaD utilizes Object-based Image Analysis and Random Forest to map landslides. It requires optical imagery, a DEM, corner coordinates of a training area, and manually mapped landslides within the training area. The code is built to run primarily on a Linux.

# Installation
1.	Install Singularity

User can find thorough instruction for installation of Singularity >=3.0.0 on different operating systems (Linux, Windows or Mac) here:
https://sylabs.io/guides/3.0/user-guide/installation.html 

2.	Build a Singularity container from Singularity definition file

Singularity definition files can be used as the target when building a container. Assuming user has the definition file called SALaD.def (see below), the container (named ilab-salad.sif) can be built with the command:

$ sudo singularity build ilab-salad.sif SALaD.def
       
For more details, check:  
https://sylabs.io/guides/3.0/user-guide/build_a_container.html
             
If you don’t have root access on a Linux machine or want to host your container on the cloud, you can build the container on the Remote Builder: https://cloud.sylabs.io/builder
# Executing SALaD from a container
singularity run -B <local_dir> < path_to_singularity_container>/ilab-salad.sif python <path_to_scripts>/driver.py -i "image.tif" -d "srtm.tif" -l "manual_landslide.shp" -lx 308335 -ly 3114295 -rx 312440 -ry 3109225 -rmi 2 -rma 32 -s 2 -p "<path_to_input_data_folder>" -op "<path_to_output_folder>" -r "landslide_SALaD.shp" 
# Example definition file (SALaD.def)
	Bootstrap: docker
	FROM: nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04
	

	%labels
	    Author Remi Cresson <remi.cresson[at]irstea[dot]fr>
	    Version v1.0.0
	

	%help
	========================================================================
	        - Orfeo Toolbox (without Tensor Flow)
	========================================================================
	

	%environment
	    # ------------------------------------------------------------------
	    # Add important environment variables
	    # ------------------------------------------------------------------
	    export PATH="$PATH:/work/otb/superbuild_install/bin/"
	    export PYTHONPATH="/work/otb/superbuild_install/lib/otb/python:$PYTHONPATH"
	    export OTB_APPLICATION_PATH="/work/otb/superbuild_install/lib/otb/applications"
	    export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/work/otb/superbuild_install/lib/:/work/tf/installdir/lib/"
	    # set PYTHONPATH for access to OTB application
	    export PYTHONPATH="/usr/local/otb/src/innovation-lab:$PYTHONPATH"
	

	%post
	apt-get update -y \
	 && apt-get upgrade -y \
	 && apt-get install -y --no-install-recommends \
	        git
	

	    # retrieve OTB source from git repository and open permissions
	    mkdir -p /usr/local/otb
	    git clone --single-branch --branch otb-container https://github.com/nasa-nccs-hpda/innovation-lab.git /usr/local/otb
	    chmod a+rwx -R /usr/local/otb
	

	apt-get update -y \
	 && apt-get upgrade -y \
	 && apt-get install -y --no-install-recommends \
	        sudo \
	        ca-certificates \
	        curl \
	        make \
	        cmake \
	        g++ \
	        gcc \
	        git \
	        libtool \
	        swig \
	        xvfb \
	        wget \
	        autoconf \
	        automake \
	        pkg-config \
	        zip \
	        zlib1g-dev \
	        unzip \
	 && rm -rf /var/lib/apt/lists/*
	

	# ---------------------------------------------------------------------------
	# OTB and TensorFlow dependencies
	# ---------------------------------------------------------------------------
	apt-get update -y \
	 && apt-get upgrade -y \
	 && apt-get install -y --no-install-recommends \
	        freeglut3-dev \
	        libboost-date-time-dev \
	        libboost-filesystem-dev \
	        libboost-graph-dev \
	        libboost-program-options-dev \
	        libboost-system-dev \
	        libboost-thread-dev \
	        libcurl4-gnutls-dev \
	        libexpat1-dev \
	        libfftw3-dev \
	        libgdal-dev \
	        libgeotiff-dev \
	        libglew-dev \
	        libglfw3-dev \
	        libgsl-dev \
	        libinsighttoolkit4-dev \
	        libkml-dev \
	        libmuparser-dev \
	        libmuparserx-dev \
	        libopencv-core-dev \
	        libopencv-ml-dev \
	        libopenthreads-dev \
	        libossim-dev \
	        libpng-dev \
	        libqt5opengl5-dev \
	        libqwt-qt5-dev \
	        libsvm-dev \
	        libtinyxml-dev \
	        qtbase5-dev \
	        qttools5-dev \
	        default-jdk \
	        python3-pip \
	        python3.6-dev \
	        python3.6-gdal \
	        python3-setuptools \
	        libxmu-dev \
	        libxi-dev \
	        qttools5-dev-tools \
	        bison \
	        software-properties-common \
	        dirmngr \
	        apt-transport-https \
	        lsb-release \
	        gdal-bin \
	 && rm -rf /var/lib/apt/lists/*
	

	# ---------------------------------------------------------------------------
	# Python packages
	# ---------------------------------------------------------------------------
	ln -s /usr/bin/python3 /usr/bin/python \
	 && python3 -m pip install --upgrade pip \
	 && python3 -m pip install pip six numpy wheel mock keras future
	

	# ---------------------------------------------------------------------------
	# Build OTB: Stage 1 (clone)
	# ---------------------------------------------------------------------------
	mkdir -p /work/otb \
	 && cd /work/otb \
	 && git clone https://gitlab.orfeo-toolbox.org/orfeotoolbox/otb.git otb \
	 && cd otb \
	 && git checkout release-7.0
	

	# ---------------------------------------------------------------------------
	# Build OTB: Stage 2 (superbuild)
	# ---------------------------------------------------------------------------
	mkdir -p /work/otb/build \
	 && cd /work/otb/build \
	 && cmake /work/otb/otb/SuperBuild \
	        -DUSE_SYSTEM_BOOST=ON \
	        -DUSE_SYSTEM_CURL=ON \
	        -DUSE_SYSTEM_EXPAT=ON \
	        -DUSE_SYSTEM_FFTW=ON \
	        -DUSE_SYSTEM_FREETYPE=ON \
	        -DUSE_SYSTEM_GDAL=ON \
	        -DUSE_SYSTEM_GEOS=ON \
	        -DUSE_SYSTEM_GEOTIFF=ON \
	        -DUSE_SYSTEM_GLEW=ON \
	        -DUSE_SYSTEM_GLFW=ON \
	        -DUSE_SYSTEM_GLUT=ON \
	        -DUSE_SYSTEM_GSL=ON \
	        -DUSE_SYSTEM_ITK=ON \
	        -DUSE_SYSTEM_LIBKML=ON \
	        -DUSE_SYSTEM_LIBSVM=ON \
	        -DUSE_SYSTEM_MUPARSER=ON \
	        -DUSE_SYSTEM_MUPARSERX=ON \
	        -DUSE_SYSTEM_OPENCV=ON \
	        -DUSE_SYSTEM_OPENTHREADS=ON \
	        -DUSE_SYSTEM_OSSIM=ON \
	        -DUSE_SYSTEM_PNG=ON \
	        -DUSE_SYSTEM_QT5=ON \
	        -DUSE_SYSTEM_QWT=ON \
	        -DUSE_SYSTEM_TINYXML=ON \
	        -DUSE_SYSTEM_ZLIB=ON \
	        -DUSE_SYSTEM_SWIG=OFF \
	        -DOTB_WRAP_PYTHON=OFF \
	 && make -j $(grep -c ^processor /proc/cpuinfo)
	

	# ---------------------------------------------------------------------------
	# Build OTB: Stage 3 (bindings)
	# ---------------------------------------------------------------------------
	cd /work/otb/otb/Modules/Remote \
	 && git clone https://github.com/remicres/otbtf.git \
	 && cd /work/otb/build/OTB/build \
	 && cmake /work/otb/otb \
	        -DOTB_WRAP_PYTHON=ON \
	        -DPYTHON_EXECUTABLE=/usr/bin/python3.6 \
	        -Dopencv_INCLUDE_DIR=/usr/include \
	        -DModule_OTBTensorflow=ON \
	        -DOTB_USE_TENSORFLOW=OFF \
	        -DTENSORFLOW_CC_LIB=/work/tf/installdir/lib/libtensorflow_cc.so \
	        -DTENSORFLOW_FRAMEWORK_LIB=/work/tf/installdir/lib/libtensorflow_framework.so \
	        -Dtensorflow_include_dir=/work/tf/installdir/include/ \
	 && cd /work/otb/build/ \
	 && make -j $(grep -c ^processor /proc/cpuinfo)
	

	

	# ---------------------------------------------------------------------------
	# Install Packages and Retrieve Source Code
	# ---------------------------------------------------------------------------
	    pip3 install --upgrade richdem==0.3.4
	    pip3 install --upgrade fiona==1.8.13
	    pip3 install --upgrade geopandas==0.7.0
	    pip3 install --upgrade numba==0.49.1
	    pip3 install --upgrade pandas==1.0.3
	    pip3 install --upgrade peakutils==1.3.3
	    pip3 install --upgrade rasterstats==0.14.0
	    pip3 install --upgrade scikit-learn==0.21.3
	

	# Below added 7/15/21
	

	     sudo apt-get update
	     sudo apt-get install -y libspatialindex-dev
	

	     pip3 install Pysal==1.14.4 
	     pip3 install rtree==0.8.3 


