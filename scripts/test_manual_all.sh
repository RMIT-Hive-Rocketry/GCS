set -e;
mkdir -p build-debug
cd build-debug;

cmake -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTS=ON  ..;
make;

echo "Running C++ and python tests with default compiler in Debug mode";
ctest --output-on-failure  --test-dir backend/tests --verbose;