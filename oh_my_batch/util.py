from typing import List, Iterable
import glob
import os


def expand_globs(patterns: Iterable[str], raise_invalid=False) -> List[str]:
    """
    Expand glob patterns in paths

    :param patterns: list of paths or glob patterns
    :param raise_invalid: if True, will raise error if no file found for a glob pattern
    :return: list of expanded paths
    """
    paths = []
    for pattern in patterns:
        result = glob.glob(pattern, recursive=True) if '*' in pattern else [pattern]
        if raise_invalid and len(result) == 0:
            raise FileNotFoundError(f'No file found for {pattern}')
        for p in result:
            if p not in paths:
                paths.append(p)
            else:
                print(f'path {p} already exists in the list')
    return paths


def split_list(l, n):
    """
    Splits a list into n sub-lists.

    :param l: The list to be split.
    :param n: The number of sub-lists to create.
    :return: A list of sub-lists.
    """
    if n <= 0:
        raise ValueError("Number of sub-lists must be a positive integer")

    # Calculate the size of each sublist
    k, m = divmod(len(l), n)

    for i in range(n):
        start = i * k + min(i, m)
        end = (i + 1) * k + min(i + 1, m)
        if start == end:
            break
        yield l[start:end]


def ensure_dir(path: str):
    """
    Ensure the directory exists

    :param path: Path to directory or file.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
