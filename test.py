from FeasibilityCheck import import_tasks, import_solution, validate_solution, FeasibilityException
import pytest

HEADER_TASKS = "Order,Description,Quantity,Length,Width,Height,TurningAllowed,StackingAllowed,Group"
HEADER_SOLUTIONS = "Order,xPos,yPos,zPos,HTurned"


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


def test0_basic():
    tasks = import_tasks_default(["1,EuroPallet1,4,10,20,30,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "1,10,0,0,0", "1,10,20,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 4


def test1_count():
    with pytest.raises(FeasibilityException, match=r'.* Anzahl .*'):
        tasks = import_tasks_default(["1,EuroPallet1,4,10,20,30,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "1,10,0,0,0"], tasks)
        validate_solution_default(solution, tasks)


def test2_turning_not_allowed():
    with pytest.raises(FeasibilityException, match=r'.* unzulässigerweise gedreht.'):
        tasks = import_tasks_default(["2,EuroPallet2,1,20,40,40,0,0,1"])
        solution = import_solution_default(["2,0,0,0,1"], tasks)
        validate_solution_default(solution, tasks)


def test3_overlap_overlaps_same_origin_z():
    with pytest.raises(FeasibilityException, match=r'.* überschneiden .*'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution_overlaps_same_origin_z = import_solution_default(["1,0,0,0,0", "1,5,5,0,0"], tasks)
        validate_solution_default(solution_overlaps_same_origin_z, tasks)


def test4_overlap_contains():
    with pytest.raises(FeasibilityException, match=r'.* überschneiden .'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution_contains = import_solution_default(["1,0,0,0,0", "1,0,0,0,0"], tasks)
        validate_solution_default(solution_contains, tasks)


def test5_check_extend_container_dimensions():
    with pytest.raises(FeasibilityException, match=r'.* überschreitet die Container Dimensionen.'):
        tasks = import_tasks_default(["1,EuroPallet2,1,20,40,40,0,0,1"])
        solution = import_solution_default(["1,0,0,1,0"], tasks)  # extend height of container
        validate_solution(solution, tasks, 40, 40, 0)


def test6_check_touch_container():
    tasks = import_tasks_default(["1,EuroPallet2,1,20,40,40,0,0,1"])
    solution = import_solution_default(["1,0,0,0,0"], tasks)
    validate_solution(solution, tasks, 40, 40, 0)
    assert len(solution) == 1


def test7_stack_right():
    tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,0,0,10,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 2


def test8_stack_not_allowed1():
    with pytest.raises(FeasibilityException, match=r'.* unzulässigerweise gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,1,10,10,10,1,1,1", "2,EuroPallet2,1,10,10,10,1,0,1"])
        solution = import_solution_default(["1,0,0,0,0", "2,0,0,10,0"], tasks)
        validate_solution_default(solution, tasks)


def test9_stack_not_allowed2():
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,1,10,10,10,1,0,1", "2,EuroPallet2,1,10,10,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "2,0,0,10,0"], tasks)
        validate_solution_default(solution, tasks)


def test10_stack_hover():
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,0,15,0"], tasks)
        validate_solution_default(solution, tasks)


def test11_overhang():
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,1,0,10,0"], tasks)
        validate_solution_default(solution, tasks)


def test12_multiple_stack():  # 1. Layer: 2 Pallets Type 1 / 2. Layer: 1 Pallet Type 2 / 3. Layer: 2 Palleten Type 3
    tasks = import_tasks_default(["1,EuroPallet1,2,10,20,10,1,1,2", "2,EuroPallet2,1,20,10,10,1,1,1",
                                  "3,EuroPallet2,2,5,5,10,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "1,10,0,0,0", "2,0,0,10,0", "3,15,0,20,0", "3,15,5,20,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 5


def test13_wrong_multiple_stack():  # Gap under Type 2 / between both Type 1
    with pytest.raises(FeasibilityException, match=r'.* falsch gestapelt.'):
        tasks = import_tasks_default(["1,EuroPallet1,2,10,10,10,1,1,1", "2,EuroPallet2,1,10,30,10,1,1,1"])
        solution = import_solution_default(["1,0,0,0,0", "1,0,20,0,0", "2,0,0,10,0"], tasks)
        validate_solution_default(solution, tasks)


def test14_wrong_lifo_one_layer():  # Pallet Order 2 in front of Order 1
    with pytest.raises(FeasibilityException, match=r'.* verdeckt.'):
        tasks = import_tasks_default(["1,EuroPallet1,1,10,15,10,1,1,1", "2,EuroPallet2,1,10,15,10,1,1,2"])
        solution = import_solution_default(["1,0,0,0,0", "2,10,0,0,0,0"], tasks)
        validate_solution_default(solution, tasks)


def test15_right_lifo_one_layer1():  # 3 pallets, First large pallet order 2, Second two small pallets order 1/2
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,2",
                                  "2,EuroPallet2,1,10,15,10,1,1,2", "3,EuroPallet2,1,10,15,10,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "2,10,0,0,0", "3,10,15,0,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 3


def test16_right_lifo_one_layer2():  # 2 pallets, different order, different length
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,1",
                                  "2,EuroPallet2,1,20,15,10,1,1,2"])
    solution = import_solution_default(["1,0,0,0,0", "2,0,30,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 2


def test17_right_lifo_two_layers():  # first layer Order 2, second layer Order 1
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,1",
                                  "2,EuroPallet2,1,20,50,10,1,1,2"])
    solution = import_solution_default(["1,10,0,10,0", "2,0,0,0,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 2


def test18_right_lifo_multiple_pallets():  # first layer: Pallet type 1, type 2, type 1 / second layer: pallet type 3
    tasks = import_tasks_default(["1,EuroPallet1,2,10,5,10,1,1,1",
                                  "2,EuroPallet2,1,10,5,10,1,1,2",
                                  "3,EuroPallet3,1,5,5,5,1,1,2"])
    solution = import_solution_default(["1,0,0,0,0", "2,0,5,0,0", "1,0,10,0,0", "3,5,5,10,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 4


def test19_right_lifo_multiple_pallets2():  #
    tasks = import_tasks_default(["1,EuroPallet1,1,5,15,40,1,1,1",
                                  "2,EuroPallet2,1,20,15,10,1,1,2",
                                  "3,EuroPallet3,1,10,5,5,1,1,1",
                                  "4,EuroPallet4,1,10,5,5,1,1,2",
                                  "5,EuroPallet5,1,5,5,5,1,1,1"])
    solution = import_solution_default(["1,0,0,0,0", "2,0,15,0,0", "3,10,25,10,0",
                                        "4,10,15,10,0", "5,15,15,15,0"], tasks)
    validate_solution_default(solution, tasks)
    assert len(solution) == 5


def test20_wrong_lifo_two_layers():  # first layer Order 1, second layer Order 2
    with pytest.raises(FeasibilityException, match=r'.* LIFO .'):
        tasks = import_tasks_default(["1,EuroPallet1,1,20,10,10,1,1,2",
                                      "2,EuroPallet2,1,20,10,10,1,1,1"])
        solution = import_solution_default(["1,0,0,10,0", "2,0,0,0,0"], tasks)
        validate_solution_default(solution, tasks)


def test21_wrong_lifo_two_layers2():  # first layer Order 2, second layer Order 1 (not in front)
    with pytest.raises(FeasibilityException, match=r'.* LIFO .'):
        tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,1",
                                      "2,EuroPallet2,1,20,50,10,1,1,2"])
        solution = import_solution_default(["1,0,0,10,0", "2,0,0,0,0"], tasks)
        validate_solution_default(solution, tasks)


def test22_right_lifo_two_layers2():
    tasks = import_tasks_default(["1,EuroPallet1,1,10,30,10,1,1,1",
                                  "2,EuroPallet2,1,20,50,10,1,1,2"])
    solution = import_solution_default(["1,0,0,10,0", "2,0,0,0,0"], tasks)
    validate_solution(solution, tasks, 100, 100, 10)
    assert len(solution) == 2
