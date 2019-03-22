import argparse
import csv
from shapely.geometry import Point, box
from shapely.ops import cascaded_union


class FeasibilityException(Exception):
    pass


class AbstractPallet:
    def __init__(self, length, width, height):
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
        self.id = type_id
        super(PalletType, self).__init__(length, width, height)


class SolutionPallet(AbstractPallet):
    def __init__(self, pallet_type, x_pos, y_pos, z_pos, h_turned):
        length = pallet_type.length if not h_turned else pallet_type.width
        width = pallet_type.length if h_turned else pallet_type.width
        self.origin_point = Point(x_pos, y_pos, z_pos)
        self.base_area = box(x_pos, y_pos, x_pos + length, y_pos + width)
        self.front_face = box(y_pos, z_pos, y_pos + width, z_pos + pallet_type.height)
        self.type = pallet_type
        super(SolutionPallet, self).__init__(length, width, pallet_type.height)

    def validate_rotation(self):
        if self.length == self.type.width and self.width == self.type.length:
            if self.type.turning_allowed:
                return True
            else:
                raise FeasibilityException(
                    "Die Palette im Startpunkt %s wurde unzulässigerweise gedreht." % self.origin_point.coords[:])
        return False

    def is_stackable(self):
        return self.type.stacking_allowed

    def validate_length(self):
        return self.length == self.type.length

    def get_maxx(self):
        """
        Get the maximum x value from the base area
        :return:
        """
        return self.base_area.bounds[2]

    def get_maxz(self):
        return self.origin_point.z + self.height

    def validate_width(self):
        return self.width == self.type.width

    def extends_width(self, width_value):
        return self.origin_point.z + self.width > width_value

    def validate_height(self, ):
        return self.height == self.type.height

    def extends_height(self, height_value):
        return self.origin_point.z + self.height > height_value

    def validate_dimension(self):
        if not self.validate_rotation():
            if not self.validate_length() or not self.validate_width():
                raise FeasibilityException(
                    "Die Palette im Startpunkt %s besitzt falsche Dimensionen." % self.origin_point.coords[:])
        if not self.validate_height():
            raise FeasibilityException(
                "Die Palette im Startpunkt %s besitzt falsche Dimensionen." % self.origin_point.coords[:])

    def overlaps_base_area(self, other_pallet):
        return self != other_pallet and (self.base_area.overlaps(other_pallet.base_area) or self.base_area.contains(
            other_pallet.base_area) or other_pallet.base_area.contains(self.base_area))

    def overlaps_front_face(self, other_pallet):
        return self != other_pallet and (
                self.front_face.overlaps(other_pallet.front_face) or
                self.front_face.contains(other_pallet.front_face) or other_pallet.front_face.contains(self.front_face))

    def touches_front_face(self, other_pallet):
        return self != other_pallet and self.origin_point.y <= other_pallet.origin_point.y < self.origin_point.y + self.width

    def overlaps_height(self, other_pallet):
        """
        Method checks only, if the other pallet overlaps from above
        :param other_pallet: SolutionPallet
        :return: True, if the other pallet overlaps
        """
        diff = other_pallet.origin_point.z - self.origin_point.z
        return 0 <= diff < self.height

    def is_other_pallet_stacked(self, other_pallet):
        return self.overlaps_base_area(other_pallet) and \
               self.get_maxz() == other_pallet.origin_point.z + other_pallet.height

    def is_other_pallet_in_front(self, other_pallet):
        return (self.overlaps_front_face(other_pallet) or self.touches_front_face(other_pallet))and \
               self.get_maxx() < other_pallet.get_maxx()


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
        print("Die minimale Länge beträgt: %s" % calculate_minimal_container_length(solution_pallets))
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
    check_stacking(solution_pallets)
    check_lifo(solution_pallets)


def check_count(solution_pallets, tasks):
    for key in tasks:
        used_pallets = len([i for i in filter(lambda item: item.type.id == tasks[key].id,
                                              solution_pallets)])
        if tasks[key].quantity != used_pallets:
            raise FeasibilityException(
                "Die Anzahl der Paletten vom Typ %s beträgt %s. Es ist jedoch die Anzahl %s gefordert." %
                (key, used_pallets, tasks[key].quantity))


def check_dimensions(solution_pallets):
    for pallet in solution_pallets:
        pallet.validate_dimension()


def check_container_dimensions(solution_pallets, width_value, height_value):
    for pallet in solution_pallets:
        if pallet.extends_width(width_value) or pallet.extends_height(height_value):
            raise FeasibilityException("Die Palette im Startpunkt %s vom Typ %s überschreitet die Container "
                                       "Dimensionen."
                                       % (pallet.origin_point.coords[:], pallet.type.id))


def check_stacking(solution_pallets):
    for pallet in solution_pallets:
        pallets_same_base_area = [i for i in filter(
            lambda item: pallet.overlaps_base_area(item), solution_pallets)]
        for other_pallet in pallets_same_base_area:
            if pallet.overlaps_height(other_pallet):
                raise FeasibilityException("Die Paletten in Startpunkt %s Typ: %s und %s  Typ: %s überschneiden sich." %
                                           (pallet.origin_point.coords[:], pallet.type.id,
                                            other_pallet.origin_point.coords[:], other_pallet.type.id))
        if pallet.origin_point.z > 0:
            if not pallet.is_stackable():
                raise FeasibilityException("Die Palette in Startpunkt %s vom Typ %s wurde unzulässigerweise gestapelt."
                                           % (pallet.origin_point.coords[:], pallet.type.id))
            area_for_stack = [i.base_area for i in filter(lambda item: pallet.origin_point.z == item.get_maxz(),
                                                          pallets_same_base_area)]
            if not cascaded_union(area_for_stack).contains(pallet.base_area):
                raise FeasibilityException("Die Palette in Startpunkt %s vom Typ %s wurde falsch gestapelt." %
                                           (pallet.origin_point.coords[:], pallet.type.id))


def check_lifo(solution_pallets):
    pallets_to_unload = solution_pallets.copy()
    while len(pallets_to_unload) > 0:
        min_order = min([i.type.order for i in pallets_to_unload])
        pallets_min_order = [i for i in filter(lambda item: item.type.order == min_order, pallets_to_unload)]
        max_x = max([i.get_maxx() for i in pallets_min_order])
        pallets_max_x = [i for i in filter(lambda item: item.get_maxx() == max_x, pallets_min_order)]
        max_z = max([i.get_maxz() for i in pallets_max_x])
        pallets_max_z = [i for i in filter(lambda item: item.get_maxz() == max_z, pallets_max_x)]
        # Check for accessibility
        for pallet in pallets_max_z:
            for other_pallet in pallets_to_unload:
                if pallet.is_other_pallet_stacked(other_pallet) or pallet.is_other_pallet_in_front(other_pallet):
                    raise FeasibilityException(
                        "Palette im Punkt %s vom Typ %s wird von der Palette %s vom Typ %s gemäß lifo verdeckt." %
                        (pallet.origin_point.coords[:], pallet.type.id, other_pallet.origin_point.coords[:],
                         other_pallet.type.id))
            pallets_to_unload.remove(pallet)


def calculate_minimal_container_length(solution_pallets):
    return max([i.get_maxx() for i in solution_pallets])


if __name__ == '__main__':
    main()
