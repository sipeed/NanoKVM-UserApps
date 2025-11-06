import os
import toml
import re
from collections import OrderedDict


def get_path():
    from pathlib import Path

    OUTFILE_NAME = "apps.toml"
    curr_file = Path(__file__).resolve()
    curr_dir = curr_file.parent
    parent_dir = curr_dir.parent
    apps_dir = parent_dir / "apps"
    output_path = curr_dir / OUTFILE_NAME

    return (apps_dir, output_path)


(ROOT_DIR, OUTPUT_FILE) = get_path()

DEFAULT_APP = {
    "application_name": "",
    "application_version": "1.0.0",
    "application_descriptions": "No description provided",
    "author_name": "Unknown",
    "interaction_requires_user_input": False,
}

SEMVER_REGEX = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

apps_list = []

for folder_name in os.listdir(ROOT_DIR):
    folder_path = os.path.join(ROOT_DIR, folder_name)
    if not os.path.isdir(folder_path):
        continue

    app_info = OrderedDict()
    app_info["folder"] = folder_name
    app_info.update(DEFAULT_APP)
    app_info["application_name"] = folder_name

    files = []
    for root, _, filenames in os.walk(folder_path):
        for f in filenames:
            abs_path = os.path.join(root, f)
            rel_path = os.path.relpath(abs_path, ROOT_DIR)
            files.append(rel_path.replace("\\", "/"))

    app_info["files"] = files

    app_toml_path = os.path.join(folder_path, "app.toml")
    if os.path.isfile(app_toml_path):
        try:
            data = toml.load(app_toml_path)

            if "application" in data:
                app_info["application_name"] = data["application"].get(
                    "name", folder_name
                )
                version = data["application"].get("version", "1.0.0")

                if not SEMVER_REGEX.match(version):
                    print(
                        f"Warning: {folder_name} version '{version}' is not SemVer, skipped."
                    )
                    continue

                app_info["application_version"] = version
                app_info["application_descriptions"] = data["application"].get(
                    "descriptions", "No description provided"
                )

            if "author" in data:
                app_info["author_name"] = data["author"].get("name", "Unknown")

            if "interaction" in data:
                app_info["interaction_requires_user_input"] = data["interaction"].get(
                    "requires_user_input", False
                )

        except Exception as e:
            print(f"Warning: Failed to parse {app_toml_path}: {e}")

    apps_list.append(app_info)

output_data = OrderedDict()
output_data["apps"] = apps_list

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    toml.dump(output_data, f)

print(f"Generated {OUTPUT_FILE} with {len(apps_list)} apps.")
