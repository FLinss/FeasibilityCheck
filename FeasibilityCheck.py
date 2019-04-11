import argparse
import os
import csv
from shapely.geometry import Point, box
from shapely.ops import cascaded_union


HEADER_SOLUTIONS = "Order,xPos,yPos,zPos,HTurned"


class FeasibilityException(Exception):
    pass


class DataException(Exception):
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
        """
        Checks if the pallet was rotated and then if the rotation was allowed. Raises exception, in case of incorrect
        rotation
        :return: True, if the pallet is rotated and the rotation is allowed. Otherwise, false.
        """
        if self.length == self.type.width and self.width == self.type.length:
            if self.type.turning_allowed:
                return True
            else:
                raise FeasibilityException(
                    "Die Palette im Startpunkt %s vom Typ %s wurde unzulässigerweise gedreht." % (
                      self.origin_point.coords[:], self.type.id))
        return False

    def is_stackable(self):
        """
        Checks if the pallet is stackable.
        :return: True, if the pallet is stackable
        """
        return self.type.stacking_allowed

    def validate_length(self):
        """
        Checks, if the used pallet length is equal to the pallet type length
        :return: True, if the pallet length is equal to the pallet type length
        """
        return self.length == self.type.length

    def get_maxx(self):
        """
        Get the maximum x value from the pallet (here: base area)
        :return: Maximal coordinate in x direction
        """
        return self.base_area.bounds[2]

    def get_maxz(self):
        """
        Get the maximum z value from the pallet
        :return: Maximal coordinate in z direction
        """
        return self.origin_point.z + self.height

    def validate_width(self):
        """
        Checks, if the used pallet width is equal to the pallet type width
        :return: True, if the pallet width is equal to the pallet type width
        """
        return self.width == self.type.width

    def extends_width(self, width_value):
        """
        Checks, if the pallet is wider than a specific value
        :param width_value: integer value for a specific width
        :return: True, if the pallet is wider than the specific value
        """
        return self.origin_point.z + self.width > width_value

    def validate_height(self, ):
        """
        Checks, if the used pallet height is equal to the pallet type height
        :return: True, if the pallet height is equal to the pallet type height
        """
        return self.height == self.type.height

    def extends_height(self, height_value):
        """
        Checks, if the pallet is higher than a specific value
        :param height_value: integer value for a specific height
        :return: True, if the pallet is higher than the specific value

        """
        return self.origin_point.z + self.height > height_value

    def validate_dimension(self):
        """
        Checks all dimensions of the pallet.
        :return: True, if the pallet has the right length, width and height
        """
        if not self.validate_rotation():
            if self.validate_length() and self.validate_width():
                return self.validate_height()
            return False
        return self.validate_height()

    def overlaps_base_area(self, other_pallet):
        """
        Checks, if the base areas of this and the other pallet overlap or contain each-other
        :param other_pallet: Another solution pallet
        :return: True, if the base areas overlap each-other
        """
        return self != other_pallet and (self.base_area.overlaps(other_pallet.base_area) or self.base_area.contains(
            other_pallet.base_area) or other_pallet.base_area.contains(self.base_area))

    def overlaps_front_face(self, other_pallet):
        """
        Checks, if the front faces of this and the other pallet overlap or contain each-other
        :param other_pallet:  Another solution pallet
        :return: True, if the front faces overlap each-other
        """
        return self != other_pallet and (
                self.front_face.overlaps(other_pallet.front_face) or
                self.front_face.contains(other_pallet.front_face) or other_pallet.front_face.contains(self.front_face))

    def touches_front_face(self, other_pallet):
        """
        Checks, if the front face of the other pallet just touches the self front face
        :param other_pallet: Another solution pallet
        :return: True, if the front face of the other pallet touches the self front face
        """
        return self != other_pallet and self.origin_point.y <= other_pallet.origin_point.y < \
            self.origin_point.y + self.width

    def overlaps_height(self, other_pallet):
        """
        Method checks only, if the other pallet overlaps from above
        :param other_pallet: Another solution pallet
        :return: True, if the other pallet overlaps
        """
        diff = other_pallet.origin_point.z - self.origin_point.z
        return 0 <= diff < self.height

    def is_other_pallet_stacked(self, other_pallet):
        """
        Checks, if the other pallet is stacked on top of the self pallet
        :param other_pallet:
        :return: True, if the other pallet is stacked on top of the self pallet
        """
        return self != other_pallet and self.overlaps_base_area(other_pallet) and \
            self.get_maxz() == other_pallet.origin_point.z

    def is_other_pallet_in_front(self, other_pallet):
        """
        Checks, of the other pallet is in front of the self pallet
        :param other_pallet: Another solution pallet
        :return: True, if the other pallet is in front of the self pallet
        """
        return (self.overlaps_front_face(other_pallet) or self.touches_front_face(other_pallet)) and \
            self.get_maxx() < other_pallet.get_maxx()


