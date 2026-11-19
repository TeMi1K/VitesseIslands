#!/usr/bin/env bash
# Builds dist/vitesse-islands-<version>.jar
# Requires: bash, curl, python3 (3.9+), zip
set -euo pipefail
cd "$(dirname "$0")"

IC_SHA=86ff40eb316568259dca7fc141c2aeb334ef8524        # JetBrains/intellij-community
RTP_SHA=b4209211062d1700292cb015f4bc29c2e5aa930b       # JetBrains/rider-theme-pack

ISLANDS_URL="https://raw.githubusercontent.com/JetBrains/intellij-community/${IC_SHA}/platform/platform-resources/src/themes/islands/ManyIslandsDark.theme.json"
SCHEME_URL="https://raw.githubusercontent.com/JetBrains/rider-theme-pack/${RTP_SHA}/src/main/resources/colorSchemes/RiderIslandsDark.xml"

VERSION=$(python3 -c "import xml.etree.ElementTree as E; print(E.parse('src/main/resources/META-INF/plugin.xml').getroot().findtext('version'))")

mkdir -p upstream
[ -f upstream/ManyIslandsDark.theme.json ] || curl -fsSL "$ISLANDS_URL" -o upstream/ManyIslandsDark.theme.json
[ -f upstream/RiderIslandsDark.xml ]       || curl -fsSL "$SCHEME_URL"  -o upstream/RiderIslandsDark.xml

rm -rf build && mkdir -p build
python3 scripts/build.py upstream/ManyIslandsDark.theme.json upstream/RiderIslandsDark.xml build

STAGE=build/jar
mkdir -p "$STAGE/META-INF/licenses"
cp src/main/resources/META-INF/plugin.xml src/main/resources/META-INF/pluginIcon.svg "$STAGE/META-INF/"
cp LICENSE NOTICE "$STAGE/META-INF/"
cp licenses/* "$STAGE/META-INF/licenses/"
cp -r build/src/main/resources/themes build/src/main/resources/colorSchemes "$STAGE/"

mkdir -p dist
rm -f "dist/vitesse-islands-${VERSION}.jar"
(cd "$STAGE" && zip -r -X -q "../../dist/vitesse-islands-${VERSION}.jar" META-INF themes colorSchemes)

# standalone schemes for people who only want editor colors
cp build/src/main/resources/colorSchemes/VitesseDarkIslands.xml dist/VitesseDarkIslands.icls
cp build/src/main/resources/colorSchemes/VitesseSoftIslands.xml dist/VitesseSoftIslands.icls

echo "Built dist/vitesse-islands-${VERSION}.jar"
