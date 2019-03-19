import argparse
import csv
from shapely.geometry import Point, box


class FeasibilityException(Exception):
    pass


class AbstractPallet:
    def __init__(self, type_id, length, width, height):
        self.type_id = type_id
        self.length = length
        self.width = width
        self.height = height


class PalletType(AbstractPallet):
    def __init__(self, type_id, description, quantity, length, width, height, turning_allowed, stacking_allowed,
                 order):
        self.description = description
        self.quantity = quantity
        self.turning_allowed = turning_allowed
        self.stacking_allowed = stacking_allowed
        self.order = order
        super(PalletType, self).__init__(type_id, length, width, height)


class SolutionPallet(AbstractPallet):
    def __init__(self, pallet_type, x_pos, y_pos, z_pos, h_turned):
        length = pallet_type.length if not h_turned else pallet_type.width
        width = pallet_type.length if h_turned else pallet_type.width
        self.origin_point = Point(x_pos, y_pos, z_pos)
        self.base_area = box(x_pos, y_pos, x_pos + length, y_pos + width)
        super(SolutionPallet, self).__init__(pallet_type, length, width, pallet_type.height)

    def validate_rotation(self):
        if self.length == self.type_id.width and self.width == self.type_id.length:
            if self.type_id.turning_allowed:
                return True
            else:
                raise FeasibilityException(
                    "Die Palette im Startpunkt %s wurde unzulässigerweise gedreht." % self.origin_point.coords[:])
        return False

    def validate_length(self):
        return self.length == self.type_id.length

    def validate_width(self):
        return self.width == self.type_id.width

    def check_extend_width(self, width_value):
        return self.origin_point.z + self.width > width_value

    def validate_height(self,):
        return self.height == self.type_id.height

    def check_extend_height(self, height_value):
        return self.origin_point.z + self.height > height_value

    def validate_dimension(self):
        if not self.validate_rotation():
            if not self.validate_length() or not self.validate_width():
                raise FeasibilityException(
                    "Die Palette im Startpunkt %s besitzt falsche Dimensionen." % self.origin_point.coords[:])
        if not self.validate_height():
            raise FeasibilityException(
                "Die Palette im Startpunkt %s besitzt falsche Dimensionen." % self.origin_point.coords[:])

    def check_overlaping_floor_area_with_other_pallet(self, other_pallet):
        if self != other_pallet and (self.base_area.overlaps(other_pallet.base_area) or
                                     self.base_area.contains(other_pallet.base_area)):
            return True
        return False

    def check_overlaping_heights(self, other_pallet):
        if self.check_extend_height(other_pallet.origin_point.z) and other_pallet.check_extend_height(
                self.origin_point.z):
            return True
        return False


def main():
    try:
        parser = argparse.ArgumentParser(description='Überprüfung der Zulässigkeit einer Lösung.')
        parser.add_argument('--aufgabe', '-a', type=str, required=True,
                            help='Aufgabedaten als csv-Datei')
        parser.add_argument('--loesung', '-l', type=str, required=True,
                            help='Lösungsdaten als csv-Datei')
        parser.add_argument('--breite', type=int, help='Breite des Containers', default=100)
        parser.add_argument('--hoehe', type=int, help='Höhe des Containers', default=100)
        args = parser.parse_args()
        tasks = import_tasks_by_file(args.aufgabe)
        solution_pallets = import_solution_by_file(args.loesung, tasks)
        validate_solution(solution_pallets, tasks, args.breite, args.hoehe)
        print("Die Lösung ist zulässig.")
    except FeasibilityException as e:
        print(e)


def import_tasks_by_file(file):
    with open(file, newline='') as csvfile:
        return import_tasks(csvfile)


def import_tasks(iterable):
    csvreader = csv.DictReader(iterable, delimiter=',', quotechar='|')
    result = dict()
    for row in csvreader:
        result[int(row["Id"])] = PalletType(int(row["Id"]), row["Description"], int(row["Quantity"]),
                                            int(row["Length"]), int(row["Width"]), int(row["Height"]),
                                            bool(int(row["TurningAllowed"])), bool(int(row["StackingAllowed"])),
                                            int(row["Order"]))
    return result


def import_solution_by_file(file, task_data):
    with open(file, newline='') as csvfile:
        return import_solution(csvfile, task_data)


# TODO: zweite Importfunktion mit TypId und zwei Punkten
def import_solution(iterable, task_data):
    csvreader = csv.DictReader(iterable, delimiter=',', quotechar='|')
    result = []
    for row in csvreader:
        new_solution_pallet_type = task_data[int(row["TypId"])]
        new_solution_pallet = SolutionPallet(new_solution_pallet_type, int(row["xPos"]), int(row["yPos"]),
                                             int(row["zPos"]), int(row["HTurned"]))
        result.append(new_solution_pallet)
    return result


def validate_solution(solution_pallets, tasks, height_value, width_value):
    check_count(solution_pallets, tasks)
    check_dimensions(solution_pallets)
    check_container_dimensions(solution_pallets, height_value, width_value)
    check_overlap(solution_pallets)
    check_lifo(solution_pallets)


def check_count(solution_pallets, tasks):
    for key in tasks:
        # TODO: item.type_id.type_id ungünstig
        used_pallets = len([i for i in filter(lambda item: item.type_id.type_id == tasks[key].type_id, solution_pallets)])
        if tasks[key].quantity != used_pallets:
            raise FeasibilityException(
                "Die Anzahl der Paletten von %s, Order %s beträgt %s. Es ist jedoch die Anzahl %s gefordert." % (
                    tasks[key].description, tasks[key].order, used_pallets, tasks[key].quantity))


def check_dimensions(solution_pallets):
    for pallet in solution_pallets:
        pallet.validate_dimension()


def check_container_dimensions(solution_pallets, width_value, height_value):
    for pallet in solution_pallets:
        if pallet.check_extend_width(width_value) or pallet.check_extend_height(height_value):
            raise FeasibilityException("Die Palette im Startpunkt %s überschreitet die Container Dimensionen."
                                       % pallet.origin_point.coords[:])


# TODO: Refactor: Eher Stacking Funktion und overlap wird nur bei Höhen aufgerufen.
def check_overlap(solution_pallets):
    for pallet in solution_pallets:
        for other_pallet in solution_pallets:
            if pallet.check_overlaping_floor_area_with_other_pallet(other_pallet):
                if pallet.check_overlaping_heights(other_pallet):
                    raise FeasibilityException("Die Paletten in Startpunkt %s und %s überschneiden sich." %
                                               (pallet.origin_point.coords[:], other_pallet.origin_point.coords[:]))
                # TODO: Überprüfung auf korrektes Stacking


def check_lifo(solution_pallets):
    pass


if __name__ == '__main__':
    main()