import ast
import copy
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import Dict, Set, Tuple, Optional, Iterable, Union

from graphlib import TopologicalSorter
from stdlib_list import stdlib_list


class ItemKind(str, Enum):
    IN_PROJECT = 'in project'
    THIRD_PARTY = 'third party'


def remove_suffix(target: str, suffix: str) -> str:
    if target.endswith(suffix):
        return target[:-len(suffix)]
    return target


def join(*args, sep='.'):
    return sep.join(filter(bool, args))


def remove_type_checking(text: str):
    if 'TYPE_CHECKING' not in text:
        return text

    def inner():
        it = chain(text.split('\n'), [None])
        while (line := next(it)) is not None:
            if line == 'if TYPE_CHECKING:':
                while (line := next(it)) is not None:
                    if line and line[0] != ' ':
                        yield line
                        break
            else:
                yield line

    return '\n'.join(inner())


class PySearchDeps:
    def __init__(self, home: Path):
        self.home = home.resolve()

    def analyze_module_name(self, dotted_name: str) -> Optional[Tuple[ItemKind, Union[Path, str]]]:
        first = dotted_name.split('.')[0]

        if first in stdlib_list():
            return  # import typing

        if first not in [d.name for d in self.home.iterdir()]:
            return ItemKind.THIRD_PARTY, first  # import django

        current = copy.copy(self.home)
        for module in dotted_name.split('.'):
            if current.is_dir() and module not in [remove_suffix(d.name, '.py') for d in current.iterdir()]:
                break  # from home.module import MyClass

            if (current / module).exists():
                current /= module
            elif (current / (module + '.py')).exists():
                current /= module + '.py'
            else:
                break  # import home.package
        # else: import home.module

        current = (current / '__init__.py' if current.is_dir() else current).resolve()
        return ItemKind.IN_PROJECT, current

    def analyze_file(self, file: Path) -> Iterable[Tuple[ItemKind, str]]:
        module: ast.Module = ast.parse(remove_type_checking(file.read_text()))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if target := self.analyze_module_name(alias.name):
                        yield target

            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                for alias in node.names:
                    if target := self.analyze_module_name(node.module + '.' + alias.name):
                        yield target

            elif isinstance(node, ast.ImportFrom) and node.level > 0:
                current = copy.copy(file.parent)
                for _ in range(1, node.level):
                    current /= '..'
                current = str(current.resolve())
                for alias in node.names:
                    package = str(current)[len(str(self.home)) + 1:].replace('/', '.')
                    if target := self.analyze_module_name(join(package, node.module, alias.name)):
                        yield target

    def get_uses(
            self,
            *dirs: Tuple[Path, ...],
            target: Tuple[ItemKind, ...] = (ItemKind.THIRD_PARTY,),
    ) -> Dict[Path, Set[str]]:
        data = {}
        for directory in dirs:
            for file in directory.rglob('**/*.py'):
                data[file.resolve()] = [*set(self.analyze_file(file))]

        uses = {
            file: {dep[1] for dep in deps if dep[0] in target}
            for file, deps in data.items()
        }
        ts = TopologicalSorter({
            file: {dep[1] for dep in deps if dep[0] == ItemKind.IN_PROJECT}
            for file, deps in data.items()
        })
        for file_name in ts.static_order():
            for dep in data[file_name]:
                if dep[0] == ItemKind.IN_PROJECT:
                    uses[file_name] |= uses[dep[1]]

        return uses
