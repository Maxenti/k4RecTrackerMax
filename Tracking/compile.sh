cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker
rm -rf build install
mkdir build install
cd build
cmake .. -DCMAKE_CXX_STANDARD=20 -DCMAKE_INSTALL_PREFIX=../install -DCMAKE_PREFIX_PATH=$HOME/FCCWork/genfit2/install/ -DGENFIT2_INCLUDE_DIR=$HOME/FCCWork/genfit2/install/include -DGENFIT2_LIBRARY=$HOME/FCCWork/genfit2/install/lib64/libgenfit2.so
make install
