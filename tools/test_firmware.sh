#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
json_dir=firmware/.pio/libdeps/bringup/ArduinoJson/src
if [[ ! -f "$json_dir/ArduinoJson.h" ]]; then
  json_dir=firmware/.pio/libdeps/esp32dev/ArduinoJson/src
fi
if [[ ! -f "$json_dir/ArduinoJson.h" ]]; then
  echo 'Build a firmware environment once to install pinned ArduinoJson 7.3.1.' >&2
  exit 1
fi
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
g++ -std=c++17 -Wall -Wextra -Werror -Ifirmware/include firmware/test/native/test_controller.cpp -o "$test_dir/controller"
"$test_dir/controller"
g++ -std=c++17 -Wall -Wextra -Werror -Ifirmware/include -I"$json_dir" firmware/test/native/test_runtime.cpp -o "$test_dir/runtime"
"$test_dir/runtime"
g++ -std=c++17 -Wall -Wextra -Werror -Ifirmware/include firmware/test/native/test_profile.cpp -o "$test_dir/profile"
"$test_dir/profile"
g++ -std=c++17 -Wall -Wextra -Werror -DSG_DAY3_BUILD=1 -Ifirmware/include firmware/test/native/test_profile.cpp -o "$test_dir/day3"
"$test_dir/day3"
echo 'profiles: runtime and day3 pump-lock assertions passed'
