# Copyright 2023-2025 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import importlib
import subprocess


from .DataFormatter import DataFormatter


class LazyImport:
    @staticmethod
    def from_import(
        from_package: str,
        target_modules: str | list[str],
        *,
        auto_install: bool = True,
    ):
        if not isinstance(target_modules, list):
            target_modules = [target_modules]

        loaded_modules = []
        module_name = ""

        try:
            for module_name in target_modules:
                try:
                    module_name = DataFormatter.to_str(module_name)
                    loaded_modules.append(importlib.import_module(f"{ from_package }.{ module_name }"))
                except ModuleNotFoundError:
                    base_module = importlib.import_module(from_package)
                    try:
                        module_attr = getattr(base_module, module_name)
                        loaded_modules.append(module_attr)
                    except AttributeError:
                        raise ModuleNotFoundError(
                            f"Required module not found: { module_name }\n"
                            f"Found package '{ from_package } but found no module or attribute named '{ module_name }' from it."
                        )
            return (tuple(loaded_modules) if len(loaded_modules) > 1 else loaded_modules[0]) if loaded_modules else None
        except ModuleNotFoundError:
            raise
        except ImportError:
            if auto_install:
                print(f"❗️ Missing modules: { from_package }")
                confirm = ""
                while confirm not in ("y", "n"):
                    confirm = input("Do you want to install it via pip now? [y/N]: ").strip().lower()
                if confirm == "y":
                    subprocess.check_call([sys.executable, "-m", "pip", "install", from_package])
                    return LazyImport.from_import(
                        from_package,
                        target_modules,
                        auto_install=auto_install,
                    )
            raise ImportError(
                f"Required module not found: { module_name }\n"
                f"Please install module manually using command for example: 'pip install { from_package }'"
            )

    @staticmethod
    def import_package(package_name: str, *, auto_install: bool = True):
        try:
            return importlib.import_module(package_name)
        except ImportError:
            root_package_name = package_name.split(".")[0]
            if auto_install:
                print(f"❗️ Missing modules: { root_package_name }")
                confirm = ""
                while confirm not in ("y", "n"):
                    confirm = input("Do you want to install it via pip now? [y/N]: ").strip().lower()
                if confirm == "y":
                    subprocess.check_call([sys.executable, "-m", "pip", "install", root_package_name])
                    return LazyImport.import_package(
                        package_name,
                        auto_install=auto_install,
                    )
            raise ImportError(
                f"Required module not found: { root_package_name }\n"
                f"Please install module manually using command for example: 'pip install { root_package_name }'"
            )
