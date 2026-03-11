BUILD_DIR="build-release"
mkdir -p $BUILD_DIR && cd $BUILD_DIR
echo "Creating release makefiles." && cmake -DCMAKE_BUILD_TYPE=Release .. &&
echo "Making release binaries." && make -j${nproc}
