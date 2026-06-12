# Custom protobuf setup guide

This is for if you have a different version of protobuf installed
globally than what's required and dont want to override it.

## Build protobuf and protoc

You will need to do this once.

1. Run `mkdir -p third_party && cd third_party` to ensure the directory exists.
2. Run `git clone https://github.com/protocolbuffers/protobuf.git` to clone `protobuf`.
3. Run `cd protobuf && git checkout v30.1` to checkout the required version.
4. Run `mkdir -p build_protoc && cd build_protoc && cmake .. -Dprotobuf_BUILD_TESTS=OFF && cmake --build .` to build `protoc`.
5. Run `cd .. && cmake -S . -B build -Dprotobuf_BUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX=install && cmake --build build --target install` to build `protobuf`.

## Setup protoc alias

You will need to do this whenever you need to use `protoc`.

Run `alias protoc="$(pwd)/third_party/protobuf/build_protoc/protoc"`

## Modify CMake build script

You will need to do this once.

Make the following changes to `CMakeLists.txt` in the root directory.

> [!NOTE]
> The code might not match exactly if it has been modified since this was written.

Remove the protobuf dependency lines:

```cmake
# line ~56
fetch_git_dependency(abseil "absl" "https://github.com/abseil/abseil-cpp.git" "20250127.1")

# line ~67
fetch_git_dependency(Protobuf "Protobuf" "https://github.com/protocolbuffers/protobuf.git" ${protobufVersionString})

# line ~79
find_library(UTF8_RANGE_LIBRARY NAMES utf8_range
    HINTS
    ${CMAKE_PREFIX_PATH}/lib
    $ENV{HOME}/protobuf-install/lib
    ${PROTOBUF_ROOT_DIR}/lib
    ${Protobuf_DIR}/../lib
    ${Protobuf_DIR}/../../lib)

find_path(UTF8_RANGE_INCLUDE_DIR NAMES utf8_range.h
    HINTS
    ${CMAKE_PREFIX_PATH}/include
    $ENV{HOME}/protobuf-install/include
    ${PROTOBUF_ROOT_DIR}/include
    ${Protobuf_DIR}/../include
    ${Protobuf_DIR}/../../include
    ${PROTOBUF_SOURCE_DIR}/third_party/utf8_range)
message(STATUS "utf8_range library found at:     ${UTF8_RANGE_LIBRARY}")
message(STATUS "utf8_range include dir found at: ${UTF8_RANGE_INCLUDE_DIR}")

```

Add built protobuf.

```cmake
# line ~67
set(Protobuf_DIR "./third_party/protobuf/install/lib/cmake/protobuf" CACHE PATH "Custom Protobuf build")
set(utf8_range_DIR "./third_party/protobuf/install/lib/cmake/utf8_range" CACHE PATH "Custom Protobuf build")
set(absl_DIR "./third_party/protobuf/install/lib/cmake/absl" CACHE PATH "Custom Protobuf build")
find_package(utf8_range REQUIRED CONFIG)
find_package(absl REQUIRED CONFIG)
find_package(Protobuf REQUIRED CONFIG)
```

Replace `UTF8_RANGE_LIBRARY` with built protobuf.

```diff
# line ~132
-${UTF8_RANGE_LIBRARY}
+utf8_range::utf8_range

# line ~206
-    ${UTF8_RANGE_INCLUDE_DIR}

# line ~221
-    ${UTF8_RANGE_LIBRARY}
+    utf8_range::utf8_range
```

## Finally

Finally run the build to check its all working.

```bash
source ./.venv/bin/activate && rocket dev --interface test --nopendant
```
