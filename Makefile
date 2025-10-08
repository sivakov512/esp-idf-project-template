.PHONY: libs-test-build libs-test libs-test-clean build

LIBS_UNITY_DIR := libs/unity
LIBS_UNITY_BUILD_DIR := $(LIBS_UNITY_DIR)/build

libs-test-build:
	cmake -S ${LIBS_UNITY_DIR} -B ${LIBS_UNITY_BUILD_DIR} -DCMAKE_BUILD_TYPE=Debug
	cmake --build ${LIBS_UNITY_BUILD_DIR} -j

libs-test: libs-test-build
	ctest --test-dir ${LIBS_UNITY_BUILD_DIR} --output-on-failure -V

libs-test-clean:
	rm -rf ${LIBS_UNITY_BUILD_DIR}

build:
	idf.py build
