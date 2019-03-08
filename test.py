from FeasibilityCheck import import_tasks,import_solution, validate_solution, FeasibilityException
import pytest

HEADER_TASKS = "Id,Description,Quantity,Length,Width,Height,TurningAllowed,StackingAllowed,Order"
HEADER_SOLUTIONS = "TypId,xPos,yPos,zPos,HTurned"


def import_tasks_default(tasks):
    tasks_list = [HEADER_TASKS]
    tasks_list.extend(tasks)
    return import_tasks(tasks_list)


def import_solution_default(solution, tasks):
    solution_list = [HEADER_SOLUTIONS]
    solution_list.extend(solution)
    return import_solution(solution_list, tasks)


def test_basic():
    tasks = import_tasks_default(["1,EuroPallet1,4,10,20,30,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "1,10,0,0,0", "1,10,20,0,0"], tasks)
    validate_solution(solution, tasks)
    assert len(solution) == 4


def test_count():
    with pytest.raises(FeasibilityException, match=r'.* Anzahl .*'):
        tasks = import_tasks_default(["1,EuroPallet1,4,10,20,30,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "1,10,0,0,0"], tasks)
        validate_solution(solution, tasks)


def test_turning_not_allowed():
    with pytest.raises(FeasibilityException, match=r'.* unzulässigerweise gedreht.'):
        tasks = import_tasks_default(["2,EuroPallet2,1,20,40,40,0,0,1"])
        solution = import_solution_default(["2,0,0,0,1"], tasks)
        validate_solution(solution, tasks)


def test_overlap_overlaps_same_origin_z():
    with pytest.raises(FeasibilityException, match=r'.* überschneiden .*'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution_overlaps_same_origin_z = import_solution_default(["1,0,0,0,0", "1,5,5,0,0"], tasks)
        validate_solution(solution_overlaps_same_origin_z, tasks)


def test_overlap_contains():
    with pytest.raises(FeasibilityException, match=r'.* überschneiden .'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution_contains = import_solution_default(["1,0,0,0,0", "1,0,0,0,0"], tasks)
        validate_solution(solution_contains, tasks)


def test_pallets():
    tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
    same_pallets = import_solution_default(["1,0,0,0,0", "1,0,0,0,0"], tasks)
    assert same_pallets[0] != same_pallets[1]


def test_stack_right():
    tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
    solution_contains = import_solution_default(["1,0,0,0,0", "1,0,0,10,0"], tasks)
    validate_solution(solution_contains, tasks)
    assert len(solution_contains) == 2


def test_stack_wrong():
    tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
    solution_contains = import_solution_default(["1,0,0,0,0", "1,0,0,15,0"], tasks)
    validate_solution(solution_contains, tasks)
    assert len(solution_contains) == 2