def main():
    parser = argparse.ArgumentParser(description='Überprüfung der Zulässigkeit einer Lösung.')
    parser.add_argument('--task', '-t', type=str, required=True,
                        help='Aufgabedaten als csv-Datei')
    parser.add_argument('--solution', '-s', type=str, required=True,
                        help='Lösungsdaten als csv-Datei')
    parser.add_argument('--width', '-y', type=int, help='Breite (y-Wert) des Containers', default=100)
    parser.add_argument('--height', '-z', type=int, help='Höhe (z-Wert) des Containers', default=100)
    args = parser.parse_args()
    tasks = import_tasks_by_file(args.task)
    solutions = []
    if os.path.isdir(args.solution):
        for path, dirs, files in os.walk(args.solution):
            for filename in files:
                solutions.append(os.path.join(path, filename))
    else:
        solutions.append(args.solution)
    for solution in solutions:
        try:
            print(solution)
            solution_pallets = import_solution_by_file(solution, tasks)
            validate_solution(solution_pallets, tasks, args.width, args.height)
            print("Die Lösung ist zulässig.")
            print("Die minimale Länge beträgt: %s \n" % calculate_minimal_container_length(solution_pallets))
        except (FeasibilityException, DataException) as e:
            print("Die Lösung ist unzulässig.")
            print(e, "\n")


def import_tasks_by_file(file):
    """
    Import tasks from a csv file
    :param file: A csv file
    :return: Dictionary of all tasks (pallet types)
    """
    with open(file, newline='') as csvfile:
        return import_tasks(csvfile)


def import_tasks(iterable):
    """
    Import tasks from an iterable object
    :param iterable: Iterable object; Field names must be correct
    :return: Dictionary of all tasks (pallet types)
    """
    csvreader = csv.DictReader(iterable, delimiter=',', quotechar='|')
    result = dict()
    for row in csvreader:
        result[int(row["Order"])] = PalletType(int(row["Order"]), row["Description"], int(row["Quantity"]),
                                               int(row["Length"]), int(row["Width"]), int(row["Height"]),
                                               bool(int(row["TurningAllowed"])), bool(int(row["StackingAllowed"])),
                                               int(row["Group"]))
    return result


def import_solution_by_file(file, task_data):
    """
    Import solution from a csv file
    :param file: A csv file
    :param task_data: Already imported tasks
    :return: List of solution pallets
    """
    try:
        with open(file, newline='') as csvfile:
            line = csvfile.readline().strip()  # strip is necessary, because the first line ends with '\p\n'
            if line != HEADER_SOLUTIONS:
                raise DataException("Fehlerhafter Header: %s" % line)
        with open(file, newline='') as csvfile:
            return import_solution(csvfile, task_data)
    except UnicodeDecodeError:
        raise DataException("Fehler beim Decoding; vermutlich Binärdatei.")


# TODO: zweite Importfunktion mit TypId und zwei Punkten
def import_solution(iterable, task_data):
    """
    Import solution from an iterable object
    :param iterable: An iterable object
    :param task_data: Already imported tasks
    :return: List of solution pallets
    """
    csvreader = csv.DictReader(iterable, delimiter=',', quotechar='|')
    result = []
    for row in csvreader:
        new_solution_pallet_type = task_data[int(row["Order"])]
        new_solution_pallet = SolutionPallet(new_solution_pallet_type, int(row["xPos"]), int(row["yPos"]),
                                             int(row["zPos"]), int(row["HTurned"]))
        result.append(new_solution_pallet)
    return result


def validate_solution(solution_pallets, tasks, height_value, width_value):
    """
    Main function to validate all aspects for a feasible solution
    :param solution_pallets: List of solution pallets
    :param tasks: Dictionary of tasks (pallet types)
    :param height_value: Height of the container
    :param width_value: Width of the container
    """
    check_count(solution_pallets, tasks)
    check_dimensions(solution_pallets)
    check_container_dimensions(solution_pallets, height_value, width_value)
    check_stacking(solution_pallets)
    check_lifo(solution_pallets)


def check_count(solution_pallets, tasks):
    """
    This function checks, if the quantity of pallet types in the solution is equal to the required number in tasks
    :param solution_pallets: List of solution pallets
    :param tasks: Dictionary of tasks (Pallet types)
    """
    for key in tasks:
        used_pallets = len([i for i in filter(lambda item: item.type.id == key,
                                              solution_pallets)])
        if tasks[key].quantity != used_pallets:
            raise FeasibilityException(
                "Die Anzahl der Paletten vom Typ %s beträgt %s. Es ist jedoch die Anzahl %s gefordert." %
                (key, used_pallets, tasks[key].quantity))


