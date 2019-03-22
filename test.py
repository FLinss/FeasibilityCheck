from FeasibilityCheck import import_tasks, import_solution, validate_solution, FeasibilityException
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


def validate_solution_default(solution, tasks):
    validate_solution(solution, tasks, 100, 100)


def test_basic():
    tasks = import_tasks_default(["1,EuroPallet1,4,10,20,30,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "1,10,0,0,0", "1,10,20,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 4


def test_count():
    with pytest.raises(FeasibilityException, match=r'.* Anzahl .*'):
        tasks = import_tasks_default(["1,EuroPallet1,4,10,20,30,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "1,10,0,0,0"], tasks)
        validate_solution_default(solution, tasks)


def test_turning_not_allowed():
    with pytest.raises(FeasibilityException, match=r'.* unzulässigerweise gedreht.'):
        tasks = import_tasks_default(["2,EuroPallet2,1,20,40,40,0,0,1"])
        solution = import_solution_default(["2,0,0,0,1"], tasks)
        validate_solution_default(solution, tasks)


def test_overlap_overlaps_same_origin_z():
    with pytest.raises(FeasibilityException, match=r'.* überschneiden .*'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution_overlaps_same_origin_z = import_solution_default(["1,0,0,0,0", "1,5,5,0,0"], tasks)
        validate_solution_default(solution_overlaps_same_origin_z, tasks)


def test_overlap_contains():
    with pytest.raises(FeasibilityException, match=r'.* überschneiden .'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution_contains = import_solution_default(["1,0,0,0,0", "1,0,0,0,0"], tasks)
        validate_solution_default(solution_contains, tasks)


def test_check_extend_container_dimensions():
    with pytest.raises(FeasibilityException, match=r'.* überschreitet die Container Dimensionen.'):
        tasks = import_tasks_default(["1,EuroPallet2,1,20,40,40,0,0,1"])
        solution = import_solution_default(["1,0,0,1,0"], tasks)  # extend height of container
        validate_solution(solution, tasks, 40, 40)


def test_check_touch_container():
    tasks = import_tasks_default(["1,EuroPallet2,1,20,40,40,0,0,1"])
    solution = import_solution_default(["1,0,0,0,0"], tasks)
    validate_solution(solution, tasks, 40, 40)
    assert len(solution) == 1


def test_stack_right():
    tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,0,0,10,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 2


def test_stack_not_allowed():
    with pytest.raises(FeasibilityException, match=r'.* unzulässigerweise gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,0,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,0,15,0"], tasks)
        validate_solution_default(solution, tasks)


def test_stack_hover():
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,0,15,0"], tasks)
        validate_solution_default(solution, tasks)


def test_overhang():
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,1,0,10,0"], tasks)
        validate_solution_default(solution, tasks)


def test_multiple_stack():  # 1. Layer: 2 Pallets Type 1 / 2. Layer: 1 Pallet Type 2 / 3. Layer: 1 Pallet Type 2
    tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1", "2,EuroPallet2,2,10,20,10,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,0,10,0,0", "2,0,0,10,0", "2,0,0,20,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 4


def test_wrong_multiple_stack():  # Gap under Type 2 / between both Type 1
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1", "2,EuroPallet2,1,10,30,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "2,0,0,10,0"], tasks)
        validate_solution_default(solution, tasks)


def test_wrong_lifo_one_layer():
    with pytest.raises(FeasibilityException, match=r'.* verdeckt.'):
        tasks = import_tasks_default(["1,EuroPallet1,1,10,15,10,1,1,1", "2,EuroPallet2,1,10,15,10,1,1,2"])
        solution = import_solution_default(["1,0,0,0,0", "2,10,0,0,0,0"], tasks)
        validate_solution_default(solution, tasks)


def test_right_lifo_one_layer1():  # 3 pallets, First large pallet order 2, Second two small pallets order 1/2
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,2",
                                  "2,EuroPallet2,1,10,15,10,1,1,2", "3,EuroPallet2,1,10,15,10,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "2,10,0,0,0", "3,10,15,0,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 3


def test_right_lifo_one_layer2():  # 2 pallets, different order, different length
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,1",
                                  "2,EuroPallet2,1,20,15,10,1,1,2"])
    solution = import_solution_default(["1,0,0,0,0", "2,0,30,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 2


def test_right_lifo_two_layers():
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,1",
                                  "2,EuroPallet2,1,20,50,10,1,1,2"])
    solution = import_solution_default(["1,10,0,10,0", "2,0,0,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 2

