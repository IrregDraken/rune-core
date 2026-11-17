from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
AGENT = ROOT / "android_agent"
ANDROID_NS = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID_NS)

def android_attr(name: str) -> str:
    return f"{{{ANDROID_NS}}}{name}"

def install() -> None:
    if not ANDROID.exists():
        raise SystemExit("Android platform project missing. Run flutter create --org com.draken --project-name rune_mobile --platforms=android,ios . first.")

    source = AGENT / "src/main/kotlin/com/draken/rune_mobile"
    target = ANDROID / "app/src/main/kotlin/com/draken/rune_mobile"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("MainActivity.kt", "RuneAccessibilityService.kt", "RuneOperatorService.kt"):
        shutil.copy2(source / name, target / name)

    xml_source = AGENT / "src/main/res/xml/rune_accessibility_service.xml"
    xml_target = ANDROID / "app/src/main/res/xml/rune_accessibility_service.xml"
    xml_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(xml_source, xml_target)

    manifest = ANDROID / "app/src/main/AndroidManifest.xml"
    tree = ET.parse(manifest)
    root = tree.getroot()
    application = root.find("application")
    if application is None:
        raise SystemExit("Generated Android manifest has no application element.")

    for permission in (
        "android.permission.FOREGROUND_SERVICE",
        "android.permission.FOREGROUND_SERVICE_DATA_SYNC",
        "android.permission.POST_NOTIFICATIONS",
    ):
        if not any(item.get(android_attr("name")) == permission for item in root.findall("uses-permission")):
            permission_node = ET.Element("uses-permission", {android_attr("name"): permission})
            root.insert(list(root).index(application), permission_node)

    queries = root.find("queries")
    if queries is None:
        queries = ET.Element("queries")
        root.insert(list(root).index(application), queries)
    if not any(q.find("intent") is not None for q in queries.findall("intent")):
        intent = ET.SubElement(queries, "intent")
        ET.SubElement(intent, "action", {android_attr("name"): "android.intent.action.MAIN"})
        ET.SubElement(intent, "category", {android_attr("name"): "android.intent.category.LAUNCHER"})

    existing = next((item for item in application.findall("service")
                     if item.get(android_attr("name")) == ".RuneAccessibilityService"), None)
    if existing is None:
        service = ET.SubElement(application, "service", {
            android_attr("name"): ".RuneAccessibilityService",
            android_attr("label"): "RUNE Device Operator",
            android_attr("permission"): "android.permission.BIND_ACCESSIBILITY_SERVICE",
            android_attr("exported"): "true",
        })
        intent_filter = ET.SubElement(service, "intent-filter")
        ET.SubElement(intent_filter, "action", {android_attr("name"): "android.accessibilityservice.AccessibilityService"})
        ET.SubElement(service, "meta-data", {
            android_attr("name"): "android.accessibilityservice",
            android_attr("resource"): "@xml/rune_accessibility_service",
        })

    operator = next((item for item in application.findall("service")
                     if item.get(android_attr("name")) == ".RuneOperatorService"), None)
    if operator is None:
        ET.SubElement(application, "service", {
            android_attr("name"): ".RuneOperatorService",
            android_attr("exported"): "false",
            android_attr("foregroundServiceType"): "dataSync",
        })

    strings = ANDROID / "app/src/main/res/values/strings.xml"
    if strings.exists():
        stree = ET.parse(strings)
        sroot = stree.getroot()
    else:
        sroot = ET.Element("resources")
        stree = ET.ElementTree(sroot)
    if sroot.find("string[@name='rune_accessibility_description']") is None:
        item = ET.SubElement(sroot, "string", {"name": "rune_accessibility_description"})
        item.text = "Allows RUNE to inspect and operate visible app interfaces when you explicitly enable this service."
    stree.write(strings, encoding="utf-8", xml_declaration=True)
    tree.write(manifest, encoding="utf-8", xml_declaration=True)

    # Gesture dispatch in AccessibilityService requires Android API 24+.
    gradle_kts = ANDROID / "app/build.gradle.kts"
    gradle_groovy = ANDROID / "app/build.gradle"
    if gradle_kts.exists():
        gradle = gradle_kts.read_text(encoding="utf-8")
        gradle = gradle.replace("minSdk = flutter.minSdkVersion", "minSdk = 24")
        gradle_kts.write_text(gradle, encoding="utf-8")
    elif gradle_groovy.exists():
        gradle = gradle_groovy.read_text(encoding="utf-8")
        gradle = gradle.replace("minSdkVersion flutter.minSdkVersion", "minSdkVersion 24")
        gradle_groovy.write_text(gradle, encoding="utf-8")

if __name__ == "__main__":
    install()