def check_dimensions(solution_pallets):
    """
    All pallets have to be validated regarding their dimensions
    :param solution_pallets: List of solution pallets.
    """
    for pallet in solution_pallets:
        if not pallet.validate_dimension():
            raise FeasibilityException("Die Palette im Startpunkt %s vom Typ %s besitzt falsche Dimensionen." %
                                       (pallet.origin_point.coords[:], pallet.type.id))


def check_container_dimensions(solution_pallets, width_value, height_value):
    """
    All pallets have to fit into the container
    :param solution_pallets: List of solution pallets
    :param width_value: Width of the container
    :param height_value: Height of the container
    """
    for pallet in solution_pallets:
        if pallet.extends_width(width_value) or pallet.extends_height(height_value):
            raise FeasibilityException("Die Palette im Startpunkt %s vom Typ %s überschreitet die Container "
                                       "Dimensionen."
                                       % (pallet.origin_point.coords[:], pallet.type.id))


def check_stacking(solution_pallets):
    """
    Checks the stacking of all pallets
    :param solution_pallets: List of solution pallets
    """
    for pallet in solution_pallets:
        # All pallets, which have a overlap in the base area should not overlaps in the height:
        pallets_same_base_area = [i for i in filter(lambda item: pallet.overlaps_base_area(item), solution_pallets)]
        for other_pallet in pallets_same_base_area:
            if pallet.overlaps_height(other_pallet):
                raise FeasibilityException("Die Paletten in Startpunkt %s Typ: %s und %s  Typ: %s überschneiden sich." %
                                           (pallet.origin_point.coords[:], pallet.type.id,
                                            other_pallet.origin_point.coords[:], other_pallet.type.id))
        # If the current pallet is not on the ground of the container, it needs a stackable base area:
        if pallet.origin_point.z > 0:
            if not pallet.is_stackable():
                raise FeasibilityException("Die Palette in Startpunkt %s vom Typ %s wurde unzulässigerweise gestapelt."
                                           % (pallet.origin_point.coords[:], pallet.type.id))
            area_for_stack = [i.base_area for i in
                              filter(lambda item: pallet.origin_point.z == item.get_maxz() and item.is_stackable(),
                                     pallets_same_base_area)]
            # Base area of current pallet must be completely overlapped
            if not cascaded_union(area_for_stack).contains(pallet.base_area):
                raise FeasibilityException("Die Palette in Startpunkt %s vom Typ %s wurde falsch gestapelt." %
                                           (pallet.origin_point.coords[:], pallet.type.id))


def check_lifo(solution_pallets):
    """
    Checks the accessibility for unloading all pallets according to the LIFO condition (Lowest order number at first)
    :param solution_pallets: List of solution pallets
    """
    remaining_pallets = solution_pallets.copy()
    while len(remaining_pallets) > 0:
        # Pallets must be sorted by order (ASC), maximal x coordinate (DESC) and maximal z coordinate (DESC)
        # current Pallets to unload are the first entry of the sorting
        min_order = min([i.type.order for i in remaining_pallets])
        pallets_min_order = [i for i in filter(lambda item: item.type.order == min_order, remaining_pallets)]
        max_x = max([i.get_maxx() for i in pallets_min_order])
        pallets_max_x = [i for i in filter(lambda item: item.get_maxx() == max_x, pallets_min_order)]
        max_z = max([i.get_maxz() for i in pallets_max_x])
        pallets_to_unload = [i for i in filter(lambda item: item.get_maxz() == max_z, pallets_max_x)]
        # Check for accessibility: All pallets to unload must be checked, if there is no pallet on top,
        # directly in front or in a lower layer in front
        for pallet in pallets_to_unload:
            for other_pallet in remaining_pallets:
                if pallet.is_other_pallet_stacked(other_pallet) or pallet.is_other_pallet_in_front(other_pallet):
                    raise FeasibilityException(
                        "Palette im Punkt %s vom Typ %s wird von der Palette %s vom Typ %s gemäß LIFO verdeckt." %
                        (pallet.origin_point.coords[:], pallet.type.id, other_pallet.origin_point.coords[:],
                         other_pallet.type.id))
            remaining_pallets.remove(pallet)


def calculate_minimal_container_length(solution_pallets):
    """
    Calculates the minimal container lengths so that all pallets fit into the container
    :param solution_pallets: List of solution pallets
    :return: The maximal x coordinate of all pallets as lower bound for the container length
    """
    return max([i.get_maxx() for i in solution_pallets])


if __name__ == '__main__':
    main()
