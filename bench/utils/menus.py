class MenuEntry:

    def __init__(self, option, handler):
        self.option = option
        self.handler = handler

    def __repr__(self):
        return str(self.option)


class Menu:
    def __init__(self):
        self._entries = {}
        self._autokey = 1

    def add(self, key, option, handler):
        if key == "auto":
            key = str(self._autokey)
            self._autokey += 1

        self._entries[str(key)] = MenuEntry(option, handler)

    def items(self):
        return self._entries.items()

    def keys(self):
        return self._entries.keys()

    def max_lenght(self):
        key_max_lenght = 0
        option_max_lenght = 0
        for key, option in self.items():
            if len(str(key)) > key_max_lenght:
                key_max_lenght = len(str(key))
            if len(str(option)) > option_max_lenght:
                option_max_lenght = len(str(option))
        return key_max_lenght, option_max_lenght

    def __contains__(self, key):
        return key in self._entries

    def __getitem__(self, key):
        return self._entries[key]


def menu_frame_design(menu_name, width_menu):
    '''This function return the frame of a menu.
    '''

    # Add blank around menu name
    menu_name = "*  " + menu_name + "  *"

    # Calculate width of the menu
    menu_name_size = len(menu_name)
    if menu_name_size > width_menu:
        width_menu = menu_name_size

    # Generate the menu frame design
    menu_frame = " /"
    menu_frame += "*" * width_menu
    menu_frame += "/"

    if (width_menu - menu_name_size) % 2:
        menu_name += "*"
    menu_label_fill_number = ((width_menu - menu_name_size) // 2)
    menu_label = " /"
    menu_label += "*" * menu_label_fill_number
    menu_label += menu_name
    menu_label += "*" * menu_label_fill_number
    menu_label += "/"

    return menu_frame, menu_label


if __name__ == "__main__":
    menu = Menu()
    menu.add("auto", "première option du menu", lambda: None)
    menu.add("auto", "deuxième option du menu", lambda: None)
    menu.add("q", "quitter le menu", lambda: None)
    print(menu._entries)
    for x in '123q':
        print(f'{x} in {menu.items()} is: ', x in menu.keys())
