from typing import Dict, List

def combine_dict(A: Dict[str, float], B: Dict[str, float]) -> Dict[str, float]:
    from collections import Counter
    return dict(Counter(A) + Counter(B))

def combine_dict_list(A: Dict[str, List[int]], B: Dict[str, List[int]]) -> Dict[str, List[int]]:
    return {k: A.get(k, []) + B.get(k, []) for k in set(A) | set(B)}

def scale_dict(input_dict: Dict[str, float], scaling_factor: float) -> Dict[str, float]:
    return {key: value * scaling_factor for key, value in input_dict.items()}

def sum_dict(input_dict: Dict[str, float]) -> float:
    return sum(input_dict.values())


def percent_difference(new: float, orig: float) -> float: 
    if orig == 0.0:
        return 0
    return (new - orig) / orig
