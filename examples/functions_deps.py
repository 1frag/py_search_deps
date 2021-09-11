import functools
import json
import operator
from pathlib import Path

from py_search_deps import PySearchDeps
from pydantic.json import pydantic_encoder, ENCODERS_BY_TYPE

layers = Path('layers/domain/python')
functions = Path('functions')
dirs = [layers, functions]
ENCODERS_BY_TYPE[dict] = dict


def get_stats():
    third_party_uses = PySearchDeps(layers).get_uses(*dirs)

    functions_uses = {k: v for k, v in third_party_uses.items() if k.name == 'index.py'}

    libs_in_all = functools.reduce(operator.and_, functions_uses.values())
    libs_in_any = functools.reduce(operator.or_, functions_uses.values())

    print('libs in all functions', libs_in_all)
    for function, uses in functions_uses.items():
        print(function, "don't use", libs_in_any - uses)

    functions_uses = {str(k): [*v] for k, v in functions_uses.items()}
    print(json.dumps(pydantic_encoder(functions_uses), default=str, indent=2))


if __name__ == '__main__':
    get_stats()
