CLANG_TIDY ?= clang-tidy
CLANG_TIDY_EXTRAS :=

UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
# Add path to SDK on MacOS
  XCRUN := $(shell command -v xcrun 2>/dev/null)
  ifneq ($(XCRUN),)
    SDK := $(shell xcrun --show-sdk-path 2>/dev/null)
    ifneq ($(SDK),)
      CLANG_TIDY_EXTRAS += --extra-arg=-isysroot$(SDK)
    endif
  endif
endif


# ---- Utils ----
.PHONY: _check-jq

__quote = $(foreach d,$(1),"$(d)")

_check-jq:
	@command -v jq >/dev/null || { echo "ERROR: jq not found. Install jq."; exit 1; }


# ---- Common ----
.PHONY: check-format

CLANG_FORMAT ?= clang-format

check-format:
		find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
			-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
			| xargs -0 ${CLANG_FORMAT} --dry-run --Werror


# ---- Clang compile_commands.json switching
.PHONY: use-host use-esp

__ln_cc = ln -sf "$(1)/build/compile_commands.json" compile_commands.json

use-esp:
	$(call __ln_cc,.)

use-host:
	$(call __ln_cc,tests/host)


# ---- Host ----
.PHONY: host-build host-test host-clean host-lint

__HOST_TESTS_DIR := tests/host
__HOST_TESTS_BUILD_DIR := $(__HOST_TESTS_DIR)/build
HOST_LINT_LIBS :=

host-build:
	cmake -S ${__HOST_TESTS_DIR} -B ${__HOST_TESTS_BUILD_DIR} -DCMAKE_BUILD_TYPE=Debug
	cmake --build ${__HOST_TESTS_BUILD_DIR} -j

host-test: host-build
	ctest --test-dir ${__HOST_TESTS_BUILD_DIR} --output-on-failure -V

host-clean:
	rm -rf ${__HOST_TESTS_BUILD_DIR}

host-lint: host-build
ifneq ($(strip $(HOST_LINT_LIBS)),)
	find $(call __quote,$(HOST_LINT_LIBS)) \
       	\( -type d -name include_esp -prune \) \
       	-o \
	    \( -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
		-print0 \) \
	| xargs -0 $(CLANG_TIDY) $(CLANG_TIDY_EXTRAS) -p "$(__HOST_TESTS_BUILD_DIR)"
else
	@echo "HOST_LINT_LIBS is empty, skipping host-lint"
endif

host-fullcheck: host-test host-lint


# ---- ESP ----
.PHONY: esp-menuconfig esp-build esp-sanitize-db esp-clean esp-flash esp-monitor esp-flashm esp-lint

__BUILD_DIR := build
__TIDY_DB_DIR := $(__BUILD_DIR)/tidy
PORT_ESP ?= /dev/tty.usbmodem1101

esp-menuconfig:
	idf.py menuconfig

esp-build:
	idf.py build

esp-sanitize-db: _check-jq esp-build
	@mkdir -p "$(__TIDY_DB_DIR)"
	@echo ">> sanitize $(__BUILD_DIR)/compile_commands.json -> $(__TIDY_DB_DIR)/compile_commands.json"
	@./sanitize_compile_db.py "$(__BUILD_DIR)/compile_commands.json" "$(__TIDY_DB_DIR)/compile_commands.json"

esp-clean:
	idf.py fullclean
	rm -rf $(__BUILD_DIR) .cache managed_components dependencies.lock

esp-flash: esp-build
	idf.py -p $(PORT_ESP) flash

esp-monitor: esp-build
	idf.py -p $(PORT_ESP) monitor

esp-flashm: esp-build
	idf.py -p $(PORT_ESP) flash monitor

esp-lint: esp-sanitize-db
	find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
    	-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
		| xargs -0 ${CLANG_TIDY} -p ${__TIDY_DB_DIR}


# ---- All in one ----
.PHONY: lint test fullcheck clean

lint: esp-lint host-lint check-format
test: host-test
fullcheck: lint test
clean: host-clean esp-clean
