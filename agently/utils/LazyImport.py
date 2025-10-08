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

from importlib.metadata import version as get_installed_version, PackageNotFoundError
from packaging.version import parse as parse_version
from packaging.specifiers import SpecifierSet

from .DataFormatter import DataFormatter


class LazyImport:
    @staticmethod
    def from_import(
        from_package: str,
        target_modules: str | list[str],
        *,
        auto_install: bool = True,
        version_constraint: str | None = None,
        install_name: str | None = None,
        _attempted_install: bool = False,
    ):
        # Ensure version constraint has a valid operator
        if version_constraint and not any(
            version_constraint.startswith(op) for op in ("==", ">=", "<=", "!=", ">", "<")
        ):
            version_constraint = f"=={version_constraint}"

        if not isinstance(target_modules, list):
            target_modules = [target_modules]

        loaded_modules = []
        module_name = ""

        try:
            for module_name in target_modules:
                try:
                    module_name = DataFormatter.to_str(module_name)
                    loaded_modules.append(importlib.import_module(f"{from_package}.{module_name}"))
                except ModuleNotFoundError:
                    base_module = importlib.import_module(from_package)
                    try:
                        module_attr = getattr(base_module, module_name)
                        loaded_modules.append(module_attr)
                    except AttributeError:
                        raise ModuleNotFoundError(
                            f"Required module not found: {module_name}\n"
                            f"Found package '{from_package}' but no module or attribute named '{module_name}' in it."
                        )
            if version_constraint:
                try:
                    installed_version = get_installed_version(install_name or from_package)
                    spec = SpecifierSet(version_constraint)
                    if parse_version(installed_version) not in spec:
                        print(
                            f"⚠️ Version mismatch for {install_name or from_package}: "
                            f"installed {installed_version}, expected {version_constraint}"
                        )
                        if auto_install and not _attempted_install:
                            confirm = (
                                input(f"Do you want to install the required version {version_constraint} now? [y/N]: ")
                                .strip()
                                .lower()
                            )
                            if confirm == "y":
                                subprocess.check_call(
                                    [
                                        sys.executable,
                                        "-m",
                                        "pip",
                                        "install",
                                        f"{install_name or from_package}{version_constraint}",
                                    ]
                                )
                                return LazyImport.from_import(
                                    from_package,
                                    target_modules,
                                    auto_install=auto_install,
                                    version_constraint=version_constraint,
                                    install_name=install_name,
                                    _attempted_install=True,  # Recursive call
                                )
                except PackageNotFoundError:
                    pass
            return (tuple(loaded_modules) if len(loaded_modules) > 1 else loaded_modules[0]) if loaded_modules else None
        except ModuleNotFoundError:
            raise
        except ImportError:
            if auto_install and not _attempted_install:
                print(f"❗️ Missing modules: {install_name or from_package}")
                confirm = input("Do you want to install it via pip now? [y/N]: ").strip().lower()
                if confirm == "y":
                    subprocess.check_call([sys.executable, "-m", "pip", "install", install_name or from_package])
                    # Recursive call with `_attempted_install` set to True
                    return LazyImport.from_import(
                        from_package,
                        target_modules,
                        auto_install=auto_install,
                        version_constraint=version_constraint,
                        install_name=install_name,
                        _attempted_install=True,
                    )
            raise ImportError(
                f"Required module not found: {module_name}\n"
                f"Please install module manually using command: 'pip install {install_name or from_package}'"
            )

    @staticmethod
    def import_package(
        package_name: str,
        *,
        auto_install: bool = True,
        version_constraint: str | None = None,
        install_name: str | None = None,
        _attempted_install: bool = False,
    ):
        # Ensure version constraint has a valid operator
        if version_constraint and not any(
            version_constraint.startswith(op) for op in ("==", ">=", "<=", "!=", ">", "<")
        ):
            version_constraint = f"=={version_constraint}"

        try:
            # Attempt to import the package
            module = importlib.import_module(package_name)
            if version_constraint:
                try:
                    root_package_name = install_name or package_name.split(".")[0]
                    installed_version = get_installed_version(root_package_name)
                    spec = SpecifierSet(version_constraint)
                    if parse_version(installed_version) not in spec:
                        print(
                            f"⚠️ Version mismatch for {root_package_name}: installed {installed_version}, expected {version_constraint}"
                        )
                        if auto_install and not _attempted_install:
                            confirm = (
                                input(f"Do you want to install the required version {version_constraint} now? [y/N]: ")
                                .strip()
                                .lower()
                            )
                            if confirm == "y":
                                subprocess.check_call(
                                    [
                                        sys.executable,
                                        "-m",
                                        "pip",
                                        "install",
                                        f"{root_package_name}{version_constraint}",
                                    ]
                                )
                                return LazyImport.import_package(
                                    package_name,
                                    auto_install=auto_install,
                                    version_constraint=version_constraint,
                                    install_name=install_name,
                                    _attempted_install=True,
                                )
                except PackageNotFoundError:
                    pass
            return module
        except ImportError:
            root_package_name = install_name or package_name.split(".")[0]
            if auto_install and not _attempted_install:
                print(f"❗️ Missing modules: {root_package_name}")
                confirm = ""
                while confirm not in ("y", "n"):
                    confirm = input("Do you want to install it via pip now? [y/N]: ").strip().lower()
                if confirm == "y":
                    subprocess.check_call([sys.executable, "-m", "pip", "install", root_package_name])
                    return LazyImport.import_package(
                        package_name,
                        auto_install=auto_install,
                        install_name=install_name,
                        _attempted_install=True,
                    )
            raise ImportError(
                f"Required module not found: {package_name}\n"
                f"Please install module manually using command: 'pip install {root_package_name}'"
            )
