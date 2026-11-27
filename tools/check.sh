#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
find tv tools -name '*.sh' -exec sh -c 'for script do sh -n "$script" || exit; done' sh {} +
find tv tools -name '*.sh' -exec shellcheck {} +
find tv tools -name '*.sh' -exec shfmt -d {} +
node --check app/home.js
node --check app/backgrounds.js
node --check tv/home/home-keyfilter.js
node tests/home.test.cjs
python3 lg-debloat.py --help >/dev/null
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/privacy-check.py
