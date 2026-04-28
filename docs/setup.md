# Setup

The GCS software is run by using a Python based CLI with a C++ server component. There are several dev tools used for testing included in the dependencies as well

## Setup

For a minimal clean slate installation, you can get away with:

1. Setting up your Linux environment
2. Installing `cmake` (see version below), `git`,`socat`, `python`, `qrencode`, `swig`, `zmq`, (see version below) and cpp compilers (`CXX20`) with your package manager
3. Clone and `cd` in to the repository
4. Run `bash setup.sh` to verify installs, setup python, and the rocket alias
5. Run `source .venv/bin/activate` to use the python environment
6. Run `rocket dev --interface test --nopendant` to install other libraries automatically and build the project

> [!NOTE]
> You can run the CLI with `$ python rocket.py <args>` in place of `$ rocket <args>` if you don't run the setup file.

> [!NOTE]
> \*Protobuf gencode without building can be done by running the proto script in `scripts/`.
>
> Some C++ libraries have untested `FetchContent` support for cmake. This means you may be able to build after installing just CMake. Provided you are connected to internet to download those packages. Currently they do not work. Protobuf is a pain in the ass to work with.
>
> Also running setup.sh will install Protobuf automatically

| Software       | Version        | Release Mode   | Native Dev  |
| -------------- | -------------- | -------------- | ----------- |
| Python         | `3.11.x`       | ✅             | ✅          |
| Socat          | `>=1.8.0.0`    | ❌             | ✅          |
| Cmake          | `>=3.25`       | ❌             | 🟨          |
| g++ or clang++ | Supports C++20 | ❌             | 🟨          |
| libzmq         | `4.3.x`        | ❌?            | 🟨          |
| cppzmq         | `4.10.x`       | ❌?            | 🟨          |
| Abseil         | `20250127.x`   | ❌?            | 🟨          |
| Protobuf       | `30.x`         | ✅ for gencode | ✅          |
| qrencode       | `>=4.1.0`      | ✅             | ✅          |
| swig           | `>=4.3`        | ❌             | ✅          |
| pytest         | `8.3.x`        | for testing    | for testing |
| googletest     | `1.16.x`       | for testing    | for testing |

> [!NOTE]
> Items denoted with 🟨 are not required if you use release binaries. Install these if you want to build yourself with debug binaries

> [!NOTE]
> If you have a different version of protobuf installed globally and dont want to override it refer to [this](protobuf.md).

## Further Steps

See [usage](usage.md)

---

[Home](../README.md)
